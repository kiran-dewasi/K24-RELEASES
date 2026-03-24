"""
Intent Recognizer for KITTU
Uses Gemini to understand user intent from natural language.

Universal Design:
- Works with any accounting query
- Extensible intent system
- High accuracy with confidence scores
- Graceful fallback for ambiguous requests
"""
import json
import logging
from typing import Dict, Any, Optional, List
import os
import asyncio
from enum import Enum
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Supported intent types"""
    RECONCILE_INVOICES = "reconcile_invoices"
    CREATE_PURCHASE = "create_purchase"
    CREATE_SALE = "create_sale"
    CREATE_RECEIPT = "create_receipt"
    CREATE_PAYMENT = "create_payment"
    UPDATE_GSTIN = "update_gstin"
    UPDATE_LEDGER = "update_ledger"
    QUERY_DATA = "query_data"
    GENERATE_REPORT = "generate_report"
    CLARIFY_INTENT = "clarify_intent"
    UNKNOWN = "unknown"


class Intent(BaseModel):
    """
    Recognized user intent
    
    Attributes:
        action: Type of action to perform
        entity: Primary entity (party name, ledger name, etc.)
        parameters: Additional extracted parameters
        confidence: Confidence score (0.0-1.0)
        raw_query: Original user query
        is_fallback: Whether keyword fallback was used
    """
    action: IntentType
    entity: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    raw_query: str = ""
    is_fallback: bool = False
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1"""
        return max(0.0, min(1.0, v))
    
    def is_confident(self, threshold: float = 0.7) -> bool:
        """Check if confidence exceeds threshold"""
        return self.confidence >= threshold


