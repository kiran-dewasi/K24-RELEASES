"""
Test CORE features of the application (Dashboard & Tally).
Ensures the backend sidecar is stable for desktop use.
"""
import requests
import sys
import json
import time
import os

BASE_URL = "http://localhost:8000"
API_KEY = "k24-secret-key-123" # From .env
TOKEN = None

def get_auth_token():
    """Get a valid token for testing."""
    global TOKEN
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "kittu@krishasales.com",
            "password": "password123"
        })
        if resp.status_code == 200:
            TOKEN = resp.json()["access_token"]
            return True
        return False
    except:
        return False

def test_endpoint(name, method, path, expected_status=200, use_api_key=False, use_token=False):
    """Test a specific endpoint and print results."""
    headers = {}
    
    # 🚨 BOTH might be required for some endpoints!
    if use_api_key:
        headers["x-api-key"] = API_KEY
    
    if use_token and TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
        
    url = f"{BASE_URL}{path}"
    
    print(f"\nTesting {name} ({method} {path})...")
    try:
        start = time.time()
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=10)
        else:
            resp = requests.post(url, headers=headers, timeout=10)
        duration = time.time() - start
        
        print(f"  Status: {resp.status_code} (Expected: {expected_status})")
        print(f"  Time: {duration:.2f}s")
        
        if resp.status_code == expected_status:
            try:
                data = resp.json()
                preview = json.dumps(data, indent=2)[:200].replace("\n", " ") + "..."
                print(f"  Data: {preview}")
                return True
            except:
                print(f"  Body: {resp.text[:100]}")
                return True
        else:
            print(f"  [FAIL] Error: {resp.text[:200]}")
            return False
            
    except Exception as e:
        print(f"  [CRITICAL] Endpoint crashed or unreachable: {e}")
        return False

def main():
    print("="*50)
    print("  K24 CORE FEATURE READINESS TEST")
    print("="*50)
    
    # 1. Auth Check
    if not get_auth_token():
        print("[FATAL] Could not login. Backend might be down or credentials wrong.")
        return

    # 2. Checklist
    tests = [
        # Dashboard uses x-api-key AND token (for tenant_id logic inside)
        ("Dashboard Stats", "GET", "/api/dashboard/stats", 200, True, False),
        
        # Voucher uses get_api_key AND get_current_tenant_id (user token required)
        ("Vouchers (Daybook)", "GET", "/api/vouchers?limit=5", 200, True, True),
        
        # Sync Status
        ("Tally Sync Status", "GET", "/api/sync/status", 200, False, True),
        
        # Search API - CORRECTED URL
        ("Search Global", "GET", "/api/search/global?q=test", 200, False, False),
    ]
    
    passed = 0
    total = len(tests)
    for name, method, path, status, use_key, use_token in tests:
        if test_endpoint(name, method, path, status, use_key, use_token):
            passed += 1
            
    print("\n" + "="*50)
    print(f"RESULTS: {passed}/{total} API Endpoints Operational")
    print("="*50)
    
    if passed == total:
        print("✅ Backend SIDECAR is ready for Desktop Build.")
    else:
        print("⚠️ Some endpoints failed. Check logs above.")

if __name__ == "__main__":
    main()
