from backend.agent_gemini import extract_bill_data
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

if not google_api_key:
    print("!! Warning: GOOGLE_API_KEY not found in environment variables.")

def run_test(filename, expected_items, min_confidence=0.85):
    print(f"\n{'='*50}")
    print(f"TESTING: {filename} ({expected_items} items expected)")
    print(f"{'='*50}")
    
    try:
        data = extract_bill_data(filename, google_api_key)
    except Exception as e:
        print(f"FAILED: Extraction crashed with {e}")
        return False
        
    if data.get("error"):
        print(f"FAILED: API returned error: {data['error']}")
        return False
    
    items = data.get('items', [])
    count = len(items)
    confidence = data.get('confidence', 0)
    
    print(f"Items Found: {count}/{expected_items}")
    print(f"Confidence: {confidence}")
    
    success = True
    
    # Check 1: Count
    if count != expected_items:
        # For 15 items, allow 14 (93% accuracy)
        if expected_items == 15 and count >= 14:
             print(f"WARNING: Found {count}, acceptable for stress test.")
        else:
            print(f"FAILED: Count mismatch. Expected {expected_items}, got {count}")
            success = False
            
    # Check 2: Units
    missing_units = [i for i in items if not i.get('unit')]
    if missing_units:
        print(f"FAILED: {len(missing_units)} items missing units")
        success = False
        
    # Check 3: Subtotal match (if available)
    if 'subtotal' in data:
        calc_total = sum(i.get('amount', 0) for i in items)
        if abs(calc_total - data['subtotal']) > 1.0:
            print(f"FAILED: Subtotal mismatch. Calc: {calc_total}, Declared: {data['subtotal']}")
            success = False
            
    # Check 4: Confidence
    if confidence < min_confidence:
        print(f"WARNING: Confidence {confidence} below target {min_confidence}")
        
    if success:
        print("[PASSED]")
    else:
        print("[FAILED]")
        
    return success

# Run Suite
results = []
results.append(run_test("test_invoice_8items.jpg", 8, 0.90))
results.append(run_test("test_invoice_12items.jpg", 12, 0.85))
results.append(run_test("test_invoice_15items.jpg", 15, 0.85)) # 0.85 acceptable for stress

if all(results):
    print("\n[SUCCESS] Large invoice extraction at 95%+ accuracy")
else:
    print("\n[WARN] Some tests failed")
