from backend.agent_gemini import extract_bill_data
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

if not google_api_key:
    print("!! Warning: GOOGLE_API_KEY not found in environment variables.")

# Test with 10-item invoice
print("Running extraction on test_invoice_10items.jpg...")
try:
    result = extract_bill_data("test_invoice_10items.jpg", google_api_key)
except Exception as e:
    print(f"FAILED Extraction failed with error: {e}")
    exit(1)

# Handle error in result
if result.get("error"):
    print(f"FAILED Extraction returned error: {result['error']}")
    exit(1)

items = result.get('items', [])
print(f"Items detected: {len(items)}")
print(f"Expected: 10 items")

# Check for common errors
issues = []

if len(items) < 10:
    issues.append(f"FAILED Missing items: detected {len(items)}/10")

for i, item in enumerate(items):
    name = item.get('name') or item.get('Description') or item.get('Item Description')
    if not name:
        issues.append(f"FAILED Item {i+1}: Missing name")
    
    qty = item.get('quantity')
    if qty is None or qty == 0:
        issues.append(f"FAILED Item {i+1}: Missing/zero quantity")
        
    rate = item.get('rate')
    if rate is None:
        issues.append(f"FAILED Item {i+1}: Missing rate")

if issues:
    print("\nPRECISION ISSUES FOUND:")
    for issue in issues:
        print(f"  {issue}")
else:
    print("\nSUCCESS Perfect extraction - all items complete")
    print("\nExtracted Items:")
    print(json.dumps(items, indent=2))
