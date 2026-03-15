"""
DIRECT END-TO-END TEST: Purchase Invoice Creation
Tests the EXACT same path WhatsApp uses, but directly.
Prints every step with confirmation.
"""
import sys
sys.path.insert(0, '.')

from backend.tally_engine import TallyEngine

print("=" * 60)
print("STEP 1: Create TallyEngine (fresh instance like WhatsApp path)")
engine = TallyEngine()
print("  ✅ TallyEngine created")

print()
print("STEP 2: Pre-warm cache check")
print(f"  Ledger cache populated: {engine.reader.cache_populated}")
print(f"  Item cache count: {len(engine.reader.item_cache)}")

print()
print("STEP 3: Test ledger lookup for 'Vinayak Enterprises'")
ledger = engine.reader.check_ledger_exists("Vinayak Enterprises")
print(f"  check_ledger_exists('Vinayak Enterprises') → {repr(ledger)}")

print()
print("STEP 4: Test item lookup for 'Jeera'")  
item = engine.reader.check_item_exists("Jeera")
print(f"  check_item_exists('Jeera') → {repr(item)}")

print()
print("STEP 5: Run process_purchase_request (FULL PIPELINE)")
payload = {
    "party_name": "Vinayak Enterprises",
    "date": "20260315",
    "items": [
        {
            "name": "Jeera",
            "quantity": 10.0,
            "unit": "kg",
            "rate": 130.0,
            "taxable_amount": 1300.0
        }
    ]
}

print(f"  Payload: {payload}")
print()
result = engine.process_purchase_request(payload)
print()
print("=" * 60)
print(f"RESULT: {result}")
print("=" * 60)

# Now check what was written to failed_voucher.xml
import os
if os.path.exists("failed_voucher.xml"):
    from pathlib import Path
    import time
    age = time.time() - os.path.getmtime("failed_voucher.xml")
    if age < 30:  # written in last 30 seconds = this test
        print()
        print("FAILED VOUCHER XML (from this test run):")
        print(Path("failed_voucher.xml").read_text(encoding="utf-8")[:2000])

print()
print("TALLY RESPONSE:")
if os.path.exists("tally_last_response.txt"):
    print(Path("tally_last_response.txt").read_text(encoding="utf-8"))
