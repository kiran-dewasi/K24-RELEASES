"""
Query Orchestrator Service - Day 5 Implementation
=================================================
Intelligent query processing that understands user intent and 
pulls ONLY relevant data from Tally/SQLite.

Use Cases:
- "How much does ABC Corp owe?" â†’ Outstanding summary
- "Send invoice INV-001 as PDF" â†’ Generate PDF, send via WhatsApp
- "January sales summary" â†’ Pull sales data, format concisely
- "Stock of Product A?" â†’ Quick stock status

The orchestrator follows the architecture principle:
"Don't dump all 100 bills - show top 3 and summary"
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from database import (
    get_db, Ledger, Voucher, StockItem, Bill, SessionLocal, StockMovement
)

logger = logging.getLogger("QueryOrchestrator")


# ============== INTENT DEFINITIONS ==============

class QueryIntent(Enum):
    """Supported user query intents"""
    # Customer/Party queries
    OUTSTANDING = "outstanding"           # "How much does X owe?"
    PAYMENT_HISTORY = "payment_history"   # "X's payments this month"
    CUSTOMER_360 = "customer_360"         # "Full profile of X"
    
    # Stock/Item queries
    STOCK_CHECK = "stock_check"           # "How much Product A in stock?"
    ITEM_RATE = "item_rate"               # "What's the rate of Product A?"
    ITEM_360 = "item_360"                 # "Full details of Product A"
    
    # Report queries
    SALES_SUMMARY = "sales_summary"       # "January sales summary"
    PURCHASE_SUMMARY = "purchase_summary" # "This month's purchases"
    TOP_CUSTOMERS = "top_customers"       # "Top 10 customers"
    TOP_ITEMS = "top_items"               # "Best selling items"
    CASHBOOK = "cashbook"                 # "Cash balance today"
    
    # Export requests
    EXPORT_PDF = "export_pdf"             # "Send invoice as PDF"
    EXPORT_EXCEL = "export_excel"         # "Export sales to Excel"
    
    # Voucher/Invoice queries
    INVOICE_DETAILS = "invoice_details"   # "Show invoice INV-001"
    RECENT_VOUCHERS = "recent_vouchers"   # "Last 5 sales"
    
    # Voucher Creation
    CREATE_RECEIPT = "create_receipt"     # "Received 5000 from Rahul"
    CREATE_PAYMENT = "create_payment"     # "Paid 2000 to Suresh"
    CREATE_SALE = "create_sale"           # "Sold 10 items to Rahul"
    CREATE_PURCHASE = "create_purchase"   # "Bought 50 items from Suresh"
    
    # General/Unknown
    GENERAL_QUERY = "general"             # Fallback


@dataclass
class ParsedQuery:
    """Result of query parsing"""
    intent: QueryIntent
    confidence: float  # 0.0 to 1.0
    entities: Dict[str, Any]  # Extracted entities (party name, item, date range, etc.)
    original_query: str
    format_requested: Optional[str] = None  # "pdf", "excel", "text"


@dataclass
class OrchestrationResult:
    """Result of data orchestration"""
    success: bool
    data: Dict[str, Any]
    formatted_response: str  # WhatsApp-ready text
    export_file: Optional[str] = None  # Path if PDF/Excel generated
    error: Optional[str] = None


# ============== INTENT PATTERNS ==============

INTENT_PATTERNS = {
    QueryIntent.OUTSTANDING: [
        r"(?:how much|kitna|what).+(?:owe|outstanding|due|baaki|baki|udhar)",
        r"outstanding.+(?:from|of|for|ka)",
        r"(?:check|show|tell).+outstanding",
        r"(?:pending|due|remaining).+(?:amount|balance|payment)",
    ],
    QueryIntent.PAYMENT_HISTORY: [
        r"(?:payment|receipt|paym).+(?:history|this month|last month)",
        r"(?:how much|kitna).+(?:paid|pay|received)",
        r"(?:payment|receipt)s?.+(?:from|by|of)",
        r"(?:credit|collection).+(?:history|status)",
    ],
    QueryIntent.STOCK_CHECK: [
        r"(?:how much|kitna|what).+(?:stock|inventory|qty|quantity)",
        r"(?:stock|inventory).+(?:of|for|check)",
        r"(?:available|remaining).+(?:stock|units|qty)",
        r"(?:check|show).+(?:stock|inventory)",
    ],
    QueryIntent.ITEM_RATE: [
        r"(?:what|kya).+(?:rate|price|cost)",
        r"(?:rate|price).+(?:of|for)",
        r"(?:current|latest|last).+(?:rate|price)",
    ],
    QueryIntent.SALES_SUMMARY: [
        r"(?:sales|sale|revenue).+(?:summary|report|total)",
        r"(?:january|february|march|april|may|june|july|august|september|october|november|december|this month|last month).+(?:sales|revenue)",
        r"(?:total|summary).+(?:sales|revenue)",
        r"(?:bikri|bikayi).+(?:summary|total|report)",
        r"(?:last|this)\s+(?:month|week|year).+(?:revenue|sales|turnover)",
        r"(?:revenue|turnover|sales).+(?:last|this)\s+(?:month|week|year)",
    ],
    QueryIntent.PURCHASE_SUMMARY: [
        r"(?:purchase|purchases|kharid).+(?:summary|report|total)",
        r"(?:january|february|march|april|may|june|july|august|september|october|november|december|this month|last month).+(?:purchase|purchases)",
    ],
    QueryIntent.TOP_CUSTOMERS: [
        r"(?:top|best|biggest).+(?:customer|party|client)",
        r"(?:customer|party).+(?:top|best|ranking)",
        r"(?:who|which).+(?:buy|purchase).+(?:most|maximum)",
    ],
    QueryIntent.TOP_ITEMS: [
        r"(?:top|best|most).+(?:selling|sold|popular).+(?:item|product)",
        r"(?:what|which).+(?:sell|sold).+(?:most|maximum)",
    ],
    QueryIntent.EXPORT_PDF: [
        r"(?:send|export|generate|email|give|get).+(?:pdf|invoice|bill).+(?:pdf)?",
        r"(?:pdf).+(?:of|for)",
        r"(?:invoice|bill).+(?:as|in).+pdf",
        r"(?:give|get|send|email).+pdf",
        r"(?:pdf).+(?:please|plz)?",
    ],
    QueryIntent.EXPORT_EXCEL: [
        r"(?:export|send|download|give|get).+(?:excel|xlsx|xls|spreadsheet)",
        r"(?:excel).+(?:of|for|export)",
        r"(?:give|get).+(?:excel|xlsx)",
    ],
    QueryIntent.INVOICE_DETAILS: [
        r"(?:show|send|get|invoice|bill).+(?:inv|invoice|bill|voucher)[\s\-#\.]*(?:no\.?)?\s*([A-Za-z0-9\-]+)",
        r"(?:details|info).+(?:invoice|bill|voucher)",
    ],
    QueryIntent.RECENT_VOUCHERS: [
        r"(?:last|recent|latest).+(\d+).+(?:sale|purchase|voucher|invoice)",
        r"(?:show|list).+(?:recent|last).+(?:sale|purchase|voucher)",
    ],
    QueryIntent.CASHBOOK: [
        r"(?:cash|naqd).+(?:balance|status|book|available)",
        r"(?:how much|kitna).+(?:cash|naqd)",
    ],
    QueryIntent.CUSTOMER_360: [
        r"(?:full|complete|all|360).+(?:profile|details|info).+(?:of|for)",
        r"(?:everything|sab kuch).+(?:about|of)",
    ],
    QueryIntent.ITEM_360: [
        r"(?:full|complete|all|360).+(?:details|info).+(?:item|product)",
    ],
}

# Entity extraction patterns
ENTITY_PATTERNS = {
    "party_name": [
        r"(?:from|of|for|by|to|ka|ki|ke|about)\s+([A-Z][A-Za-z\s&]+?)(?:\s+(?:owe|outstanding|pay|paid|profile|details)|$|[,.])",
        r"([A-Z][A-Za-z\s&]{2,30}?)(?:'s|'s|\s+ka|\s+ki)",
    ],
    "item_name": [
        r"(?:stock|rate|price|item|product).+(?:of|for|ka|ki)\s+([A-Za-z0-9\s\-]+)",
        r"([A-Za-z0-9\s\-]{2,30})\s+(?:stock|rate|price|in stock)",
    ],
    "invoice_number": [
        r"(?:invoice|inv|bill|voucher)[\s\-#]*([A-Z0-9\-]+)",
        r"#([A-Z0-9\-]+)",
    ],
    "date_range": [
        r"(january|february|march|april|may|june|july|august|september|october|november|december)",
        r"(this month|last month|this week|today|yesterday)",
        r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
    ],
    "limit": [
        r"(?:top|last|recent|first)\s+(\d+)",
    ],
}


class QueryOrchestrator:
    """
    Main orchestrator class that:
    1. Parses user queries to understand intent
    2. Extracts relevant entities (party name, item, date range)
    3. Pulls ONLY the required data from database
    4. Formats response concisely for WhatsApp/Web
    """
    
    def __init__(self, db: Session, tenant_id: str = "default"):
        self.db = db
        self.tenant_id = tenant_id
    
    def process_query(self, query: str) -> OrchestrationResult:
        """
        Main entry point - process a user query and return formatted result.
        
        Args:
            query: Natural language query from user (WhatsApp or Web)
            
        Returns:
            OrchestrationResult with formatted response and optional export file
        """
        try:
            # Step 1: Parse query to detect intent and entities
            parsed = self.parse_query(query)
            logger.info(f"Parsed query: intent={parsed.intent.value}, confidence={parsed.confidence}, entities={parsed.entities}")
            
            # Step 2: Route to appropriate handler based on intent
            handler = self._get_handler(parsed.intent)
            result = handler(parsed)
            
            return result
            
        except Exception as e:
            logger.error(f"Query orchestration failed: {e}")
            return OrchestrationResult(
                success=False,
                data={},
                formatted_response="âŒ Sorry, I couldn't process that request. Please try again.",
                error=str(e)
            )
    
    def parse_query(self, query: str) -> ParsedQuery:
        """
        Parse natural language query to detect intent and extract entities.
        Uses LLM (Gemini) for intelligent understanding with regex fallback.
        """
        import os
        query_lower = query.lower().strip()
        
        # ============ TRY LLM-BASED RECOGNITION FIRST ============
        try:
            from intent_recognizer import classify_intent, IntentType
            
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                llm_result = classify_intent(api_key, query)
                
                if llm_result and llm_result.get("confidence", 0) > 0.5:
                    llm_intent = llm_result.get("intent", "unknown")
                    llm_confidence = llm_result.get("confidence", 0.0)
                    llm_entity = llm_result.get("entity", "")
                    intent_obj = llm_result.get("intent_obj")
                    
                    logger.info(f"ðŸ§  LLM Intent: {llm_intent} (conf={llm_confidence:.2f})")
                    
                    # Map LLM intent types to QueryIntent
                    intent_mapping = {
                        "query_data": QueryIntent.GENERAL_QUERY,
                        "generate_report": QueryIntent.SALES_SUMMARY,
                        "create_purchase": QueryIntent.CREATE_PURCHASE,
                        "create_sale": QueryIntent.CREATE_SALE,
                        "create_receipt": QueryIntent.CREATE_RECEIPT,
                        "create_payment": QueryIntent.CREATE_PAYMENT,
                        "reconcile_invoices": QueryIntent.INVOICE_DETAILS,
                        "unknown": QueryIntent.GENERAL_QUERY,
                    }
                    
                    found_creation_intent = False
                    # Initial mapping
                    mapped_intent = intent_mapping.get(llm_intent, QueryIntent.GENERAL_QUERY)
                    if mapped_intent in [QueryIntent.CREATE_PURCHASE, QueryIntent.CREATE_SALE, QueryIntent.CREATE_RECEIPT, QueryIntent.CREATE_PAYMENT]:
                        found_creation_intent = True

                    # Check for specific keywords to refine intent (ONLY if not already a creation intent)
                    if not found_creation_intent:
                        if "outstanding" in query_lower or "owe" in query_lower or "due" in query_lower:
                            mapped_intent = QueryIntent.OUTSTANDING
                        elif "stock" in query_lower or "inventory" in query_lower:
                            mapped_intent = QueryIntent.STOCK_CHECK
                        elif "revenue" in query_lower or "sales" in query_lower or "turnover" in query_lower:
                            mapped_intent = QueryIntent.SALES_SUMMARY
                        elif "purchase" in query_lower:
                            mapped_intent = QueryIntent.PURCHASE_SUMMARY
                        elif "top" in query_lower and "customer" in query_lower:
                            mapped_intent = QueryIntent.TOP_CUSTOMERS
                    elif "cash" in query_lower or "balance" in query_lower:
                        mapped_intent = QueryIntent.CASHBOOK
                    elif "pdf" in query_lower:
                        mapped_intent = QueryIntent.EXPORT_PDF
                    elif "excel" in query_lower or "xlsx" in query_lower:
                        mapped_intent = QueryIntent.EXPORT_EXCEL
                    elif "invoice" in query_lower or "voucher" in query_lower:
                        mapped_intent = QueryIntent.INVOICE_DETAILS
                    else:
                        mapped_intent = intent_mapping.get(llm_intent, QueryIntent.GENERAL_QUERY)
                    
                    # Extract entities from LLM result
                    entities = {}
                    if intent_obj and hasattr(intent_obj, 'parameters'):
                        params = intent_obj.parameters or {}
                        if params.get('party_name'):
                            entities['party_name'] = params['party_name']
                        if params.get('item_name'):
                            entities['item_name'] = params['item_name']
                        if params.get('date_from'):
                            entities['date_from'] = params['date_from']
                        if params.get('date_to'):
                            entities['date_to'] = params['date_to']
                        if params.get('amount'):
                            entities['amount'] = params['amount']
                        if params.get('quantity'):
                            entities['quantity'] = params['quantity']
                    
                    # Also extract with regex for completeness
                    regex_entities = self._extract_entities(query)
                    entities.update({k: v for k, v in regex_entities.items() if k not in entities})
                    
                    # Detect date range from query
                    entities = self._add_date_range(query_lower, entities)
                    
                    # Detect format request
                    format_requested = None
                    if re.search(r'\bpdf\b', query_lower):
                        format_requested = "pdf"
                    elif re.search(r'\b(excel|xlsx|xls)\b', query_lower):
                        format_requested = "excel"
                    
                    return ParsedQuery(
                        intent=mapped_intent,
                        confidence=llm_confidence,
                        entities=entities,
                        original_query=query,
                        format_requested=format_requested
                    )
        except Exception as e:
            logger.warning(f"LLM intent recognition failed: {e}, falling back to regex")
        
        # ============ REGEX FALLBACK ============
        best_intent = QueryIntent.GENERAL_QUERY
        best_confidence = 0.0
        
        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    confidence = 0.8 + (len(pattern) / 200)
                    
                    if intent in [QueryIntent.EXPORT_PDF, QueryIntent.EXPORT_EXCEL]:
                        confidence += 0.2
                    elif intent == QueryIntent.INVOICE_DETAILS and ("pdf" in query_lower or "send" in query_lower):
                        confidence -= 0.3

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_intent = intent
        
        # Extract entities
        entities = self._extract_entities(query)
        entities = self._add_date_range(query_lower, entities)
        
        # Detect format request
        format_requested = None
        if re.search(r'\bpdf\b', query_lower):
            format_requested = "pdf"
        elif re.search(r'\b(excel|xlsx|xls)\b', query_lower):
            format_requested = "excel"
        
        return ParsedQuery(
            intent=best_intent,
            confidence=best_confidence,
            entities=entities,
            original_query=query,
            format_requested=format_requested
        )
    
    def _add_date_range(self, query_lower: str, entities: Dict) -> Dict:
        """Add date range to entities based on query keywords"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        
        if "last month" in query_lower:
            first_of_this_month = now.replace(day=1)
            last_month_end = first_of_this_month - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            entities['date_from'] = last_month_start
            entities['date_to'] = last_month_end
            entities['date_range'] = "Last Month"
        elif "this month" in query_lower:
            entities['date_from'] = now.replace(day=1)
            entities['date_to'] = now
            entities['date_range'] = "This Month"
        elif "this week" in query_lower:
            start_of_week = now - timedelta(days=now.weekday())
            entities['date_from'] = start_of_week
            entities['date_to'] = now
            entities['date_range'] = "This Week"
        elif "today" in query_lower:
            entities['date_from'] = now.replace(hour=0, minute=0, second=0)
            entities['date_to'] = now
            entities['date_range'] = "Today"
        elif "yesterday" in query_lower:
            yesterday = now - timedelta(days=1)
            entities['date_from'] = yesterday.replace(hour=0, minute=0, second=0)
            entities['date_to'] = yesterday.replace(hour=23, minute=59, second=59)
            entities['date_range'] = "Yesterday"
        
        return entities
    
    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract named entities from query"""
        entities = {}
        
        for entity_type, patterns in ENTITY_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value:
                        entities[entity_type] = value
                        break
        
        # Parse date range to actual dates
        if "date_range" in entities:
            entities["date_from"], entities["date_to"] = self._parse_date_range(entities["date_range"])
        
        # Parse limit to int
        if "limit" in entities:
            try:
                entities["limit"] = int(entities["limit"])
            except:
                entities["limit"] = 10
        
        return entities
    
    def _parse_date_range(self, date_str: str) -> Tuple[datetime, datetime]:
        """Convert date string to actual datetime range"""
        today = datetime.now()
        date_str = date_str.lower()
        
        month_map = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12
        }
        
        if date_str in month_map:
            month = month_map[date_str]
            year = today.year if month <= today.month else today.year - 1
            date_from = datetime(year, month, 1)
            # Last day of month
            if month == 12:
                date_to = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                date_to = datetime(year, month + 1, 1) - timedelta(days=1)
            return date_from, date_to
        
        if date_str == "this month":
            date_from = datetime(today.year, today.month, 1)
            return date_from, today
        
        if date_str == "last month":
            first_of_this_month = datetime(today.year, today.month, 1)
            date_to = first_of_this_month - timedelta(days=1)
            date_from = datetime(date_to.year, date_to.month, 1)
            return date_from, date_to
        
        if date_str == "today":
            date_from = datetime(today.year, today.month, today.day)
            return date_from, today
        
        if date_str == "yesterday":
            yesterday = today - timedelta(days=1)
            date_from = datetime(yesterday.year, yesterday.month, yesterday.day)
            date_to = date_from + timedelta(hours=23, minutes=59, seconds=59)
            return date_from, date_to
        
        # Default: Current FY
        if today.month >= 4:
            date_from = datetime(today.year, 4, 1)
        else:
            date_from = datetime(today.year - 1, 4, 1)
        return date_from, today
    
    def _get_handler(self, intent: QueryIntent):
        """Get the appropriate handler function for an intent"""
        handlers = {
            QueryIntent.OUTSTANDING: self._handle_outstanding,
            QueryIntent.PAYMENT_HISTORY: self._handle_payment_history,
            QueryIntent.CUSTOMER_360: self._handle_customer_360,
            QueryIntent.STOCK_CHECK: self._handle_stock_check,
            QueryIntent.ITEM_RATE: self._handle_item_rate,
            QueryIntent.SALES_SUMMARY: self._handle_sales_summary,
            QueryIntent.PURCHASE_SUMMARY: self._handle_purchase_summary,
            QueryIntent.TOP_CUSTOMERS: self._handle_top_customers,
            QueryIntent.TOP_ITEMS: self._handle_top_items,
            QueryIntent.CASHBOOK: self._handle_cashbook,
            QueryIntent.EXPORT_PDF: self._handle_export_pdf,
            QueryIntent.EXPORT_EXCEL: self._handle_export_excel,
            QueryIntent.INVOICE_DETAILS: self._handle_invoice_details,
            QueryIntent.RECENT_VOUCHERS: self._handle_recent_vouchers,
            QueryIntent.CREATE_RECEIPT: self._handle_create_receipt,
            QueryIntent.CREATE_PAYMENT: self._handle_create_payment,
            QueryIntent.CREATE_SALE: self._handle_create_sale,
            QueryIntent.CREATE_PURCHASE: self._handle_create_purchase,
            QueryIntent.GENERAL_QUERY: self._handle_general,
        }
        return handlers.get(intent, self._handle_general)
    
    # ============== INTENT HANDLERS ==============
    
    def _handle_outstanding(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle outstanding/due queries"""
        party_name = parsed.entities.get("party_name")
        
        if party_name:
            # Specific party outstanding
            return self._get_party_outstanding(party_name)
        else:
            # Overall outstanding summary
            return self._get_overall_outstanding()
    
    def _get_party_outstanding(self, party_name: str) -> OrchestrationResult:
        """Get outstanding for a specific party"""
        # Find the ledger
        ledger = self.db.query(Ledger).filter(
            Ledger.name.ilike(f"%{party_name}%"),
            Ledger.tenant_id == self.tenant_id
        ).first()
        
        if not ledger:
            return OrchestrationResult(
                success=False,
                data={},
                formatted_response=f"âŒ Party '{party_name}' not found. Check spelling or try a different name.",
                error="Party not found"
            )
        
        # Get outstanding bills
        bills = self.db.query(Bill).filter(
            Bill.party_name.ilike(f"%{ledger.name}%"),
            Bill.amount > 0,
            Bill.tenant_id == self.tenant_id
        ).order_by(desc(Bill.due_date)).all()
        
        total_outstanding = sum(b.amount or 0 for b in bills) # Corrected field: amount fields are positive for receivables
        
        # Safe overdue check
        from datetime import datetime
        overdue_amount = 0.0
        now = datetime.now()
        for b in bills:
            if b.amount and b.due_date:
                try:
                    # ensure b.due_date is comparable
                    if b.due_date < now:
                        overdue_amount += b.amount
                except:
                    pass
        
        # Format response (concise for WhatsApp)
        response_lines = [
            f"ðŸ“Š **{ledger.name}** - Outstanding Summary",
            "",
            f"ðŸ’° Total Due: â‚¹{total_outstanding:,.2f}",
        ]
        
        if overdue_amount > 0:
            response_lines.append(f"âš ï¸ Overdue: â‚¹{overdue_amount:,.2f}")
        
        # Show top 3 bills only (not all 100)
        if bills:
            response_lines.append("")
            response_lines.append("ðŸ“‹ Top Bills:")
            for i, bill in enumerate(bills[:3]):
                due_str = bill.due_date.strftime("%d-%b") if bill.due_date else "N/A"
                response_lines.append(f"  {i+1}. â‚¹{bill.amount:,.0f} (Due: {due_str})")
            
            if len(bills) > 3:
                response_lines.append(f"  ... and {len(bills) - 3} more bills")
        
        # Add action options
        response_lines.extend([
            "",
            "Reply:",
            "1ï¸âƒ£ PDF Statement",
            "2ï¸âƒ£ Full Details", 
            "3ï¸âƒ£ Send Reminder"
        ])
        
        return OrchestrationResult(
            success=True,
            data={
                "ledger_id": ledger.id,
                "party_name": ledger.name,
                "total_outstanding": total_outstanding,
                "overdue_amount": overdue_amount,
                "bill_count": len(bills),
                "top_bills": [{"amount": b.amount, "due_date": str(b.due_date)} for b in bills[:5]]
            },
            formatted_response="\n".join(response_lines)
        )
    
    def _get_overall_outstanding(self) -> OrchestrationResult:
        """Get overall receivables and payables summary"""
        # Sum all receivables (Sundry Debtors)
        receivables = self.db.query(func.sum(Ledger.closing_balance)).filter(
            Ledger.under_group.ilike("%sundry debtor%"),
            Ledger.closing_balance > 0,
            Ledger.tenant_id == self.tenant_id
        ).scalar() or 0
        
        # Sum all payables (Sundry Creditors)
        payables = self.db.query(func.sum(Ledger.closing_balance)).filter(
            Ledger.under_group.ilike("%sundry creditor%"),
            Ledger.closing_balance < 0,
            Ledger.tenant_id == self.tenant_id
        ).scalar() or 0
        payables = abs(payables)
        
        # Get top 5 debtors
        top_debtors = self.db.query(Ledger).filter(
            Ledger.under_group.ilike("%sundry debtor%"),
            Ledger.closing_balance > 0,
            Ledger.tenant_id == self.tenant_id
        ).order_by(desc(Ledger.closing_balance)).limit(5).all()
        
        response_lines = [
            "ðŸ“Š **Overall Outstanding Summary**",
            "",
            f"ðŸ“¥ Receivables: â‚¹{receivables:,.0f}",
            f"ðŸ“¤ Payables: â‚¹{payables:,.0f}",
            f"ðŸ“ˆ Net: â‚¹{receivables - payables:,.0f}",
            "",
            "ðŸ” Top 5 Debtors:"
        ]
        
        for i, ledger in enumerate(top_debtors):
            response_lines.append(f"  {i+1}. {ledger.name}: â‚¹{ledger.closing_balance:,.0f}")
        
        response_lines.extend([
            "",
            "Reply with party name for details (e.g., 'ABC Corp outstanding')"
        ])
        
        return OrchestrationResult(
            success=True,
            data={
                "receivables": receivables,
                "payables": payables,
                "net": receivables - payables,
                "top_debtors": [{"name": l.name, "amount": l.closing_balance} for l in top_debtors]
            },
            formatted_response="\n".join(response_lines)
        )
    
    def _handle_payment_history(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle payment history queries"""
        party_name = parsed.entities.get("party_name")
        date_from = parsed.entities.get("date_from", datetime.now() - timedelta(days=30))
        date_to = parsed.entities.get("date_to", datetime.now())
        
        # Query receipt vouchers
        query = self.db.query(Voucher).filter(
            Voucher.voucher_type.in_(["Receipt", "Payment"]),
            Voucher.date >= date_from,
            Voucher.date <= date_to,
            Voucher.tenant_id == self.tenant_id
        )
        
        if party_name:
            query = query.filter(Voucher.party_ledger_name.ilike(f"%{party_name}%"))
        
        vouchers = query.order_by(desc(Voucher.date)).limit(10).all()
        
        total_receipts = sum(v.amount or 0 for v in vouchers if v.voucher_type == "Receipt")
        total_payments = sum(v.amount or 0 for v in vouchers if v.voucher_type == "Payment")
        
        period = parsed.entities.get("date_range", "Last 30 days")
        
        response_lines = [
            f"ðŸ’³ **Payment History** - {period}",
            f"ðŸ‘¤ Party: {party_name or 'All Parties'}",
            "",
            f"ðŸ“¥ Total Receipts: â‚¹{total_receipts:,.0f}",
            f"ðŸ“¤ Total Payments: â‚¹{total_payments:,.0f}",
            "",
            "ðŸ“‹ Recent Transactions:"
        ]
        
        for v in vouchers[:5]:
            icon = "ðŸ“¥" if v.voucher_type == "Receipt" else "ðŸ“¤"
            date_str = v.date.strftime("%d-%b") if v.date else "N/A"
            response_lines.append(f"  {icon} {date_str}: â‚¹{v.amount:,.0f}")
        
        return OrchestrationResult(
            success=True,
            data={
                "total_receipts": total_receipts,
                "total_payments": total_payments,
                "transaction_count": len(vouchers),
                "transactions": [{"date": str(v.date), "type": v.voucher_type, "amount": v.amount} for v in vouchers]
            },
            formatted_response="\n".join(response_lines)
        )
    
    def _handle_customer_360(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle complete customer profile request"""
        party_name = parsed.entities.get("party_name")
        
        if not party_name:
            return OrchestrationResult(
                success=False,
                data={},
                formatted_response="â“ Which customer? Please specify the name (e.g., 'Full profile of ABC Corp')",
            )
        
        # Redirect to Customer 360 API
        # For now, return a summary with link to full view
        ledger = self.db.query(Ledger).filter(
            Ledger.name.ilike(f"%{party_name}%"),
            Ledger.tenant_id == self.tenant_id
        ).first()
        
        if not ledger:
            return OrchestrationResult(
                success=False,
                data={},
                formatted_response=f"âŒ Customer '{party_name}' not found."
            )
        
        # Get quick summary
        total_sales = self.db.query(func.sum(Voucher.amount)).filter(
            Voucher.party_ledger_name.ilike(f"%{ledger.name}%"),
            Voucher.voucher_type == "Sales",
            Voucher.tenant_id == self.tenant_id
        ).scalar() or 0
        
        outstanding = ledger.closing_balance or 0
        
        response_lines = [
            f"ðŸ‘¤ **{ledger.name}** - 360Â° Profile",
            "",
            f"ðŸ“Š Type: {ledger.ledger_type or 'Customer'}",
            f"ðŸ’° Total Sales: â‚¹{total_sales:,.0f}",
            f"âš¡ Outstanding: â‚¹{outstanding:,.0f}",
            f"ðŸ“ Group: {ledger.under_group or 'N/A'}",
            "",
            "ðŸ”— Full Details: Open K24 Dashboard â†’ Customers â†’ Search"
        ]
        
        return OrchestrationResult(
            success=True,
            data={
                "ledger_id": ledger.id,
                "name": ledger.name,
                "total_sales": total_sales,
                "outstanding": outstanding
            },
            formatted_response="\n".join(response_lines)
        )
    
    def _handle_stock_check(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle stock/inventory queries"""
        item_name = parsed.entities.get("item_name")
        
        if item_name:
            # Specific item stock
            item = self.db.query(StockItem).filter(
                StockItem.name.ilike(f"%{item_name}%"),
                StockItem.tenant_id == self.tenant_id
            ).first()
            
            if not item:
                return OrchestrationResult(
                    success=False,
                    data={},
                    formatted_response=f"âŒ Item '{item_name}' not found. Check spelling or try a different name."
                )
            
            response_lines = [
                f"ðŸ“¦ **{item.name}** - Stock Status",
                "",
                f"ðŸ“Š Quantity: {item.closing_stock or 0} {item.unit or 'units'}",
                f"ðŸ’° Last Sale Rate: â‚¹{item.last_sale_rate or 0:,.2f}",
                f"ðŸ­ Last Purchase Rate: â‚¹{item.last_purchase_rate or 0:,.2f}",
            ]
            
            if item.default_godown:
                response_lines.append(f"ðŸ“ Godown: {item.default_godown}")
            
            # Reorder suggestion
            if (item.closing_stock or 0) < (item.reorder_level or 10):
                response_lines.extend([
                    "",
                    f"âš ï¸ **LOW STOCK** - Consider reordering!"
                ])
            
            return OrchestrationResult(
                success=True,
                data={
                    "item_name": item.name,
                    "quantity": item.closing_stock,
                    "unit": item.unit,
                    "last_sale_rate": item.last_sale_rate,
                    "last_purchase_rate": item.last_purchase_rate
                },
                formatted_response="\n".join(response_lines)
            )
        else:
            # Overall stock summary
            items = self.db.query(StockItem).filter(
                StockItem.tenant_id == self.tenant_id,
                StockItem.closing_stock > 0
            ).order_by(desc(StockItem.closing_stock)).limit(10).all()
            
            total_items = self.db.query(func.count(StockItem.id)).filter(
                StockItem.tenant_id == self.tenant_id
            ).scalar() or 0
            
            response_lines = [
                "ðŸ“¦ **Inventory Summary**",
                "",
                f"ðŸ“Š Total Items: {total_items}",
                "",
                "ðŸ” Top Items by Stock:"
            ]
            
            for i, item in enumerate(items[:5]):
                response_lines.append(f"  {i+1}. {item.name}: {item.closing_stock or 0} {item.unit or ''}")
            
            response_lines.extend([
                "",
                "Ask about specific item: 'Stock of [item name]'"
            ])
            
            return OrchestrationResult(
                success=True,
                data={"total_items": total_items, "items": [{"name": i.name, "stock": i.closing_stock} for i in items]},
                formatted_response="\n".join(response_lines)
            )
    
    def _handle_item_rate(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle rate/price queries"""
        item_name = parsed.entities.get("item_name")
        
        if not item_name:
            return OrchestrationResult(
                success=False,
                data={},
                formatted_response="â“ Which item's rate do you want? (e.g., 'Rate of Product A')"
            )
        
        item = self.db.query(StockItem).filter(
            StockItem.name.ilike(f"%{item_name}%"),
            StockItem.tenant_id == self.tenant_id
        ).first()
        
        if not item:
            return OrchestrationResult(
                success=False,
                data={},
                formatted_response=f"âŒ Item '{item_name}' not found."
            )
        
        response_lines = [
            f"ðŸ’° **{item.name}** - Rate Info",
            "",
            f"ðŸ“ˆ Last Sale Rate: â‚¹{item.last_sale_rate or 0:,.2f}",
            f"ðŸ“‰ Last Purchase Rate: â‚¹{item.last_purchase_rate or 0:,.2f}",
            f"ðŸ“Š Margin: {((item.last_sale_rate or 0) - (item.last_purchase_rate or 0)):,.2f}"
        ]
        
        return OrchestrationResult(
            success=True,
            data={
                "item_name": item.name,
                "sale_rate": item.last_sale_rate,
                "purchase_rate": item.last_purchase_rate
            },
            formatted_response="\n".join(response_lines)
        )
    
    def _handle_sales_summary(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle sales summary queries"""
        date_from = parsed.entities.get("date_from", datetime.now() - timedelta(days=30))
        date_to = parsed.entities.get("date_to", datetime.now())
        period = parsed.entities.get("date_range", "Current Period")
        
        # Get sales vouchers
        sales = self.db.query(Voucher).filter(
            Voucher.voucher_type == "Sales",
            Voucher.date >= date_from,
            Voucher.date <= date_to,
            Voucher.tenant_id == self.tenant_id
        ).all()
        
        total_sales = sum(v.amount or 0 for v in sales)
        voucher_count = len(sales)
        avg_sale = total_sales / voucher_count if voucher_count else 0
        
        # Top customers
        from collections import Counter
        party_sales = Counter()
        for v in sales:
            if v.party_name:
                party_sales[v.party_name] += v.amount or 0
        
        top_customers = party_sales.most_common(3)
        
        response_lines = [
            f"ðŸ“ˆ **Sales Summary** - {period}",
            "",
            f"ðŸ’° Total Sales: â‚¹{total_sales:,.0f}",
            f"ðŸ“Š Invoices: {voucher_count}",
            f"ðŸ“ˆ Avg Sale: â‚¹{avg_sale:,.0f}",
            "",
            "ðŸ† Top Customers:"
        ]
        
        for i, (name, amount) in enumerate(top_customers):
            response_lines.append(f"  {i+1}. {name}: â‚¹{amount:,.0f}")
        
        response_lines.extend([
            "",
            "Reply '2' for Excel export"
        ])
        
        return OrchestrationResult(
            success=True,
            data={
                "total_sales": total_sales,
                "voucher_count": voucher_count,
                "avg_sale": avg_sale,
                "top_customers": [{"name": n, "amount": a} for n, a in top_customers]
            },
            formatted_response="\n".join(response_lines)
        )
    
    def _handle_purchase_summary(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle purchase summary queries"""
        date_from = parsed.entities.get("date_from", datetime.now() - timedelta(days=30))
        date_to = parsed.entities.get("date_to", datetime.now())
        period = parsed.entities.get("date_range", "Current Period")
        
        purchases = self.db.query(Voucher).filter(
            Voucher.voucher_type == "Purchase",
            Voucher.date >= date_from,
            Voucher.date <= date_to,
            Voucher.tenant_id == self.tenant_id
        ).all()
        
        total_purchases = sum(v.amount or 0 for v in purchases)
        voucher_count = len(purchases)
        
        response_lines = [
            f"ðŸ“‰ **Purchase Summary** - {period}",
            "",
            f"ðŸ’¸ Total Purchases: â‚¹{total_purchases:,.0f}",
            f"ðŸ“Š Bills: {voucher_count}",
        ]
        
        return OrchestrationResult(
            success=True,
            data={"total_purchases": total_purchases, "bill_count": voucher_count},
            formatted_response="\n".join(response_lines)
        )
    
    def _handle_cashbook(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle cash balance queries"""
        # Find Cash ledger
        cash_ledgers = self.db.query(Ledger).filter(
            Ledger.under_group.ilike("%Cash-in-hand%"),
            Ledger.tenant_id == self.tenant_id
        ).all()
        
        if not cash_ledgers:
            return OrchestrationResult(
                success=True,
                data={},
                formatted_response="â„¹ï¸ No cash accounts found."
            )
        
        total_cash = sum(l.closing_balance or 0 for l in cash_ledgers)
        
        response_lines = [
            "ðŸ’µ **Cash Balance**",
            "",
            f"ðŸ’° Total: â‚¹{total_cash:,.2f}",
            ""
        ]
        
        for l in cash_ledgers:
            response_lines.append(f"- {l.name}: â‚¹{l.closing_balance:,.2f}")
            
        return OrchestrationResult(
            success=True,
            data={"total_cash": total_cash, "ledgers": [{"name": l.name, "balance": l.closing_balance} for l in cash_ledgers]},
            formatted_response="\n".join(response_lines)
        )

    def _handle_top_customers(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle top customers query"""
        limit = parsed.entities.get("limit", 10)
        
        # Query for Top Debtors with POSITIVE balance (since we fixed the sign)
        # We also include Creditors if they have a Debit (Positive) balance, 
        # because sometimes customers are classified as Creditors or have debit balances.
        top_customers = self.db.query(Ledger).filter(
            or_(
                Ledger.parent.ilike("%sundry debtor%"),
                Ledger.parent.ilike("%sundry creditor%")
            ),
            Ledger.tenant_id == self.tenant_id,
            Ledger.closing_balance > 0  # Only those who OWE money (Positive)
        ).order_by(desc(Ledger.closing_balance)).limit(limit).all()
        
        response_lines = [
            f"ðŸ† **Top {limit} Customers by Outstanding**",
            ""
        ]
        
        if not top_customers:
             response_lines.append("No customers with outstanding balance found.")
        
        for i, ledger in enumerate(top_customers):
            response_lines.append(f"  {i+1}. {ledger.name}: â‚¹{ledger.closing_balance or 0:,.0f}")
        
        return OrchestrationResult(
            success=True,
            data={"customers": [{"name": l.name, "balance": l.closing_balance} for l in top_customers]},
            formatted_response="\n".join(response_lines)
        )
    
    def _handle_top_items(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle top selling items query"""
        limit = parsed.entities.get("limit", 10)
        
        # Query voucher items to get best sellers
        from sqlalchemy import func
        top_items = self.db.query(
            StockItem.name.label("item_name"),
            func.sum(StockMovement.quantity).label("total_qty"),
            func.sum(StockMovement.amount).label("total_value")
        ).join(StockItem, StockMovement.item_id == StockItem.id)\
         .join(Voucher, StockMovement.voucher_id == Voucher.id).filter(
            Voucher.voucher_type == "Sales",
            Voucher.tenant_id == self.tenant_id
        ).group_by(StockItem.name).order_by(
            desc("total_value")
        ).limit(limit).all()
        
        response_lines = [
            f"ðŸ† **Top {limit} Selling Items**",
            ""
        ]
        
        for i, (name, qty, value) in enumerate(top_items):
            response_lines.append(f"  {i+1}. {name}: â‚¹{value or 0:,.0f} ({qty or 0} units)")
        
        return OrchestrationResult(
            success=True,
            data={"items": [{"name": n, "qty": q, "value": v} for n, q, v in top_items]},
            formatted_response="\n".join(response_lines)
        )
    
    def _handle_cashbook(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle cash balance query"""
        cash_ledger = self.db.query(Ledger).filter(
            or_(
                Ledger.name.ilike("%cash%"),
                Ledger.under_group.ilike("%cash%")
            ),
            Ledger.tenant_id == self.tenant_id
        ).first()
        
        cash_balance = cash_ledger.closing_balance if cash_ledger else 0
        
        response_lines = [
            "ðŸ’µ **Cash Status**",
            "",
            f"ðŸ’° Current Balance: â‚¹{cash_balance:,.0f}",
        ]
        
        return OrchestrationResult(
            success=True,
            data={"cash_balance": cash_balance},
            formatted_response="\n".join(response_lines)
        )
    
    def _handle_export_pdf(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle PDF export request - generates actual PDF file"""
        from services.export_service import ExportService
        
        export_service = ExportService(self.db, self.tenant_id)
        
        # Determine what type of PDF to generate
        invoice_number = parsed.entities.get("invoice_number")
        party_name = parsed.entities.get("party_name")
        
        if invoice_number:
            # Export specific invoice as PDF
            voucher = self.db.query(Voucher).filter(
                or_(
                    Voucher.voucher_number.ilike(f"%{invoice_number}%"),
                    Voucher.tally_voucher_id.ilike(f"%{invoice_number}%")
                ),
                Voucher.tenant_id == self.tenant_id
            ).first()
            
            if not voucher:
                return OrchestrationResult(
                    success=False,
                    data={},
                    formatted_response=f"âŒ Invoice '{invoice_number}' not found."
                )
            
            result = export_service.export_invoice_pdf(voucher.id)
            
            if result["success"]:
                return OrchestrationResult(
                    success=True,
                    data={
                        "export_type": "pdf",
                        "file_path": result["file_path"],
                        "filename": result["filename"]
                    },
                    formatted_response=f"ðŸ“„ Invoice PDF generated!\n\nðŸ“ File: {result['filename']}\n\nSending file...",
                    export_file=result["file_path"]
                )
            else:
                return OrchestrationResult(
                    success=False,
                    data={},
                    formatted_response=f"âŒ Failed to generate PDF: {result.get('error', 'Unknown error')}"
                )
        
        elif party_name:
            # Export outstanding statement for party
            result = export_service.export_statement_pdf(party_name)
            
            if result["success"]:
                return OrchestrationResult(
                    success=True,
                    data={
                        "export_type": "pdf",
                        "file_path": result["file_path"],
                        "filename": result["filename"]
                    },
                    formatted_response=f"ðŸ“„ Outstanding Statement PDF generated!\n\nðŸ“ File: {result['filename']}\n\nSending file...",
                    export_file=result["file_path"]
                )
            else:
                return OrchestrationResult(
                    success=False,
                    data={},
                    formatted_response=f"âŒ Failed to generate PDF: {result.get('error', 'Unknown error')}"
                )
        
        else:
            # Ask what they want to export
            return OrchestrationResult(
                success=True,
                data={"export_type": "pdf", "needs_clarification": True},
                formatted_response=(
                    "ðŸ“„ **PDF Export**\n\n"
                    "What would you like to export?\n\n"
                    "â€¢ 'Send invoice INV-001 as PDF'\n"
                    "â€¢ 'ABC Corp statement PDF'\n"
                    "â€¢ 'Outstanding statement of XYZ Industries'"
                )
            )
    
    def _handle_export_excel(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle Excel export request - generates actual Excel file"""
        from services.export_service import ExportService
        
        export_service = ExportService(self.db, self.tenant_id)
        
        query_lower = parsed.original_query.lower()
        date_from = parsed.entities.get("date_from")
        date_to = parsed.entities.get("date_to")
        
        # Determine what type of Excel to generate
        if "sale" in query_lower:
            result = export_service.export_sales_excel(date_from, date_to)
            report_type = "Sales Register"
        elif "purchase" in query_lower:
            result = export_service.export_purchase_excel(date_from, date_to)
            report_type = "Purchase Register"
        elif "outstanding" in query_lower or "receivable" in query_lower:
            result = export_service.export_outstanding_excel("receivable")
            report_type = "Outstanding Receivables"
        elif "payable" in query_lower:
            result = export_service.export_outstanding_excel("payable")
            report_type = "Outstanding Payables"
        elif "stock" in query_lower or "inventory" in query_lower:
            result = export_service.export_stock_excel()
            report_type = "Stock Report"
        else:
            # Default to sales
            result = export_service.export_sales_excel(date_from, date_to)
            report_type = "Sales Register"
        
        if result["success"]:
            return OrchestrationResult(
                success=True,
                data={
                    "export_type": "excel",
                    "report_type": report_type,
                    "file_path": result["file_path"],
                    "filename": result["filename"]
                },
                formatted_response=f"ðŸ“Š {report_type} Excel generated!\n\nðŸ“ File: {result['filename']}\n\nSending file...",
                export_file=result["file_path"]
            )
        else:
            return OrchestrationResult(
                success=False,
                data={},
                formatted_response=f"âŒ Failed to generate Excel: {result.get('error', 'Unknown error')}"
            )
    
    def _handle_invoice_details(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle invoice/voucher details query"""
        invoice_number = parsed.entities.get("invoice_number")
        
        if not invoice_number:
            return OrchestrationResult(
                success=False,
                data={},
                formatted_response="â“ Which invoice? Please specify (e.g., 'Show invoice INV-001')"
            )
        
        voucher = self.db.query(Voucher).filter(
            or_(
                Voucher.voucher_number.ilike(f"%{invoice_number}%"),
                Voucher.tally_voucher_id.ilike(f"%{invoice_number}%")
            ),
            Voucher.tenant_id == self.tenant_id
        ).first()
        
        if not voucher:
            return OrchestrationResult(
                success=False,
                data={},
                formatted_response=f"âŒ Invoice '{invoice_number}' not found."
            )
        
        # Get items with names
        results = self.db.query(StockMovement, StockItem.name).join(
            StockItem, StockMovement.item_id == StockItem.id
        ).filter(
            StockMovement.voucher_id == voucher.id
        ).all()
        
        # Convert to dictionary list for easy usage
        items = []
        for move, name in results:
            items.append({
                "item_name": name, 
                "quantity": move.quantity, 
                "rate": move.rate
            })
        
        # Safe Date Formatting
        date_str = "N/A"
        if voucher.date:
            try:
                if isinstance(voucher.date, str):
                    date_str = voucher.date
                else:
                    # Windows safely handles years > 1900
                    if voucher.date.year < 1900:
                         date_str = voucher.date.isoformat()
                    else:
                         date_str = voucher.date.strftime('%d-%b-%Y')
            except Exception:
                date_str = str(voucher.date)

        response_lines = [
            f"ðŸ§¾ **{voucher.voucher_type} - {voucher.voucher_number}**",
            "",
            f"ðŸ“… Date: {date_str}",
            f"ðŸ‘¤ Party: {voucher.party_ledger_name or 'N/A'}",
            f"ðŸ’° Total: â‚¹{voucher.amount or 0:,.2f}",
            "",
            "ðŸ“‹ Items:"
        ]
        
        for item in items[:5]:
            response_lines.append(f"  â€¢ {item['item_name']}: {item['quantity']} x â‚¹{item['rate'] or 0:,.0f}")
        
        if len(items) > 5:
            response_lines.append(f"  ... and {len(items) - 5} more items")
        
        return OrchestrationResult(
            success=True,
            data={
                "voucher_id": voucher.id,
                "voucher_number": voucher.voucher_number,
                "party": voucher.party_ledger_name,
                "amount": voucher.amount,
                "items": [{"name": i['item_name'], "qty": i['quantity'], "rate": i['rate']} for i in items]
            },
            formatted_response="\n".join(response_lines)
        )
    
    def _handle_recent_vouchers(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle recent vouchers query"""
        limit = parsed.entities.get("limit", 5)
        voucher_type = "Sales"  # Default
        
        if "purchase" in parsed.original_query.lower():
            voucher_type = "Purchase"
        
        vouchers = self.db.query(Voucher).filter(
            Voucher.voucher_type == voucher_type,
            Voucher.tenant_id == self.tenant_id
        ).order_by(desc(Voucher.date)).limit(limit).all()
        
        response_lines = [
            f"ðŸ“‹ **Last {limit} {voucher_type} Vouchers**",
            ""
        ]
        
        for v in vouchers:
            date_str = v.date.strftime("%d-%b") if v.date else "N/A"
            response_lines.append(f"  â€¢ {date_str}: {v.party_ledger_name or 'N/A'} - â‚¹{v.amount or 0:,.0f}")
        
        return OrchestrationResult(
            success=True,
            data={"vouchers": [{"date": str(v.date), "party": v.party_ledger_name, "amount": v.amount} for v in vouchers]},
            formatted_response="\n".join(response_lines)
        )
    
    def _handle_export_pdf(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle PDF export requests"""
        return OrchestrationResult(
            success=True,
            data={},
            formatted_response="â„¹ï¸ PDF export is coming soon."
        )

    def _handle_export_excel(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle Excel export requests"""
        return OrchestrationResult(
            success=True,
            data={},
            formatted_response="â„¹ï¸ Excel export is coming soon."
        )

    def _handle_invoice_details(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle invoice detail queries"""
        # Placeholder for now
        return OrchestrationResult(
            success=True,
            data={},
            formatted_response="â„¹ï¸ Invoice details view is coming soon."
        )

    def _handle_recent_vouchers(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle recent vouchers queries"""
        limit = 5
        vouchers = self.db.query(Voucher).filter(
            Voucher.tenant_id == self.tenant_id
        ).order_by(desc(Voucher.date)).limit(limit).all()
        
        response_lines = ["ðŸ“‹ **Recent Vouchers**", ""]
        for v in vouchers:
            response_lines.append(f"- {v.date.strftime('%d-%b')}: {v.voucher_type} - {v.party_ledger_name} (â‚¹{v.amount:,.0f})")
            
        return OrchestrationResult(
            success=True,
            data={"vouchers": [{"date": str(v.date), "party": v.party_ledger_name, "amount": v.amount} for v in vouchers]},
            formatted_response="\n".join(response_lines)
        )
    
    def _handle_create_receipt(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle receipt creation intent"""
        party = parsed.entities.get("party_name", "Unknown Party")
        amount = parsed.entities.get("amount", "0")
        
        return OrchestrationResult(
            success=True,
            data={},
            formatted_response=f"âœ… I understand you want to create a RECEIPT.\n\nðŸ‘¤ From: {party}\nðŸ’° Amount: â‚¹{amount}\n\n(â„¹ï¸ Voucher creation is in preview mode. This was NOT saved to Tally.)"
        )

    def _handle_create_payment(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle payment creation intent"""
        party = parsed.entities.get("party_name", "Unknown Party")
        amount = parsed.entities.get("amount", "0")
        
        return OrchestrationResult(
            success=True,
            data={},
            formatted_response=f"âœ… I understand you want to create a PAYMENT.\n\nðŸ‘¤ To: {party}\nðŸ’° Amount: â‚¹{amount}\n\n(â„¹ï¸ Voucher creation is in preview mode. This was NOT saved to Tally.)"
        )
        
    def _handle_create_sale(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle sale creation intent"""
        party = parsed.entities.get("party_name", "Cash")
        items = parsed.entities.get("item_name", "Items")
        qty = parsed.entities.get("quantity", "")
        
        return OrchestrationResult(
            success=True,
            data={},
            formatted_response=f"âœ… I understand you want to create a SALE.\n\nðŸ‘¤ Customer: {party}\nðŸ“¦ Item: {items} (Qty: {qty})\n\n(â„¹ï¸ Voucher creation is in preview mode. This was NOT saved to Tally.)"
        )

    def _handle_create_purchase(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Handle purchase creation intent"""
        party = parsed.entities.get("party_name", "Cash")
        items = parsed.entities.get("item_name", "Items")
        qty = parsed.entities.get("quantity", "")
        
        return OrchestrationResult(
            success=True,
            data={},
            formatted_response=f"âœ… I understand you want to create a PURCHASE.\n\nðŸ‘¤ Supplier: {party}\nðŸ“¦ Item: {items} (Qty: {qty})\n\n(â„¹ï¸ Voucher creation is in preview mode. This was NOT saved to Tally.)"
        )

    def _handle_general(self, parsed: ParsedQuery) -> OrchestrationResult:
        """Fallback handler for unrecognized queries"""
        return OrchestrationResult(
            success=True,
            data={"intent": "general"},
            formatted_response=(
                "ðŸ¤” I'm not sure what you're looking for. Try asking:\n\n"
                "ðŸ“Š Outstanding from [Party Name]\n"
                "ðŸ“¦ Stock of [Item Name]\n"
                "ðŸ“ˆ Last month revenue\n"
                "ðŸ“ˆ This month sales summary\n"
                "ðŸ† Top 10 customers\n"
                "ðŸ§¾ Show invoice [Number]\n"
                "ðŸ’µ Cash balance\n"
                "ðŸ“‹ Last 5 purchases"
            )
        )


# ============== CONVENIENCE FUNCTIONS ==============

def process_user_query(query: str, tenant_id: str = "default") -> OrchestrationResult:
    """
    Quick function to process a user query.
    
    Usage:
        result = process_user_query("How much does ABC Corp owe?")
        print(result.formatted_response)
    """
    db = SessionLocal()
    try:
        orchestrator = QueryOrchestrator(db, tenant_id)
        return orchestrator.process_query(query)
    finally:
        db.close()


def get_supported_queries() -> List[str]:
    """Return list of example queries the system supports"""
    return [
        "How much does ABC Corp owe?",
        "Outstanding from XYZ Industries",
        "ABC Corp payment history this month",
        "Stock of Product A",
        "What's the rate of Product B?",
        "January sales summary",
        "This month's purchases",
        "Top 10 customers",
        "Best selling items",
        "Cash balance today",
        "Show invoice INV-001",
        "Last 5 sales",
        "Export January sales to Excel",
        "Send invoice as PDF",
    ]

