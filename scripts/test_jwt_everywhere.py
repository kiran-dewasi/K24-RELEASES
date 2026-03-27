import os
import sys
import requests
import json

# Configuration from environment variables with sane defaults
BASE_URL = os.getenv("BASE_URL", "http://localhost:8001").rstrip("/")
LOGIN_EMAIL = os.getenv("LOGIN_EMAIL")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD")
API_KEY = os.getenv("API_KEY")

def login_and_get_token():
    """
    Authenticates against the real backend /api/auth/login endpoint.
    On success, returns the access_token.
    On failure, prints the error and exits.
    """
    if not LOGIN_EMAIL or not LOGIN_PASSWORD:
        print("Error: LOGIN_EMAIL and LOGIN_PASSWORD environment variables must be set.")
        sys.exit(1)

    login_url = f"{BASE_URL}/api/auth/login"
    payload = {
        "username": LOGIN_EMAIL, # OAuth2PasswordRequestForm uses 'username'
        "password": LOGIN_PASSWORD
    }

    try:
        # Standard login expects form data (OAuth2PasswordRequestForm)
        response = requests.post(login_url, data=payload, timeout=10)
        
        # Fallback to JSON if form fails with 422
        if response.status_code == 422:
            response = requests.post(login_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access_token")
            if token:
                print(f"Logged in successfully. Token: {token[:10]}...")
                return token
            else:
                print(f"Error: No access_token found in response from {login_url}")
                sys.exit(1)
        else:
            print(f"Login failed: POST {login_url} -> status {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"Exception during login: {e}")
        sys.exit(1)

def make_request(method, path, token):
    """
    Makes an authenticated request using JWT token.
    Exits on 401, 403, or 5xx.
    """
    url = f"{BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    if API_KEY:
        headers["x-api-key"] = API_KEY

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json={}, timeout=10)
        else:
            print(f"Unsupported method: {method}")
            sys.exit(1)

        status_code = response.status_code
        print(f"{method.upper():<6} {path:<40} -> status {status_code}", end=" ")

        if 200 <= status_code < 300:
            print(" [OK]")
        elif status_code in (401, 403):
            print(f" [AUTH FAILURE] -> {response.text}")
            sys.exit(1)
        elif status_code >= 500:
            print(f" [SERVER ERROR] -> {response.text}")
            sys.exit(1)
        else:
            print(f" [INFO] -> {response.text[:100]}")

        return response
    except Exception as e:
        print(f"\nException during request to {url}: {e}")
        sys.exit(1)

def main():
    print("--- JWT Authentication Regression Test ---")
    print(f"Targeting: {BASE_URL}")
    
    # 1. Login
    token = login_and_get_token()

    # 2. Sequential tests
    test_paths = [
        ("/api/dashboard/stats", "GET"),
        ("/api/reports/sales-register", "GET"),
        ("/api/vouchers", "GET"),
        ("/api/inventory", "GET"),
        ("/reports/gst-summary", "GET"),
        ("/api/bills/receivables", "GET"),
        ("/api/customers/top", "GET"),
        ("/contacts/detailed", "GET"),
        ("/internal/usage/event", "POST"),
        ("/api/whatsapp/settings/whatsapp", "GET"),
        ("/api/whatsapp/contacts/by-whatsapp/test", "GET"),
        ("/api/sync/tally", "POST")
    ]

    print("\n--- Testing Endpoints ---")
    for path, method in test_paths:
        make_request(method, path, token)

    print("\nRegression test completed successfully.")

if __name__ == "__main__":
    main()
