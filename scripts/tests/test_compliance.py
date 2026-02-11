import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8001"
HEADERS = {"x-api-key": "k24-secret-key-123"}

def create_receipt(party, amount, date, reason="Test Entry"):
    url = f"{BASE_URL}/vouchers/receipt"
    data = {
        "party_name": party,
        "amount": amount,
        "date": date,
        "narration": f"Compliance Test {amount}",
        "reason": reason
    }
    try:
        res = requests.post(url, json=data, headers=HEADERS)
        print(f"Created Receipt: {party} ₹{amount} ({date}) -> Status: {res.status_code}")
        if res.status_code != 200:
            print("Error:", res.text)
        return res.json()
    except Exception as e:
        print(f"Failed to create receipt: {e}")

def check_dashboard():
    url = f"{BASE_URL}/compliance/dashboard-stats"
    res = requests.get(url, headers=HEADERS)
    print("\n--- Dashboard Stats ---")
    print(json.dumps(res.json(), indent=2))

def check_audit_logs():
    url = f"{BASE_URL}/compliance/audit-logs"
    res = requests.get(url, headers=HEADERS)
    print("\n--- Audit Logs (Latest 3) ---")
    logs = res.json()
    for log in logs[:3]:
        print(f"[{log['timestamp']}] {log['action']} by {log['user_id']}: {log['reason']}")

def main():
    print("🚀 Starting Compliance System Test...")
    
    # 1. Normal Entry
    create_receipt("Jane Doe", 5000, datetime.now().strftime("%Y-%m-%d"), "Normal Business")
    
    # 2. High Value Entry (>2L)
    create_receipt("Jane Doe", 250000, datetime.now().strftime("%Y-%m-%d"), "Big Deal")
    
    # 3. Backdated Entry (5 days ago)
    back_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    create_receipt("Jane Doe", 10000, back_date, "Forgot to enter")
    
    # 4. Weekend Entry (Force a Saturday date if today isn't)
    # 2025-11-29 is Saturday. So today is Saturday.
    # The system uses current date for weekend check logic in engine.py if I recall correctly, 
    # or the voucher date. Let's check engine.py.
    # It checks v.date. So if I use today (Saturday), it should flag.
    
    # Run Scan manually to update flags (since flags are updated on scan, not creation in my current implementation?)
    # Wait, I implemented `run_forensic_scan` but didn't hook it into creation.
    # So I need to call /compliance/run-scan
    
    print("\nRunning Forensic Scan...")
    requests.post(f"{BASE_URL}/compliance/run-scan", headers=HEADERS)
    
    # Verify
    check_dashboard()
    check_audit_logs()

if __name__ == "__main__":
    main()
