"""
K24 Intent Classification - Main Classifier
============================================
Classifies user intent with pattern matching + LLM fallback.
Includes timeout handling and confidence threshold enforcement.
"""

import asyncio
import logging
import time
from typing import Tuple, Optional, Dict, Any
import os

from classification.intents import Intent
from classification.intent_patterns import pattern_match_intent
from gemini.gemini_orchestrator import GeminiOrchestrator

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_TIMEOUT = 3  # seconds
CONFIDENCE_THRESHOLD = 0.85
GEMINI_MODEL = "gemini-2.0-flash-exp"

class IntentClassifier:
    """
    Main intent classifier with dual-path classification:
    1. Fast pattern matching (< 100ms)
    2. LLM classification (< 3 seconds)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize classifier with Gemini Orchestrator"""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not set. LLM classification will fail.")
        
        # Build comprehensive system prompt with all 68 intents
        self.system_prompt = """You are KITTU, an expert AI accountant for K24.ai.

Your task: Classify the user's intent into one of these accounting categories:

READ_QUERIES:
- QUERY_OUTSTANDING_INVOICES
- QUERY_CASH_POSITION
- QUERY_CUSTOMER_BALANCE
- QUERY_GST_LIABILITY
- QUERY_TDS_OBLIGATION
- QUERY_SALES_REPORT
- QUERY_EXPENSE_REPORT
- QUERY_PROFIT_LOSS
- QUERY_AGED_RECEIVABLES
- QUERY_AGED_PAYABLES
- QUERY_INVENTORY_STATUS
- QUERY_CUSTOMER_CREDIT_LIMIT
- QUERY_VENDOR_PAYMENT_TERMS
- QUERY_BANK_RECONCILIATION
- QUERY_FINANCIAL_RATIO

CREATE_OPERATIONS:
- CREATE_INVOICE
- CREATE_RECEIPT
- CREATE_PAYMENT
- CREATE_CREDIT_NOTE
- CREATE_DEBIT_NOTE
- CREATE_JOURNAL_ENTRY
- CREATE_CUSTOMER
- CREATE_VENDOR
- CREATE_EXPENSE_ENTRY
- CREATE_BANK_DEPOSIT
- CREATE_BANK_WITHDRAWAL
- CREATE_INVENTORY_ENTRY

UPDATE_OPERATIONS:
- UPDATE_INVOICE_AMOUNT
- UPDATE_INVOICE_DATE
- UPDATE_CUSTOMER_DETAILS
- UPDATE_VENDOR_DETAILS
- UPDATE_LEDGER_NAME
- UPDATE_PAYMENT_STATUS
- UPDATE_INVENTORY_QUANTITY
- UPDATE_GST_RATE
- UPDATE_BANK_RECONCILIATION
- UPDATE_CREDIT_LIMIT

DELETE_OPERATIONS:
- DELETE_INVOICE
- DELETE_RECEIPT
- DELETE_PAYMENT
- DELETE_JOURNAL_ENTRY
- DELETE_CUSTOMER_DRAFT
- DELETE_VENDOR_DRAFT
- DELETE_INVENTORY_ENTRY
- DELETE_EXPENSE_ENTRY

COMPLIANCE_QUERIES:
- QUERY_GST_FILING_DEADLINE
- QUERY_TDS_FILING_DEADLINE
- QUERY_ITR_FILING_DEADLINE
- QUERY_AUDIT_REQUIREMENTS
- QUERY_COMPLIANCE_STATUS
- QUERY_TAX_CALENDAR
- QUERY_REGULATORY_REQUIREMENTS
- QUERY_GSTR1_STATUS
- QUERY_GSTR3B_STATUS
- QUERY_ITC_ELIGIBILITY

ANALYTICS:
- ANALYTICS_SALES_TREND
- ANALYTICS_EXPENSE_TREND
- ANALYTICS_PROFIT_TREND
- ANALYTICS_CUSTOMER_CHURN
- ANALYTICS_TOP_CUSTOMERS
- ANALYTICS_PAYMENT_DELAYS
- ANALYTICS_CASH_FLOW_FORECAST
- ANALYTICS_GROSS_MARGIN_TREND

META_OPERATIONS:
- HELP_REQUEST
- FEEDBACK_SUGGESTION
- REPORT_BUG
- REQUEST_FEATURE
- EXPORT_DATA

FALLBACK:
- CLARIFY_REQUEST (if unclear)
- UNKNOWN (if cannot determine)

Rules:
1. Return ONLY the intent name (exact match, uppercase)
2. Assign confidence score 0.0-1.0
3. If confidence < 0.85, suggest a clarifying question
4. Be conservative: Only high confidence for financial accuracy

Format your response as:
INTENT: [INTENT_NAME]
CONFIDENCE: [0.0-1.0]
CLARIFICATION: [question for user if needed, or null]

Example:
INTENT: QUERY_OUTSTANDING_INVOICES
CONFIDENCE: 0.95
CLARIFICATION: null
"""
        
        # Initialize orchestrator
        self.orchestrator = GeminiOrchestrator(
            api_key=self.api_key,
            system_prompt=self.system_prompt
        )
    
    async def classify_intent(
        self,
        message: str,
        timeout: int = DEFAULT_TIMEOUT
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Classify user intent with timeout and confidence threshold.
        
        Flow:
        1. Try pattern matching (fast path)
        2. If no match or low confidence, try LLM
        3. If timeout or low confidence, return CLARIFY_REQUEST
        
        Args:
            message: User input message
            timeout: Maximum time in seconds (default 3)
            
        Returns:
            Tuple of (intent, confidence, metadata)
            
        Example:
            >>> await classifier.classify_intent("Show me outstanding invoices")
            ("QUERY_OUTSTANDING_INVOICES", 0.95, {"method": "pattern"})
        """
        start_time = time.time()
        
        try:
            # Step 1: Fast pattern matching
            intent, confidence = pattern_match_intent(message)
            
            if intent and confidence >= CONFIDENCE_THRESHOLD:
                elapsed = time.time() - start_time
                logger.info(f"Pattern match: {intent} (confidence={confidence:.2f}, time={elapsed*1000:.0f}ms)")
                return (intent, confidence, {"method": "pattern", "elapsed": elapsed})
            
            # Step 2: LLM classification with timeout
            try:
                llm_intent, llm_confidence, llm_meta = await asyncio.wait_for(
                    self._llm_classify(message),
                    timeout=timeout
                )
                
                elapsed = time.time() - start_time
                
                # Check confidence threshold
                if llm_confidence >= CONFIDENCE_THRESHOLD:
                    logger.info(f"LLM match: {llm_intent} (confidence={llm_confidence:.2f}, time={elapsed*1000:.0f}ms)")
                    return (llm_intent, llm_confidence, {"method": "llm", "elapsed": elapsed})
                else:
                    # Low confidence, return clarification needed
                    logger.info(f"Low confidence ({llm_confidence:.2f}), requesting clarification")
                    return (Intent.CLARIFY_REQUEST, llm_confidence, {
                        "method": "llm_low_confidence",
                        "attempted": llm_intent,
                        "elapsed": elapsed
                    })
                    
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                logger.warning(f"Classification timeout after {timeout}s")
                return (Intent.CLARIFY_REQUEST, 0.0, {
                    "method": "timeout",
                    "elapsed": elapsed
                })
                
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return (Intent.UNKNOWN, 0.0, {"method": "error", "error": str(e)})
    
    async def _llm_classify(self, message: str) -> Tuple[str, float, Dict[str, Any]]:
        """
        Use Gemini LLM to classify intent.
        
        Args:
            message: User input
            
        Returns:
            Tuple of (intent, confidence, metadata)
        """
        
        prompt = f"User message: \"{message}\"\n\nYour classification:"
        
        # Call Gemini via Orchestrator
        # We use a short timeout for classification
        try:
            response_text = await self.orchestrator.invoke_with_retry(
                query=prompt,
                max_attempts=2,  # Fewer retries for latency sensitivity
                timeout=5       # Short timeout
            )
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            raise
        
        # Parse response
        intent, confidence, clarification = self._parse_llm_response(response_text)
        
        return (intent, confidence, {"clarification": clarification})
    
    def _parse_llm_response(self, response: str) -> Tuple[str, float, Optional[str]]:
        """
        Parse Gemini response to extract intent, confidence, and clarification.
        
        Expected format:
        INTENT: QUERY_OUTSTANDING_INVOICES
        CONFIDENCE: 0.95
        CLARIFICATION: null
        """
        intent = Intent.UNKNOWN
        confidence = 0.0
        clarification = None
        
        lines = response.strip().split('\n')
        for line in lines:
            if line.startswith("INTENT:"):
                intent_str = line.split(":", 1)[1].strip()
                # Validate against known intents
                try:
                    intent = Intent(intent_str)
                except ValueError:
                    intent = Intent.UNKNOWN
                    
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                except:
                    confidence = 0.0
                    
            elif line.startswith("CLARIFICATION:"):
                clar_str = line.split(":", 1)[1].strip()
                if clar_str.lower() not in ["null", "none", ""]:
                    clarification = clar_str
        
        return (intent, confidence, clarification)

# Global instance
_classifier: Optional[IntentClassifier] = None

def get_classifier() -> IntentClassifier:
    """Get or create global classifier instance"""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier

async def classify_intent(message: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[str, float, Dict[str, Any]]:
    """
    Convenience function for intent classification.
    
    Args:
        message: User input
        timeout: Max time in seconds
        
    Returns:
        Tuple of (intent, confidence, metadata)
    """
    classifier = get_classifier()
    return await classifier.classify_intent(message, timeout)

