"""
K24 Orchestrator ("The Brain")
Coordinates Intent Recognition, Context Management, and Tally Integration.
Implements the "Competence over Magic" philosophy.
"""
import logging
import json
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import os

from backend.intent_recognizer import IntentRecognizer, IntentType, Intent
from backend.context_manager import ContextManager, UserContext
from backend.tally_connector import TallyConnector
from backend.agent import TallyAgent

logger = logging.getLogger(__name__)

@dataclass
class DraftResponse:
    """Structured response for the frontend"""
    message: str
    type: str  # 'text', 'draft_voucher', 'report', 'clarification', 'follow_up', 'card'
    data: Optional[Dict[str, Any]] = None
    confidence: float = 1.0
    
    def to_dict(self):
        return asdict(self)

class K24Orchestrator:
    def __init__(self, api_key: str, redis_url: str = "redis://localhost:6379"):
        self.intent_recognizer = IntentRecognizer(api_key)
        self.context_manager = ContextManager(redis_url=redis_url)
        # Tally connector for lookups
        tally_url = os.getenv("TALLY_URL", "http://localhost:9000")
        self.tally = TallyConnector(tally_url)
        # Analyst Agent
        self.analyst = TallyAgent(api_key=api_key)
        
    async def process_message(self, user_id: str, message: str, active_draft: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main entry point: Process user message and return structured response.
        """
        # 1. Handle Draft Editing (If active draft exists)
        if active_draft:
            updated_draft = self._update_draft(active_draft, message)
            if updated_draft:
                return updated_draft.to_dict()

        # 2. Get Context
        context = self.context_manager.get_context(user_id)
        
        # 3. Recognize Intent
        intent = await self.intent_recognizer.recognize(message, context=context.to_dict())
        
        # 4. Contextual Entity Resolution (Handle "them", "it", "him")
        if not intent.entity and context.last_entity:
            intent.entity = self._resolve_entity_from_context(message, context.last_entity)
            if intent.entity:
                logger.info(f"Resolved entity from context: {intent.entity}")

        # 5. Route based on Intent (The Director)
        response = await self._route_intent(user_id, intent, context)
        
        # 6. Update History
        self.context_manager.add_to_history(
            user_id=user_id,
            user_message=message,
            assistant_response=response.message,
            intent=intent.dict()
        )
        
        # Update last entity if found in this turn
        if intent.entity:
            self.context_manager.update_context(user_id, last_entity=intent.entity)
        
        return response.to_dict()

    def _resolve_entity_from_context(self, message: str, last_entity: str) -> Optional[str]:
        """If message contains pronouns, return the last entity."""
        pronouns = ["it", "them", "him", "her", "this", "that", "party", "ledger"]
        message_lower = message.lower()
        if any(f" {p} " in f" {message_lower} " for p in pronouns):
            return last_entity
        return None

    async def _route_intent(self, user_id: str, intent: Intent, context: UserContext) -> DraftResponse:
        """
        The Director: Decides the best way to present the answer.
        Prioritizes Widgets and Actions over Text.
        """
        
        # --- SCENARIO 1: DATA QUERY (Executive Brief) ---
        if intent.action == IntentType.QUERY_DATA:
            # Robust Report Mapping
            report_map = {
                "balance sheet": ("/reports/balance-sheet", "Balance Sheet Snapshot"),
                "profit": ("/reports/profit-loss", "P&L Snapshot"),
                "loss": ("/reports/profit-loss", "P&L Snapshot"),
                "cash": ("/reports/cash-book", "Cash Position"),
                "bank": ("/reports/cash-book", "Bank Position"),
                "sales": ("/reports/sales-register", "Sales Performance"),
                "purchase": ("/reports/purchase-register", "Purchase Analysis"),
                "gst": ("/reports/gst", "GST Liability"),
                "tax": ("/reports/gst", "Tax Overview"),
                "daybook": ("/daybook", "Today's Activity"),
                "ledger": ("/ledgers", "Ledger View"),
                "outstanding": ("/reports/outstanding", "Outstanding Receivables"),
                "receivable": ("/reports/outstanding", "Outstanding Receivables"),
                "pending": ("/reports/outstanding", "Outstanding Receivables"),
                "due": ("/reports/outstanding", "Outstanding Receivables"),
                "audit": ("/reports/audit", "Compliance Audit"),
                "health": ("/reports/audit", "System Health Check"),
                "compliance": ("/reports/audit", "Compliance Report"),
                "risk": ("/reports/audit", "Risk Assessment"),
            }

            query_lower = intent.raw_query.lower()
            
            # Check if query matches any known report
            for keyword, (path, title) in report_map.items():
                if keyword in query_lower:
                    return DraftResponse(
                        message=f"Opening {title}...",
                        type="navigation",
                        data={
                            "path": path,
                            "widget": {
                                "type": "KPI_CARD",
                                "title": title,
                                "data": {"Status": "Loading..."}
                            }
                        }
                    )
            
            # Check for Ledger/Contact specific query
            if intent.entity:
                 matches = self.tally.lookup_ledger(intent.entity)
                 if matches:
                     ledger_name = matches[0]
                     return DraftResponse(
                        message=f"Opening history for {ledger_name}...",
                        type="navigation",
                        data={
                            "path": f"/contacts/{ledger_name}",
                            "widget": {
                                "type": "KPI_CARD",
                                "title": ledger_name,
                                "data": {"Status": "Loading History..."}
                            }
                        }
                    )

            # If no specific report found, fall back to general analysis
            return await self._handle_query(user_id, intent, context)

        # --- SCENARIO 2: TRANSACTION (Action Card or Form) ---
        elif intent.action == IntentType.CREATE_SALE:
            return await self._handle_voucher_navigation(user_id, intent, context)
        
        elif intent.action == IntentType.CREATE_PURCHASE:
            return await self._handle_transaction_draft(user_id, intent, context)
        
        # --- SCENARIO 3: RECEIPT/PAYMENT (Voucher Form) ---
        elif intent.action in [IntentType.CREATE_RECEIPT, IntentType.CREATE_PAYMENT]:
            return await self._handle_voucher_navigation(user_id, intent, context)
            
        # --- SCENARIO 4: CLARIFICATION (Ambiguous Request) ---
        elif intent.action == IntentType.CLARIFY_INTENT:
            return DraftResponse(
                message=f"I can help with that. What kind of transaction is this for {intent.entity or 'you'}?",
                type="follow_up",
                data={
                    "question": f"What kind of transaction is this for {intent.entity or 'you'}?",
                    "missing_slots": ["transaction_type"],
                    "options": ["Sales", "Purchase", "Receipt", "Payment"]
                }
            )

        # --- SCENARIO 5: UNKNOWN ---
        elif intent.action == IntentType.UNKNOWN:
            return DraftResponse(
                message="I didn't catch that. Try 'Show Balance Sheet' or 'Sale to Sharma'.",
                type="text"
            )
            
        else:
            # Fallback
            return DraftResponse(
                message=f"I understood: {intent.action.value}. (Workflow pending)",
                type="text"
            )

    async def _handle_transaction_draft(self, user_id: str, intent: Intent, context: UserContext) -> DraftResponse:
        """
        Creates a 'Draft Card' for approval.
        """
        party_name = intent.entity
        if not party_name:
             return DraftResponse(
                message="Which party is this for?",
                type="follow_up",
                data={"missing_slots": ["party"]}
            )

        # --- SMART LOOKUP ---
        matches = self.tally.lookup_ledger(party_name)
        
        if not matches:
            return DraftResponse(
                message=f"I couldn't find a ledger for '{party_name}'. Do you want to create it?",
                type="follow_up",
                data={
                    "question": f"Create new ledger for '{party_name}'?",
                    "missing_slots": ["create_ledger_confirm"], 
                    "options": ["Yes, Create New", "No, Cancel"]
                }
            )
        
        if len(matches) > 1:
            return DraftResponse(
                message=f"Found multiple matches for '{party_name}'. Please select one:",
                type="follow_up",
                data={
                    "question": "Select the correct party:",
                    "missing_slots": ["party_selection"],
                    "options": matches[:5]
                }
            )
            
        final_party_name = matches[0]

        # Construct Draft
        draft_voucher = {
            "party_name": final_party_name,
            "voucher_type": "Sales" if intent.action == IntentType.CREATE_SALE else "Purchase",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "items": [
                {
                    "name": intent.parameters.get("item", "General Item"),
                    "amount": float(intent.parameters.get("amount", 0) or 0),
                    "quantity": float(intent.parameters.get("quantity", 1) or 1),
                    "rate": float(intent.parameters.get("rate", 0) or 0)
                }
            ],
            "amount": float(intent.parameters.get("amount", 0) or 0)
        }
        
        return DraftResponse(
            message=f"Ready to book {draft_voucher['voucher_type']} for {final_party_name}?",
            type="draft_voucher",
            data=draft_voucher
        )

    async def _handle_query(self, user_id: str, intent: Intent, context: UserContext) -> DraftResponse:
        """Handle general queries with Analyst Mode"""
        query = intent.raw_query.lower()
        
        # Check for deep analysis triggers
        analysis_keywords = ["why", "analyze", "trend", "compare", "reason", "insight", "forecast"]
        if any(k in query for k in analysis_keywords):
            # ANALYST MODE
            try:
                # For now, we fetch a summary dataframe (e.g., Sales Register)
                # In a real scenario, we'd pick the right dataset based on the query
                df = self.tally.fetch_sales_register("SHREE JI SALES") # Default company for now
                
                if df is None or df.empty:
                    return DraftResponse(message="I tried to analyze, but couldn't fetch data.", type="text")
                
                analysis_result = self.analyst.analyze_with_pandas(df, intent.raw_query)
                
                return DraftResponse(
                    message=analysis_result,
                    type="card",
                    data={
                        "title": "AI Analysis",
                        "data": {"Insight": "See text above"} # Frontend renders text + card
                    }
                )
            except Exception as e:
                logger.error(f"Analyst mode failed: {e}")
                return DraftResponse(message="I encountered an error during analysis.", type="text")

        # Standard Response
        return DraftResponse(
            message=self.intent_recognizer._get_response_for_intent(intent),
            type="text"
        )

    async def _handle_voucher_navigation(self, user_id: str, intent: Intent, context: UserContext) -> DraftResponse:
        """Navigate to voucher creation form with pre-filled data"""
        party_name = intent.entity or ""
        amount = intent.parameters.get("amount", "")
        
        voucher_type_map = {
            IntentType.CREATE_SALE: ("sales", "Sales Invoice"),
            IntentType.CREATE_RECEIPT: ("receipt", "Receipt"),
            IntentType.CREATE_PAYMENT: ("payment", "Payment")
        }
        
        voucher_route, voucher_label = voucher_type_map.get(intent.action, ("receipt", "Receipt"))
        
        # Build query parameters
        query_params = []
        if party_name:
            query_params.append(f"party={party_name}")
        if amount:
            query_params.append(f"amount={amount}")
        
        query_string = "?" + "&".join(query_params) if query_params else ""
        path = f"/vouchers/new/{voucher_route}{query_string}"
        
        return DraftResponse(
            message=f"Opening {voucher_label} form...",
            type="navigation",
            data={
                "path": path,
                "widget": {
                    "type": "KPI_CARD",
                    "title": f"New {voucher_label}",
                    "data": {"Party": party_name or "TBD", "Amount": amount or "TBD"}
                }
            }
        )

    def _update_draft(self, draft: Dict[str, Any], message: str) -> Optional[DraftResponse]:
        """
        Smartly updates an existing draft based on user feedback.
        """
        # Update Amount/Price
        amount_match = re.search(r'(?:price|amount|val|value|rs|inr|to)\s*[:=]?\s*(\d+)', message, re.IGNORECASE)
        if not amount_match:
             if message.strip().isdigit():
                 amount_match = re.search(r'(\d+)', message)
        
        if amount_match:
            new_amount = float(amount_match.group(1))
            draft['amount'] = new_amount
            if draft.get('items') and len(draft['items']) == 1:
                draft['items'][0]['amount'] = new_amount
                qty = draft['items'][0].get('quantity', 1)
                if qty > 0:
                    draft['items'][0]['rate'] = new_amount / qty
            
            return DraftResponse(
                message=f"Updated amount to {new_amount}. Ready?",
                type="draft_voucher",
                data=draft
            )
            
        # Update Quantity
        qty_match = re.search(r'(?:qty|quantity|count|bags|nos|pcs)\s*[:=]?\s*(\d+)', message, re.IGNORECASE)
        if qty_match:
            new_qty = float(qty_match.group(1))
            if draft.get('items') and len(draft['items']) == 1:
                draft['items'][0]['quantity'] = new_qty
            
            return DraftResponse(
                message=f"Updated quantity to {new_qty}. Ready?",
                type="draft_voucher",
                data=draft
            )

        return None
