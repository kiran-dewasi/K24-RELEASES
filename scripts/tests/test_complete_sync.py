"""
Complete Sync Verification Test
Tests the entire data flow from Tally to Frontend
"""

import requests
import time
from backend.database import SessionLocal, Voucher
from backend.tally_connector import TallyConnector

print("="*60)
print("COMPLETE SYNC VERIFICATION TEST")
print("="*60)

# Step 1: Test Parser
print("\n1. Testing Voucher Parser...")
t = TallyConnector('http://localhost:9000')
df = t.fetch_vouchers()
print(f"   Vouchers parsed from Tally: {len(df)}")
if not df.empty:
    print(f"   Columns: {list(df.columns)}")
    print(f"   Sample data:")
    print(df.to_string())
else:
    print("   ❌ NO DATA PARSED!")
    exit(1)

# Step 2: Check DB Before Sync
print("\n2. Checking Shadow DB BEFORE sync...")
db = SessionLocal()
vouchers_before = db.query(Voucher).all()
print(f"   Vouchers in DB: {len(vouchers_before)}")
for v in vouchers_before:
    print(f"     - {v.voucher_type} | {v.party_name} | ₹{v.amount} | {v.date}")
db.close()

# Step 3: Trigger Sync
print("\n3. Triggering Sync via API...")
r = requests.post('http://127.0.0.1:8001/sync', headers={'x-api-key': 'k24-secret-key-123'})
print(f"   Status: {r.status_code}")
print(f"   Response: {r.json()}")

# Step 4: Wait for Sync
print("\n4. Waiting 5 seconds for sync to complete...")
time.sleep(5)

# Step 5: Check DB After Sync
print("\n5. Checking Shadow DB AFTER sync...")
db = SessionLocal()
vouchers_after = db.query(Voucher).all()
print(f"   Vouchers in DB: {len(vouchers_after)}")
for v in vouchers_after:
    print(f"     - {v.voucher_type} | {v.party_name} | ₹{v.amount} | {v.date}")
db.close()

# Step 6: Verify Data Changed
print("\n6. Verification:")
if len(vouchers_after) != len(vouchers_before):
    print(f"   ✅ Data CHANGED! ({len(vouchers_before)} → {len(vouchers_after)} vouchers)")
else:
    # Check if any voucher data changed
    changed = False
    for v_after in vouchers_after:
        found = False
        for v_before in vouchers_before:
            if (v_after.voucher_number == v_before.voucher_number and 
                v_after.date == v_before.date and
                v_after.party_name == v_before.party_name and
                v_after.amount == v_before.amount):
                found = True
                break
        if not found:
            changed = True
            break
    
    if changed:
        print(f"   ✅ Data UPDATED! (Same count but different content)")
    else:
        print(f"   ❌ Data DID NOT CHANGE!")

# Step 7: Test API
print("\n7. Testing API endpoint...")
r = requests.get('http://127.0.0.1:8001/reports/daybook', headers={'x-api-key': 'k24-secret-key-123'})
if r.status_code == 200:
    data = r.json()
    print(f"   ✅ API works! Returns {len(data)} vouchers")
else:
    print(f"   ❌ API failed: {r.status_code}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
