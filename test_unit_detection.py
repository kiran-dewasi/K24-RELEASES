"""
Test script for unit detection 
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from backend.agent_gemini import fix_missing_units, COMMON_UNITS

print("=" * 60)
print("UNIT DETECTION TEST")
print("=" * 60)

# Test cases with various item names
test_items = [
    {"name": "Steel Pipe 2 inch", "quantity": 10, "unit": None},
    {"name": "Cooking Oil 1 Liter", "quantity": 5, "unit": ""},
    {"name": "Metal Pieces", "quantity": 100, "unit": "unknown"},
    {"name": "Cement 50kg Bag", "quantity": 2, "unit": ""},
    {"name": "5 ltr Water Container", "quantity": 3, "unit": None},
    {"name": "Electronic Component", "quantity": 50, "unit": "pcs"},
    {"name": "Wire 10 meter roll", "quantity": 10, "unit": ""},
    {"name": "Sugar 500 gram pack", "quantity": 20, "unit": ""},
    {"name": "Random Product ABC", "quantity": 5, "unit": None},  # Should default to Kgs
]

test_data = {"items": test_items.copy()}

print("\nBefore fix_missing_units:")
for item in test_items:
    print(f"  {item['name']}: '{item.get('unit', 'None')}'")

result = fix_missing_units(test_data)

print("\nAfter fix_missing_units:")
for item in result['items']:
    print(f"  {item['name']}: '{item['unit']}'")

# Verify all units are valid
print("\n" + "=" * 60)
print("VALIDATION:")
print("=" * 60)

all_valid = True
for item in result['items']:
    unit = item.get('unit', '')
    if not unit or unit.lower() in ['null', 'unknown', '', 'na', 'none']:
        print(f"  FAIL: {item['name']} has invalid unit: '{unit}'")
        all_valid = False
    else:
        print(f"  OK: {item['name']} -> {unit}")

print("\n" + "=" * 60)
if all_valid:
    print("SUCCESS: All items have valid units!")
else:
    print("FAIL: Some items have invalid units!")
print("=" * 60)
