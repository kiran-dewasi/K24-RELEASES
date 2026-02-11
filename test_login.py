import requests
import sys

def test_login():
    url = "http://127.0.0.1:8001/api/auth/login"
    payload = {
        "email": "kittu@krishasales.com",
        "password": "password123"
    }
    
    try:
        print(f"Testing login at {url}...")
        response = requests.post(url, json=payload, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                print("[SUCCESS] Login Successful! Access Token received.")
                print(f"Token: {data['access_token'][:20]}...")
            else:
                print("[FAIL] Login Failed: No access_token in response.")
                print(response.text)
        else:
            print("[FAIL] Login Failed.")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"[FAIL] Connection Failed: {e}")

if __name__ == "__main__":
    test_login()
