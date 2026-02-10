# K24 AI Agent - Intent Classifier
# =================================
# Parses user natural language into structured intents and parameters

from typing import Dict, Any, Tuple, Optional, List
import logging
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import os
import json

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Classifies user intent and extracts parameters using Gemini.
    Supports multiple intent types with confidence scoring.
    """
    
    SUPPORTED_INTENTS = [
        "create_invoice",
        "create_receipt", 
        "create_payment",
        "create_sales",
        "query_data",
        "audit_transactions",
        "update_ledger",
        "unknown"
    ]
    
    def __init__(self, api_key: str = None, model_name: str = "gemini-2.0-flash-exp"):
        """Initialize with Gemini model optimized for intent classification"""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY must be provided")
        
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self.api_key,
            temperature=0.1,  # Low temperature for consistency
            max_tokens=500
        )
    
    def classify(self, user_message: str) -> Tuple[str, float, Dict[str, Any]]:
        """
        Classify intent and extract parameters.
        Returns: (intent, confidence, parameters)
        """
        
        # Quick pattern matching for common intents
        quick_match = self._quick_pattern_match(user_message)
        if quick_match:
            intent, params = quick_match
            logger.info(f"Quick pattern match: {intent}")
            return (intent, 0.95, params)
        
        # Use LLM for complex cases
        try:
            print(f"[INTENT] Classifying message: {user_message}")
            result = self._llm_classify(user_message)
            print(f"[INTENT] Classified as: {result[0]} (confidence: {result[1]})")
            return result
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            print(f"[INTENT ERROR] {e}")
            return ("unknown", 0.0, {})
    
    def _quick_pattern_match(self, message: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Fast pattern matching for common intents.
        Returns (intent, params) or None if no match.
        """
        message_lower = message.lower()
        
        # Create invoice patterns
        if any(word in message_lower for word in ["invoice", "bill", "sales"]):
            params = self._extract_transaction_params(message)
            if params.get("party_name") and params.get("amount"):
                intent = "create_invoice" if "invoice" in message_lower or "bill" in message_lower else "create_sales"
                return (intent, params)
        
        # Receipt patterns
        if any(word in message_lower for word in ["receipt", "received", "payment received", "got payment"]):
            params = self._extract_transaction_params(message)
            if params.get("party_name") and params.get("amount"):
                return ("create_receipt", params)
        
        # Payment patterns
        if any(word in message_lower for word in ["pay", "paid", "payment"]) and "received" not in message_lower:
            params = self._extract_transaction_params(message)
            if params.get("party_name") and params.get("amount"):
                return ("create_payment", params)
        
        # Query patterns
        if any(word in message_lower for word in ["show", "list", "what", "how much", "outstanding"]):
            return ("query_data", {"query": message})
        
        # Audit patterns
        if any(word in message_lower for word in ["audit", "check", "verify", "compliance"]):
            return ("audit_transactions", {"query": message})
        
        return None
    
    def _extract_transaction_params(self, message: str) -> Dict[str, Any]:
        """Extract transaction parameters using regex patterns"""
        params = {}
        
        # Extract amount (₹50000, 50000, 50,000, Rs. 50000)
        amount_patterns = [
            r'₹\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'Rs\.?\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'rupees?\s*([0-9,]+(?:\.[0-9]{2})?)',
            r'(?:for|of|amount)\s+([0-9,]+(?:\.[0-9]{2})?)',
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    params["amount"] = float(amount_str)
                    break
                except ValueError:
                    pass
        
        # Extract party name (common patterns)
        party_patterns = [
            r'(?:to|from|for)\s+([A-Z][A-Za-z\s&.-]+?)(?:\s+for|\s+of|$)',
            r'(?:customer|party|ledger)\s+([A-Z][A-Za-z\s&.-]+?)(?:\s+for|\s+of|$)',
        ]
        
        for pattern in party_patterns:
            match = re.search(pattern, message)
            if match:
                party = match.group(1).strip()
                # Clean up
                party = re.sub(r'\s+', ' ', party)
                if len(party) > 2:  # Minimum reasonable length
                    params["party_name"] = party
                    break
        
        # Extract GST rate
        gst_match = re.search(r'(\d+)%\s*(?:gst|tax)', message, re.IGNORECASE)
        if gst_match:
            params["tax_rate"] = int(gst_match.group(1))
        
        # Extract narration (if "for" clause exists)
        narration_match = re.search(r'(?:for|towards)\s+(.+?)(?:\s+with|\s+at|$)', message, re.IGNORECASE)
        if narration_match:
            params["narration"] = narration_match.group(1).strip()
        
        return params
    
    def _llm_classify(self, message: str) -> Tuple[str, float, Dict[str, Any]]:
        """Use Gemini to classify intent and extract parameters"""
        
        # Build prompt using string concatenation to avoid any encoding issues
        prompt = (
            "You are an AI assistant for a Tally accounting system. "
            "Analyze the user's command and respond with a JSON object.\n\n"
            "User Command: \"" + message + "\"\n\n"
            "Analyze the intent and extract parameters. "
            "Return ONLY a valid JSON object with this exact structure:\n"
            "{\n"
            "  \"intent\": \"<one of: create_invoice, create_receipt, create_payment, create_sales, query_data, audit_transactions, unknown>\",\n"
            "  \"confidence\": <float between 0.0 and 1.0>,\n"
            "  \"parameters\": {\n"
            "    \"party_name\": \"<customer/vendor name>\",\n"
            "    \"amount\": <numeric amount>,\n"
            "    \"tax_rate\": <GST percentage if mentioned>,\n"
            "    \"narration\": \"<description/purpose>\",\n"
            "    \"voucher_type\": \"<Receipt, Payment, Sales, etc>\",\n"
            "    \"date\": \"<YYYY-MM-DD if mentioned>\"\n"
            "  }\n"
            "}\n\n"
            "Rules:\n"
            "1. Only include parameters that are explicitly mentioned or can be clearly inferred\n"
            "2. Party name should be extracted carefully (look for company names, person names)\n"
            "3. Amount should be numeric only (no currency symbols)\n"
            "4. Intent must be one of the listed options\n"
            "5. Confidence should reflect how clear the intent is\n\n"
            "Return ONLY the JSON, no explanations."
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            response_text = response.content.strip()
            
            # Clean up response (remove markdown if present)
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1]
                if response_text.endswith("```"):
                    response_text = response_text.rsplit("\n", 1)[0]
            
            # Parse JSON
            result = json.loads(response_text)
            
            intent = result.get("intent", "unknown")
            confidence = result.get("confidence", 0.5)
            parameters = result.get("parameters", {})
            
            # Validate intent
            if intent not in self.SUPPORTED_INTENTS:
                logger.warning(f"Unknown intent from LLM: {intent}")
                intent = "unknown"
                confidence = 0.0
            
            logger.info(f"LLM classification: {intent} (confidence: {confidence})")
            return (intent, confidence, parameters)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response_text}")
            return ("unknown", 0.0, {})
        except Exception as e:
            logger.error(f"LLM classification error: {e}")
            return ("unknown", 0.0, {})
    
    def get_intent_description(self, intent: str) -> str:
        """Get human-readable description of intent"""
        descriptions = {
            "create_invoice": "Create a sales invoice",
            "create_receipt": "Record a payment received from customer",
            "create_payment": "Record a payment made to vendor",
            "create_sales": "Create a sales transaction",
            "query_data": "Query financial data",
            "audit_transactions": "Audit and review transactions",
            "update_ledger": "Update ledger information",
            "unknown": "Unable to determine intent"
        }
        return descriptions.get(intent, "Unknown intent")


# Utility functions
def normalize_party_name(name: str) -> str:
    """Normalize party name (title case, clean whitespace)"""
    if not name:
        return name
    
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name.strip())
    
    # Title case (but preserve all-caps acronyms)
    words = name.split()
    normalized = []
    for word in words:
        if word.isupper() and len(word) > 1:
            normalized.append(word)  # Keep acronyms
        else:
            normalized.append(word.title())
    
    return ' '.join(normalized)


def validate_intent_parameters(intent: str, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that required parameters are present for an intent.
    Returns (is_valid, missing_fields)
    """
    required_fields = {
        "create_invoice": ["party_name", "amount"],
        "create_receipt": ["party_name", "amount"],
        "create_payment": ["party_name", "amount"],
        "create_sales": ["party_name", "amount"],
        "query_data": [],
        "audit_transactions": [],
        "update_ledger": ["party_name"],
    }
    
    required = required_fields.get(intent, [])
    missing = [field for field in required if field not in params or not params[field]]
    
    return (len(missing) == 0, missing)