class IntentRecognizer:
    """
    Recognize user intent from natural language using Gemini.
    
    Universal Features:
    - Handles any Tally-related query
    - Extracts structured parameters (amounts, dates, quantities)
    - Multiple language support (English, Hindi)
    - Confidence-based routing
    """
    
    # Intent examples for few-shot learning
    INTENT_EXAMPLES = {
        IntentType.RECONCILE_INVOICES: [
            "Reconcile invoices for Acme Corp",
            "Fix discrepancies for Vasudev Enterprises",
            "Check Ramesh Traders ledger for errors"
        ],
        IntentType.CREATE_PURCHASE: [
            "I bought 500 cumin bags from Vasudev Enterprises",
            "Purchase of 100 units from ABC Suppliers at Rs.2500",
            "Create purchase entry for Ramesh Traders"
        ],
        IntentType.CREATE_SALE: [
            "Sold 200 items to Customer ABC",
            "Create sale for Rs.50000 to XYZ Corp",
            "Sales entry for 100 units @500 each"
        ],
        IntentType.UPDATE_GSTIN: [
            "Update GSTIN for Vasudev Enterprises",
            "Add GST number for Acme Corp",
            "Change GSTIN to 12ABCDE1234F1Z5"
        ],
        IntentType.QUERY_DATA: [
            "What's my total revenue?",
            "Show me all parties with pending balances",
            "How much did Acme Corp purchase last month?"
        ],
        IntentType.GENERATE_REPORT: [
            "Generate P&L report",
            "Create balance sheet",
            "Show me party-wise outstanding report"
        ],
        IntentType.CREATE_RECEIPT: [
            "Receipt from Sharma for 5000",
            "Received 10000 from ABC Corp",
            "Create receipt for payment received from Customer X"
        ],
        IntentType.CREATE_PAYMENT: [
            "Payment to Vendor Y for 2000",
            "Paid 5000 to Sharma Traders",
            "Create payment voucher for electricity bill"
        ],
        IntentType.CLARIFY_INTENT: [
            "Add a transaction",
            "Create a voucher",
            "I want to add an entry",
            "New transaction for Vinayak Enterprises"
        ]
    }
    
    def __init__(self, api_key: str, use_pro: bool = False):
        """
        Initialize Intent Recognizer

        Args:
            api_key: Google AI API key
            use_pro: If True, use a more capable but heavier model
        """
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            # Use latest stable flash/pro models available for this key
            if use_pro:
                model = "gemini-2.0-flash"
            else:
                # Use lite model for speed and efficiency
                model = "gemini-2.0-flash"

            self.llm = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
                transport="rest",
                temperature=0.1,      # low temp for consistent classification
                max_output_tokens=500,
                max_retries=1,        # fail fast so we can use fallback
                # api_version left as default; SDK will use correct v1
            )
            logger.info(f"Initialized IntentRecognizer with model {model} (use_pro={use_pro})")

        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            # re-raise so the top-level classify_intent can handle fallback
            raise
    
    async def recognize(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Intent:
        """
        Recognize intent from user message

        Args:
            user_message: User's natural language input
            context: Optional conversation context

        Returns:
            Intent object with action, entity, parameters, and confidence
        """
        import time
        print(f"[INTENT_CALL] {time.strftime('%H:%M:%S')} â€” query: {user_message[:30]}")
        # Build prompt with context
        prompt = self._build_prompt(user_message, context)
        
        try:
            # Get LLM response
            response = await self.llm.ainvoke(prompt)
            
            # Parse JSON response
            result = self._parse_response(response.content, user_message)
            
            logger.info(
                f"Recognized intent: action={result.action}, "
                f"entity={result.entity}, confidence={result.confidence:.2f}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Intent recognition failed: {e}")
            # Return fallback intent using keyword matching
            return self._keyword_fallback(user_message)
    
    def _build_prompt(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build classification prompt"""
        
        # Extract context info
        company = context.get("company", "Unknown") if context else "Unknown"
        recent_history = context.get("conversation_history", [])[-2:] if context else []
        
        # Build examples
        examples_text = "\\n\\n".join([
            f"**{intent.value}:**\\n" + "\\n".join(f"  - {ex}" for ex in examples[:2])
            for intent, examples in self.INTENT_EXAMPLES.items()
        ])
        
        prompt = f"""You are an intent classifier for KITTU, an AI accounting assistant for TallyPrime.

USER MESSAGE: "{user_message}"

CONTEXT:
- Company: {company}
- Recent conversation: {json.dumps(recent_history, indent=2) if recent_history else "None"}

AVAILABLE INTENTS & EXAMPLES:
{examples_text}

TASK: Classify the user's intent and extract structured information.

EXTRACT:
1. **action**: One of the intent types above.
   - If the user says "add a transaction" or "create voucher" WITHOUT specifying type (Sale/Purchase/Receipt/Payment), use "clarify_intent".
   - If the user says "add a transaction for [Party]", use "clarify_intent" but extract the entity.

2. **entity**: Party/ledger name if mentioned (or null)
3. **parameters**: Extract any of these if present:
   - **quantity**: Number of items/units
   - **amount**: Total money value
   - **rate**: Price per unit
   - **item**: Item/product name
   - **date**: Transaction date
   - **gstin**: GST number
   
4. **confidence**: 0.0-1.0

RESPONSE FORMAT (JSON only, no markdown):
{{
  "action": "create_sale",
  "entity": "prince enterprises",
  "parameters": {{"quantity": 500}},
  "confidence": 0.95
}}

Return ONLY valid JSON, nothing else."""
        
        return prompt
    
    def _parse_response(self, response_text: str, original_query: str) -> Intent:
        """Parse LLM JSON response into Intent object"""
        try:
            # Clean response (remove markdown code blocks if present)
            response_text = response_text.strip()
            if response_text.startswith("```"):
                # Remove markdown code blocks
                lines = response_text.split("\\n")
                response_text = "\\n".join(
                    line for line in lines
                    if not line.strip().startswith("```")
                )
            
            # Parse JSON
            data = json.loads(response_text.strip())
            
            # Validate and normalize action
            action_str = data.get("action", "unknown")
            try:
                action = IntentType(action_str)
            except ValueError:
                logger.warning(f"Unknown intent type: {action_str}, using QUERY_DATA")
                action = IntentType.QUERY_DATA
            
            # Build Intent object
            intent = Intent(
                action=action,
                entity=data.get("entity"),
                parameters=data.get("parameters", {}),
                confidence=float(data.get("confidence", 0.5)),
                raw_query=original_query,
                is_fallback=False
            )
            
            return intent
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            
            # Fallback: Try keyword matching
            return self._keyword_fallback(original_query)
        
        except Exception as e:
            logger.error(f"Intent parsing error: {e}")
            return self._keyword_fallback(original_query)
    
    def _keyword_fallback(self, query: str) -> Intent:
        """Fallback keyword-based intent recognition with entity extraction"""
        from entity_extractor import extract_entity_fallback, extract_parameters_fallback
        
        query_lower = query.lower()
        
        # Keyword mapping
        if any(word in query_lower for word in ["reconcile", "fix", "check", "discrepancy"]):
            action = IntentType.RECONCILE_INVOICES
            confidence = 0.6
        elif any(word in query_lower for word in ["bought", "purchase", "buy"]):
            action = IntentType.CREATE_PURCHASE
            confidence = 0.6
        elif "from" in query_lower and any(w in query_lower for w in ["bag", "kg", "nos", "pcs", "item", "inr", "rs"]):
            # Implicit Purchase: "500 bags FROM xyz"
            action = IntentType.CREATE_PURCHASE
            confidence = 0.55
        elif any(word in query_lower for word in ["sold", "sale", "sell"]):
            action = IntentType.CREATE_SALE
            confidence = 0.6
        elif "to" in query_lower and any(w in query_lower for w in ["bag", "kg", "nos", "pcs", "item", "inr", "rs"]):
            # Implicit Sale: "500 bags TO xyz"
            action = IntentType.CREATE_SALE
            confidence = 0.55
        elif any(word in query_lower for word in ["receipt", "received", "got payment", "collect"]):
            action = IntentType.CREATE_RECEIPT
            confidence = 0.6
        elif any(word in query_lower for word in ["payment", "paid", "pay", "expense"]):
            action = IntentType.CREATE_PAYMENT
            confidence = 0.6
        elif any(word in query_lower for word in ["gstin", "gst number", "tax id"]):
            action = IntentType.UPDATE_GSTIN
            confidence = 0.6
        elif any(word in query_lower for word in ["report", "generate", "show report"]):
            action = IntentType.GENERATE_REPORT
            confidence = 0.6
        elif any(word in query_lower for word in ["transaction", "voucher", "entry"]):
            action = IntentType.CLARIFY_INTENT
            confidence = 0.5
        else:
            action = IntentType.QUERY_DATA
            confidence = 0.4
        
        # Extract entity and parameters using regex fallback
        entity = extract_entity_fallback(query, action.value)
        parameters = extract_parameters_fallback(query)
        
        logger.info(f"Fallback keyword matching: {action.value} (confidence: {confidence}), entity: {entity}, params: {parameters}")
        
        return Intent(
            action=action,
            entity=entity,
            parameters=parameters,
            confidence=confidence,
            raw_query=query,
            is_fallback=True
        )
    
    def get_supported_intents(self) -> List[Dict[str, Any]]:
        """Get list of supported intents with examples"""
        return [
            {
                "intent": intent.value,
                "examples": examples,
                "description": self._get_intent_description(intent)
            }
            for intent, examples in self.INTENT_EXAMPLES.items()
        ]
    
    @staticmethod
    def _get_intent_description(intent: IntentType) -> str:
        """Get human-readable intent description"""
        descriptions = {
            IntentType.RECONCILE_INVOICES: "Find and fix discrepancies in invoices",
            IntentType.CREATE_PURCHASE: "Create a purchase voucher/entry",
            IntentType.CREATE_SALE: "Create a sales voucher/entry",
            IntentType.UPDATE_GSTIN: "Update GST number for a party",
            IntentType.UPDATE_LEDGER: "Update ledger information",
            IntentType.QUERY_DATA: "Ask questions about accounting data",
            IntentType.GENERATE_REPORT: "Generate accounting reports",
            IntentType.CLARIFY_INTENT: "Ask for clarification on ambiguous requests",
            IntentType.UNKNOWN: "Unrecognized request"
        }
        return descriptions.get(intent, "Unknown intent")

    def _get_response_for_intent(self, intent: Intent) -> str:
        """Get a conversational response for the intent"""
        responses = {
            IntentType.RECONCILE_INVOICES: "I can help you reconcile invoices. Which party should we check?",
            IntentType.CREATE_PURCHASE: "Let's record a purchase. Who is the supplier?",
            IntentType.CREATE_SALE: "Okay, creating a sales invoice. Who is the customer?",
            IntentType.UPDATE_GSTIN: "I can update the GSTIN. Which party is this for?",
            IntentType.UPDATE_LEDGER: "Sure, I can update ledger details. Which ledger?",
            IntentType.QUERY_DATA: "I can help you with that. You can ask about sales, purchases, or specific ledgers.",
            IntentType.GENERATE_REPORT: "I can generate reports like P&L, Balance Sheet, or Outstanding Receivables.",
            IntentType.CREATE_RECEIPT: "Recording a receipt. Who is the payment from?",
            IntentType.CREATE_PAYMENT: "Recording a payment. Who are you paying?",
            IntentType.CLARIFY_INTENT: f"I can create a transaction for {intent.entity or 'you'}. Is this a Sale, Purchase, Receipt, or Payment?",
            IntentType.UNKNOWN: "I'm not sure I understand. Could you rephrase that?"
        }
        return responses.get(intent.action, "How can I help you with that?")


async def classify_intent(
    api_key: str,
    user_message: str,
    context: Optional[Dict[str, Any]] = None,
    use_pro: bool = False,
) -> Dict[str, Any]:
    """
    High-level helper to classify intent with Gemini, with safe fallback.

    Returns a dict:
    {
        "intent": str,          # IntentType.value
        "confidence": float,    # 0.0 - 1.0
        "fallback": bool,       # True if keyword-based fallback was used
        "intent_obj": Intent,   # The full Intent Pydantic object
    }
    """
    recognizer: Optional[IntentRecognizer] = None

    try:
        # Try to init Gemini-based recognizer
        recognizer = IntentRecognizer(api_key=api_key, use_pro=use_pro)
        intent_obj = await recognizer.recognize(user_message, context)

    except Exception as e:
        logger.error(f"Top-level intent classification error, using fallback: {e}")

        # If recognizer instance is available, use its fallback
        if recognizer is not None:
            intent_obj = recognizer._keyword_fallback(user_message)
        else:
            # Last-resort static fallback if init itself fails
            # Minimal dependency to avoid circular imports
            from entity_extractor import (
                extract_entity_fallback,
                extract_parameters_fallback,
            )
            query_lower = user_message.lower()

            # Very simple default mapping
            if any(w in query_lower for w in ["receipt", "received", "got payment", "collect"]):
                action = IntentType.CREATE_RECEIPT
                confidence = 0.5
            elif any(w in query_lower for w in ["payment", "paid", "pay", "expense"]):
                action = IntentType.CREATE_PAYMENT
                confidence = 0.5
            else:
                action = IntentType.QUERY_DATA
                confidence = 0.4

            entity = extract_entity_fallback(user_message, action.value)
            parameters = extract_parameters_fallback(user_message)

            intent_obj = Intent(
                action=action,
                entity=entity,
                parameters=parameters,
                confidence=confidence,
                raw_query=user_message,
                is_fallback=True,
            )

    return {
        "intent": intent_obj.action.value,
        "confidence": intent_obj.confidence,
        "fallback": intent_obj.is_fallback,
        "intent_obj": intent_obj,
    }


if __name__ == "__main__":
    async def _self_test():
        api_key = os.getenv("GOOGLE_API_KEY", "")
        if not api_key:
            print("GOOGLE_API_KEY not set, will likely hit fallback only.")
        result = await classify_intent(
            api_key=api_key,
            user_message="Kal 10,000 ka receipt Sharma & Co ke naam se banao",
            context={"company": "Demo Co"},
        )
        print(result)

    asyncio.run(_self_test())

