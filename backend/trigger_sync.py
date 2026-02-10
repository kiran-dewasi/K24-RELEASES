import requests
import json
import time

BASE_URL = "http://localhost:8000"

def trigger_sync():
    print("[INFO] Triggering Comprehensive Sync...")
    try:
        # Trigger Sync
        res = requests.post(f"{BASE_URL}/api/sync/comprehensive", json={"mode": "incremental"})
        print(f"Sync Status Code: {res.status_code}")
        print(f"Sync Response: {res.text}")
        
        # Also trigger Item Complete to be sure
        res_items = requests.post(f"{BASE_URL}/api/sync/items/complete")
        print(f"Items Sync Status: {res_items.status_code}")
    except Exception as e:
        print(f"[ERROR] Sync Failed: {e}")

if __name__ == "__main__":
    trigger_sync()
