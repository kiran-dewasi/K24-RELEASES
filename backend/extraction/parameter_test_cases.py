"""
K24 Parameter Extraction - Test Cases
======================================
Comprehensive test suite for parameter extraction.
"""

import asyncio
from backend.extraction.parameter_extractor import extract_parameters
from backend.extraction.fuzzy_matcher import fuzzy_match_ledger, exact_match_ledger
from backend.extraction.parameter_models import Amount, InvoiceDate, GstRate

# Test cases: (message, intent, expected_results)
TEST_CASES = [
    # Amount extraction
    ("Create invoice for 50000", "CREATE_INVOICE", {"amount": 50000.0}),
    ("Invoice for ₹5,00,000", "CREATE_INVOICE", {"amount": 500000.0}),
    ("Bill for Rs. 25000", "CREATE_INVOICE", {"amount": 25000.0}),
    ("Create invoice for 5L", "CREATE_INVOICE", {"amount": 500000.0}),
    ("Make invoice 1Cr", "CREATE_INVOICE", {"amount": 10000000.0}),
    
    # GST rate extraction
    ("Create invoice with 18% GST", "CREATE_INVOICE", {"gst_rate": 18.0}),
    ("Invoice with GST 12%", "CREATE_INVOICE", {"gst_rate": 12.0}),
    ("Bill with 5 percent gst", "CREATE_INVOICE", {"gst_rate": 5.0}),
    
    # Date extraction
    ("Create invoice for today", "CREATE_INVOICE", {"date_is_today": True}),
    ("Invoice dated yesterday", "CREATE_INVOICE", {"date_is_today": False}),
    ("Create invoice on 2025-12-01", "CREATE_INVOICE", {"date_str": "2025-12-01"}),
    
    # Customer name extraction
    ("Create invoice for HDFC Bank", "CREATE_INVOICE", {"customer_contains": "HDFC"}),
    ("Invoice for ABC Corp", "CREATE_INVOICE", {"customer_contains": "ABC"}),
    ("Bill customer XYZ Ltd", "CREATE_INVOICE", {"customer_contains": "XYZ"}),
    
    # Combined parameters
    ("Create invoice for HDFC Bank 50000 with 18% GST", "CREATE_INVOICE", {
        "customer_contains": "HDFC",
        "amount": 50000.0,
        "gst_rate": 18.0
    }),
    ("Make invoice for ABC Corp Rs. 25000", "CREATE_INVOICE", {
        "customer_contains": "ABC",
        "amount": 25000.0
    }),
    
    # Edge cases
    ("Invoice for 0", "CREATE_INVOICE", {"has_error": True}),  # Invalid amount
    ("Create invoice 20000000", "CREATE_INVOICE", {"has_error": True}),  # Exceeds max
    ("Invoice with 50% GST", "CREATE_INVOICE", {"has_error": True}),  # Invalid GST
]

def test_amount_parsing():
    """Test amount parsing with various formats"""
    print("\n" + "="*80)
    print("Testing Amount Parsing")
    print("="*80)
    
    test_cases = [
        ("50000", 50000.0),
        ("5L", 500000.0),
        ("1Cr", 10000000.0),
        ("₹50,000", 50000.0),
        ("Rs. 25000", 25000.0),
    ]
    
    passed = 0
    failed = 0
    
    for text, expected in test_cases:
        from backend.extraction.parameter_extractor import ParameterExtractor
        result = ParameterExtractor.parse_amount(text)
        
        if result == expected:
            print(f"✓ '{text}' -> {result}")
            passed += 1
        else:
            print(f"✗ '{text}' -> {result} (expected {expected})")
            failed += 1
    
    print(f"\nAmount parsing: {passed} passed, {failed} failed")
    return passed, failed

def test_gst_validation():
    """Test GST rate validation"""
    print("\n" + "="*80)
    print("Testing GST Validation")
    print("="*80)
    
    test_cases = [
        (0.0, True),
        (5.0, True),
        (12.0, True),
        (18.0, True),
        (28.0, True),
        (15.0, False),  # Invalid
        (50.0, False),  # Invalid
    ]
    
    passed = 0
    failed = 0
    
    for rate, should_pass in test_cases:
        try:
            gst = GstRate(value=rate)
            if should_pass:
                print(f"✓ {rate}% is valid")
                passed += 1
            else:
                print(f"✗ {rate}% should have failed but passed")
                failed += 1
        except ValueError:
            if not should_pass:
                print(f"✓ {rate}% correctly rejected")
                passed += 1
            else:
                print(f"✗ {rate}% should have passed but failed")
                failed += 1
    
    print(f"\nGST validation: {passed} passed, {failed} failed")
    return passed, failed

async def test_parameter_extraction():
    """Test full parameter extraction"""
    print("\n" + "="*80)
    print("Testing Parameter Extraction")
    print("="*80)
    
    passed = 0
    failed = 0
    
    for i, (message, intent, expected) in enumerate(TEST_CASES[:10], 1):  # First 10 tests
        try:
            result = await extract_parameters(message, intent, timeout=5)
            
            # Check expectations
            all_checks_passed = True
            
            if "amount" in expected:
                if result.amount and result.amount.value == expected["amount"]:
                    pass
                else:
                    all_checks_passed = False
            
            if "gst_rate" in expected:
                if result.gst_rate and result.gst_rate.value == expected["gst_rate"]:
                    pass
                else:
                    all_checks_passed = False
            
            if "has_error" in expected and expected["has_error"]:
                if len(result.errors) > 0:
                    pass
                else:
                    all_checks_passed = False
            
            if all_checks_passed:
                print(f"✓ [{i}] '{message[:50]}...'")
                passed += 1
            else:
                print(f"✗ [{i}] '{message[:50]}...'")
                print(f"   Expected: {expected}")
                print(f"   Got: amount={result.amount}, errors={result.errors}")
                failed += 1
                
        except Exception as e:
            print(f"✗ [{i}] '{message[:50]}...' - Error: {e}")
            failed += 1
    
    print(f"\nParameter extraction: {passed} passed, {failed} failed")
    return passed, failed

async def run_all_tests():
    """Run all test suites"""
    print("="*80)
    print("K24 Parameter Extraction - Test Suite")
    print("="*80)
    
    total_passed = 0
    total_failed = 0
    
    # Test 1: Amount parsing
    p, f = test_amount_parsing()
    total_passed += p
    total_failed += f
    
    # Test 2: GST validation
    p, f = test_gst_validation()
    total_passed += p
    total_failed += f
    
    # Test 3: Full extraction
    p, f = await test_parameter_extraction()
    total_passed += p
    total_failed += f
    
    # Summary
    print("\n" + "="*80)
    print(f"TOTAL: {total_passed} passed, {total_failed} failed")
    print(f"Success Rate: {total_passed/(total_passed+total_failed)*100:.1f}%")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
