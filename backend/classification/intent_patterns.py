"""
K24 Intent Classification - Pattern Matching
=============================================
Regex patterns for fast intent classification (< 100ms).
Compiled patterns for performance optimization.
"""

import re
from typing import Dict, List, Tuple, Optional
from backend.classification.intents import Intent

# Compiled regex patterns for each intent
# Format: {Intent: [compiled_patterns]}

INTENT_PATTERNS: Dict[str, List[re.Pattern]] = {
    # READ_QUERIES
    Intent.QUERY_OUTSTANDING_INVOICES: [
        re.compile(r'outstanding.*invoices?', re.IGNORECASE),
        re.compile(r'show.*due.*invoices?', re.IGNORECASE),
        re.compile(r'what.*owe.*me', re.IGNORECASE),
        re.compile(r'unpaid.*invoices?', re.IGNORECASE),
        re.compile(r'pending.*invoices?', re.IGNORECASE),
        re.compile(r'receivables?', re.IGNORECASE),
        re.compile(r'customers?.*owe', re.IGNORECASE),
        re.compile(r'bills?.*due', re.IGNORECASE),
    ],
    
    Intent.QUERY_CASH_POSITION: [
        re.compile(r'cash.*position', re.IGNORECASE),
        re.compile(r'bank.*balance', re.IGNORECASE),
        re.compile(r'how.*much.*cash', re.IGNORECASE),
        re.compile(r'liquid.*position', re.IGNORECASE),
        re.compile(r'cash.*on.*hand', re.IGNORECASE),
        re.compile(r'available.*funds?', re.IGNORECASE),
        re.compile(r'current.*balance', re.IGNORECASE),
    ],
    
    Intent.QUERY_CUSTOMER_BALANCE: [
        re.compile(r'customer.*balance', re.IGNORECASE),
        re.compile(r'how.*much.*\w+.*owe', re.IGNORECASE),
        re.compile(r'balance.*for.*\w+', re.IGNORECASE),
        re.compile(r'what.*does.*\w+.*owe', re.IGNORECASE),
        re.compile(r'check.*\w+.*balance', re.IGNORECASE),
    ],
    
    Intent.QUERY_GST_LIABILITY: [
        re.compile(r'gst.*liability', re.IGNORECASE),
        re.compile(r'gst.*owe', re.IGNORECASE),
        re.compile(r'gst.*payable', re.IGNORECASE),
        re.compile(r'tax.*liability', re.IGNORECASE),
        re.compile(r'how.*much.*gst', re.IGNORECASE),
    ],
    
    Intent.QUERY_SALES_REPORT: [
        re.compile(r'sales?.*report', re.IGNORECASE),
        re.compile(r'show.*sales', re.IGNORECASE),
        re.compile(r'revenue.*report', re.IGNORECASE),
        re.compile(r'how.*much.*sold', re.IGNORECASE),
        re.compile(r'sales?.*summary', re.IGNORECASE),
    ],
    
    Intent.QUERY_PROFIT_LOSS: [
        re.compile(r'profit.*loss', re.IGNORECASE),
        re.compile(r'p\s*&\s*l', re.IGNORECASE),
        re.compile(r'p/l.*statement', re.IGNORECASE),
        re.compile(r'income.*statement', re.IGNORECASE),
        re.compile(r'profit.*statement', re.IGNORECASE),
    ],
    
    # CREATE_OPERATIONS
    Intent.CREATE_INVOICE: [
        re.compile(r'create.*invoice.*for', re.IGNORECASE),
        re.compile(r'make.*invoice', re.IGNORECASE),
        re.compile(r'bill.*customer', re.IGNORECASE),
        re.compile(r'raise.*invoice', re.IGNORECASE),
        re.compile(r'generate.*bill', re.IGNORECASE),
        re.compile(r'new.*invoice', re.IGNORECASE),
        re.compile(r'invoice.*\w+.*for', re.IGNORECASE),
    ],
    
    Intent.CREATE_RECEIPT: [
        re.compile(r'create.*receipt', re.IGNORECASE),
        re.compile(r'record.*payment.*received', re.IGNORECASE),
        re.compile(r'received.*from', re.IGNORECASE),
        re.compile(r'payment.*received', re.IGNORECASE),
        re.compile(r'got.*payment', re.IGNORECASE),
        re.compile(r'customer.*paid', re.IGNORECASE),
        re.compile(r'money.*received', re.IGNORECASE),
    ],
    
    Intent.CREATE_PAYMENT: [
        re.compile(r'create.*payment', re.IGNORECASE),
        re.compile(r'record.*payment.*made', re.IGNORECASE),
        re.compile(r'paid.*to', re.IGNORECASE),
        re.compile(r'pay.*\w+', re.IGNORECASE),
        re.compile(r'make.*payment', re.IGNORECASE),
        re.compile(r'send.*money', re.IGNORECASE),
    ],
    
    Intent.CREATE_EXPENSE_ENTRY: [
        re.compile(r'create.*expense', re.IGNORECASE),
        re.compile(r'record.*expense', re.IGNORECASE),
        re.compile(r'add.*expense', re.IGNORECASE),
        re.compile(r'new.*expense', re.IGNORECASE),
        re.compile(r'spent.*on', re.IGNORECASE),
    ],
    
    # UPDATE_OPERATIONS
    Intent.UPDATE_INVOICE_AMOUNT: [
        re.compile(r'update.*invoice.*amount', re.IGNORECASE),
        re.compile(r'change.*invoice.*amount', re.IGNORECASE),
        re.compile(r'modify.*invoice.*amount', re.IGNORECASE),
        re.compile(r'edit.*invoice.*amount', re.IGNORECASE),
    ],
    
    Intent.UPDATE_CUSTOMER_DETAILS: [
        re.compile(r'update.*customer', re.IGNORECASE),
        re.compile(r'change.*customer.*details', re.IGNORECASE),
        re.compile(r'edit.*customer', re.IGNORECASE),
        re.compile(r'modify.*customer', re.IGNORECASE),
    ],
    
    # DELETE_OPERATIONS
    Intent.DELETE_INVOICE: [
        re.compile(r'delete.*invoice', re.IGNORECASE),
        re.compile(r'remove.*invoice', re.IGNORECASE),
        re.compile(r'cancel.*invoice', re.IGNORECASE),
        re.compile(r'void.*invoice', re.IGNORECASE),
    ],
    
    Intent.DELETE_RECEIPT: [
        re.compile(r'delete.*receipt', re.IGNORECASE),
        re.compile(r'remove.*receipt', re.IGNORECASE),
        re.compile(r'cancel.*receipt', re.IGNORECASE),
    ],
    
    # COMPLIANCE_QUERIES
    Intent.QUERY_GST_FILING_DEADLINE: [
        re.compile(r'gst.*filing.*deadline', re.IGNORECASE),
        re.compile(r'gst.*due.*date', re.IGNORECASE),
        re.compile(r'when.*gst.*due', re.IGNORECASE),
        re.compile(r'gst.*filing.*date', re.IGNORECASE),
    ],
    
    Intent.QUERY_TDS_FILING_DEADLINE: [
        re.compile(r'tds.*filing.*deadline', re.IGNORECASE),
        re.compile(r'tds.*due.*date', re.IGNORECASE),
        re.compile(r'when.*tds.*due', re.IGNORECASE),
    ],
    
    Intent.QUERY_COMPLIANCE_STATUS: [
        re.compile(r'compliance.*status', re.IGNORECASE),
        re.compile(r'am.*i.*compliant', re.IGNORECASE),
        re.compile(r'compliance.*check', re.IGNORECASE),
    ],
    
    # ANALYTICS
    Intent.ANALYTICS_SALES_TREND: [
        re.compile(r'sales.*trend', re.IGNORECASE),
        re.compile(r'sales.*over.*time', re.IGNORECASE),
        re.compile(r'sales.*growth', re.IGNORECASE),
        re.compile(r'compare.*sales', re.IGNORECASE),
    ],
    
    Intent.ANALYTICS_TOP_CUSTOMERS: [
        re.compile(r'top.*customers?', re.IGNORECASE),
        re.compile(r'best.*customers?', re.IGNORECASE),
        re.compile(r'biggest.*customers?', re.IGNORECASE),
        re.compile(r'who.*buys?.*most', re.IGNORECASE),
    ],
    
    # META_OPERATIONS
    Intent.HELP_REQUEST: [
        re.compile(r'\bhelp\b', re.IGNORECASE),
        re.compile(r'how.*do.*i', re.IGNORECASE),
        re.compile(r'what.*can.*you.*do', re.IGNORECASE),
        re.compile(r'assist.*me', re.IGNORECASE),
    ],
    
    Intent.EXPORT_DATA: [
        re.compile(r'export.*data', re.IGNORECASE),
        re.compile(r'download.*data', re.IGNORECASE),
        re.compile(r'export.*to.*excel', re.IGNORECASE),
        re.compile(r'export.*to.*csv', re.IGNORECASE),
    ],
}

def pattern_match_intent(message: str) -> Tuple[Optional[str], float]:
    """
    Fast pattern matching for intent classification.
    
    Args:
        message: User input message
        
    Returns:
        Tuple of (intent, confidence) or (None, 0.0) if no match
        
    Example:
        >>> pattern_match_intent("Show me outstanding invoices")
        ("QUERY_OUTSTANDING_INVOICES", 0.95)
    """
    message_lower = message.lower().strip()
    
    # Try each intent's patterns
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(message):
                # Strong match confidence for pattern-based classification
                confidence = 0.95
                return (intent, confidence)
    
    return (None, 0.0)
