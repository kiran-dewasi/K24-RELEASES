"""
Test all auth endpoints to verify they're working.
Run this with: python test_auth_endpoints.py
"""
import requests
import sys
sys.path.insert(0, '.')

BASE_URL = "http://localhost:8000"

def test_endpoint(method, path, data=None, headers=None, expected_status=None):
    """Test an endpoint and return result."""
    url = f"{BASE_URL}{path}"
    print(f"\n{'='*60}")
    print(f"{method} {path}")
    print(f"{'='*60}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        
        print(f"Status: {response.status_code}")
        try:
            print(f"Response: {response.json()}")
        except:
            print(f"Response: {response.text[:200]}")
        
        if expected_status and response.status_code != expected_status:
            print(f"[WARNING] Expected {expected_status}, got {response.status_code}")
        
        return response.status_code, response
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to backend. Is it running on port 8000?")
        return None, None
    except Exception as e:
        print(f"[ERROR] {e}")
        return None, None

def main():
    print("\n" + "="*60)
    print("K24 AUTH ENDPOINTS TEST")
    print("="*60)
    
    # 1. Test root endpoint
    status, _ = test_endpoint("GET", "/")
    if status != 200:
        print("\n[FATAL] Backend is not running!")
        return
    
    # 2. Test Login (with existing user)
    print("\n--- Testing Login ---")
    status, response = test_endpoint("POST", "/api/auth/login", {
        "email": "kittu@krishasales.com",
        "password": "password123"
    })
    
    token = None
    if status == 200:
        data = response.json()
        token = data.get("access_token")
        print(f"[OK] Login successful! Token: {token[:20]}...")
    else:
        print("[ERROR] Login failed")
    
    # 3. Test /me endpoint (requires auth)
    if token:
        print("\n--- Testing /me ---")
        test_endpoint("GET", "/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
    
    # 4. Test Forgot Password
    print("\n--- Testing Forgot Password ---")
    status, _ = test_endpoint("POST", "/api/auth/forgot-password", {
        "email": "test@example.com"
    })
    # This should always return 200 (to prevent email enumeration)
    
    # 5. Test Subscription endpoint
    if token:
        print("\n--- Testing Subscription Status ---")
        test_endpoint("GET", "/api/auth/subscription", headers={
            "Authorization": f"Bearer {token}"
        })
    
    # 6. Test Check Setup
    if token:
        print("\n--- Testing Check Setup ---")
        test_endpoint("GET", "/api/auth/check-setup", headers={
            "Authorization": f"Bearer {token}"
        })
    
    # 7. Test Logout
    if token:
        print("\n--- Testing Logout ---")
        test_endpoint("POST", "/api/auth/logout", headers={
            "Authorization": f"Bearer {token}"
        })
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    
    # Summary
    print("\nSUMMARY:")
    print("- Backend is running: OK")
    print("- Login works: " + ("OK" if token else "FAIL"))
    print("- All endpoints accessible: Check above for details")
    print("\nNOTE: Email sending requires valid Supabase configuration.")
    print("      Configure in Supabase Dashboard > Authentication > Email Templates")

if __name__ == "__main__":
    main()
