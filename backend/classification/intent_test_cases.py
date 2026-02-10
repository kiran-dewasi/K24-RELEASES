"""
K24 Intent Classification - Test Cases
=======================================
Comprehensive test suite for 68 intents.
"""

import asyncio
from backend.classification.intent_classifier import classify_intent
from backend.classification.intents import Intent

# Test cases: (message, expected_intent, min_confidence)
TEST_CASES = [
    # READ_QUERIES
    ("Show me outstanding invoices", Intent.QUERY_OUTSTANDING_INVOICES, 0.85),
    ("What do my customers owe me?", Intent.QUERY_OUTSTANDING_INVOICES, 0.85),
    ("List unpaid bills", Intent.QUERY_OUTSTANDING_INVOICES, 0.85),
    
    ("What's my cash position?", Intent.QUERY_CASH_POSITION, 0.85),
    ("Check bank balance", Intent.QUERY_CASH_POSITION, 0.85),
    ("How much cash do I have?", Intent.QUERY_CASH_POSITION, 0.85),
    
    ("What does ABC Corp owe me?", Intent.QUERY_CUSTOMER_BALANCE, 0.75),
    ("Check balance for Reliance", Intent.QUERY_CUSTOMER_BALANCE, 0.75),
    
    ("What's my GST liability?", Intent.QUERY_GST_LIABILITY, 0.85),
    ("How much GST do I owe?", Intent.QUERY_GST_LIABILITY, 0.85),
    
    ("Show sales report", Intent.QUERY_SALES_REPORT, 0.85),
    ("How much did I sell this month?", Intent.QUERY_SALES_REPORT, 0.80),
    
    ("Show me profit and loss", Intent.QUERY_PROFIT_LOSS, 0.85),
    ("P&L statement", Intent.QUERY_PROFIT_LOSS, 0.85),
    
    # CREATE_OPERATIONS
    ("Create invoice for HDFC Bank for 50000", Intent.CREATE_INVOICE, 0.85),
    ("Make an invoice for ABC Corp", Intent.CREATE_INVOICE, 0.85),
    ("Bill customer XYZ for services", Intent.CREATE_INVOICE, 0.85),
    
    ("Create receipt for payment from Reliance", Intent.CREATE_RECEIPT, 0.85),
    ("Record payment received from customer", Intent.CREATE_RECEIPT, 0.85),
    ("Got 25000 from HDFC", Intent.CREATE_RECEIPT, 0.80),
    
    ("Create payment to vendor ABC", Intent.CREATE_PAYMENT, 0.85),
    ("Paid 10000 to electricity board", Intent.CREATE_PAYMENT, 0.85),
    ("Record payment made to supplier", Intent.CREATE_PAYMENT, 0.85),
    
    ("Create expense for office supplies", Intent.CREATE_EXPENSE_ENTRY, 0.85),
    ("Record expense of 5000", Intent.CREATE_EXPENSE_ENTRY, 0.85),
    
    # UPDATE_OPERATIONS
    ("Update invoice amount to 60000", Intent.UPDATE_INVOICE_AMOUNT, 0.80),
    ("Change invoice amount", Intent.UPDATE_INVOICE_AMOUNT, 0.75),
    
    ("Update customer details for ABC Corp", Intent.UPDATE_CUSTOMER_DETAILS, 0.80),
    ("Change customer information", Intent.UPDATE_CUSTOMER_DETAILS, 0.75),
    
    # DELETE_OPERATIONS
    ("Delete invoice INV001", Intent.DELETE_INVOICE, 0.85),
    ("Remove invoice", Intent.DELETE_INVOICE, 0.80),
    ("Cancel invoice", Intent.DELETE_INVOICE, 0.80),
    
    ("Delete receipt REC001", Intent.DELETE_RECEIPT, 0.85),
    
    # COMPLIANCE_QUERIES
    ("When is GST filing due?", Intent.QUERY_GST_FILING_DEADLINE, 0.85),
    ("GST filing deadline", Intent.QUERY_GST_FILING_DEADLINE, 0.85),
    ("What's my GST due date?", Intent.QUERY_GST_FILING_DEADLINE, 0.80),
    
    ("When is TDS filing due?", Intent.QUERY_TDS_FILING_DEADLINE, 0.85),
    
    ("Am I compliant with regulations?", Intent.QUERY_COMPLIANCE_STATUS, 0.75),
    ("Check compliance status", Intent.QUERY_COMPLIANCE_STATUS, 0.80),
    
    # ANALYTICS
    ("Show me sales trend", Intent.ANALYTICS_SALES_TREND, 0.85),
    ("Sales over time", Intent.ANALYTICS_SALES_TREND, 0.80),
    ("Compare sales month over month", Intent.ANALYTICS_SALES_TREND, 0.75),
    
    ("Who are my top customers?", Intent.ANALYTICS_TOP_CUSTOMERS, 0.85),
    ("Best customers", Intent.ANALYTICS_TOP_CUSTOMERS, 0.85),
    
    # META_OPERATIONS
    ("Help", Intent.HELP_REQUEST, 0.85),
    ("What can you do?", Intent.HELP_REQUEST, 0.80),
    ("How do I create an invoice?", Intent.HELP_REQUEST, 0.75),
    
    ("Export data to Excel", Intent.EXPORT_DATA, 0.85),
    ("Download data", Intent.EXPORT_DATA, 0.80),
    
    # FALLBACK
    ("Show me something about finances", Intent.CLARIFY_REQUEST, 0.50),
    ("Random gibberish xyz123", Intent.CLARIFY_REQUEST, 0.50),
]

async def run_tests():
    """Run all test cases"""
    print("=" * 80)
    print("K24 Intent Classification - Test Suite")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for i, (message, expected_intent, min_confidence) in enumerate(TEST_CASES, 1):
        try:
            intent, confidence, metadata = await classify_intent(message, timeout=5)
            
            # Check if intent matches
            intent_match = (intent == expected_intent)
            
            # Check if confidence is acceptable
            if expected_intent in [Intent.CLARIFY_REQUEST, Intent.UNKNOWN]:
                # For fallback intents, we expect low confidence or these specific intents
                confidence_ok = True
            else:
                confidence_ok = confidence >= min_confidence
            
            if intent_match and confidence_ok:
                status = "✓ PASS"
                passed += 1
            else:
                status = "✗ FAIL"
                failed += 1
            
            method = metadata.get("method", "unknown")
            elapsed_ms = metadata.get("elapsed", 0) * 1000
            
            print(f"\n[{i}/{len(TEST_CASES)}] {status}")
            print(f"  Message: \"{message}\"")
            print(f"  Expected: {expected_intent} (conf >= {min_confidence})")
            print(f"  Got: {intent} (conf = {confidence:.2f})")
            print(f"  Method: {method}, Time: {elapsed_ms:.0f}ms")
            
            if not intent_match:
                print(f"  ⚠ Intent mismatch!")
            if not confidence_ok:
                print(f"  ⚠ Confidence too low!")
                
        except Exception as e:
            print(f"\n[{i}/{len(TEST_CASES)}] ✗ ERROR")
            print(f"  Message: \"{message}\"")
            print(f"  Error: {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")
    print(f"Success Rate: {passed/len(TEST_CASES)*100:.1f}%")
    print("=" * 80)
    
    return passed, failed

if __name__ == "__main__":
    asyncio.run(run_tests())
