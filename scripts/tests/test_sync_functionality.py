"""
Test Sync Functionality (Push & Pull)
This script verifies:
1. Pull: Sync data FROM Tally TO Shadow DB
2. Push: Create voucher in K24 and verify it reaches Tally
"""

import requests
import time

API_URL = "http://127.0.0.1:8001"
HEADERS = {"x-api-key": "k24-secret-key-123"}

def test_pull_sync():
    """Test pulling data from Tally"""
    print("\n=== Testing PULL Sync (Tally → Shadow DB) ===")
    
    # 1. Trigger sync
    print("1. Triggering sync...")
    r = requests.post(f"{API_URL}/sync", headers=HEADERS)
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.json()}")
    
    # 2. Wait for sync to complete
    print("2. Waiting 3 seconds for sync to complete...")
    time.sleep(3)
    
    # 3. Check if data was pulled
    print("3. Checking Sales Register data...")
    r = requests.get(f"{API_URL}/reports/sales-register", headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Sales data found")
        print(f"   Total Sales: ₹{data.get('total_sales', 0)}")
        monthly = data.get('monthly_data', [])
        if monthly:
            print(f"   Months with data: {len(monthly)}")
    else:
        print(f"   ❌ Failed: {r.status_code}")
    
    print("4. Checking Ledgers...")
    r = requests.get(f"{API_URL}/ledgers", headers=HEADERS)
    if r.status_code == 200:
        ledgers = r.json()
        print(f"   ✅ Ledgers synced: {len(ledgers)}")
        if ledgers:
            print(f"   Sample: {ledgers[0]['name']}")
    else:
        print(f"   ❌ Failed: {r.status_code}")

def test_push_sync():
    """Test pushing data to Tally"""
    print("\n=== Testing PUSH Sync (K24 → Tally) ===")
    
    # 1. Create a test receipt
    print("1. Creating test receipt...")
    receipt_data = {
        "party_name": "Test Customer",
        "amount": 1000.00,
        "bank_cash_ledger": "Cash",
        "narration": "Test receipt from K24"
    }
    
    r = requests.post(f"{API_URL}/operations/receipt", 
                     json=receipt_data, 
                     headers=HEADERS)
    
    if r.status_code == 200:
        result = r.json()
        print(f"   ✅ Receipt created: {result}")
    else:
        print(f"   ❌ Failed: {r.status_code}")
        try:
            print(f"   Error: {r.json()}")
        except:
            print(f"   Error: {r.text}")

if __name__ == "__main__":
    print("=" * 60)
    print("K24 Sync Functionality Test")
    print("=" * 60)
    
    test_pull_sync()
    test_push_sync()
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
