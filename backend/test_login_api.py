
import requests
import json

def test_login():
    url = "http://localhost:8000/api/auth/login"
    payload = {
        "email": "kittu@krishasales.com",
        "password": "password123"
    }
    
    try:
        print(f"Attempting login to {url}...")
        response = requests.post(url, json=payload)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Login SUCCESS!")
            print("Token:", response.json().get('access_token')[:20] + "...")
        else:
            print("❌ Login FAILED")
            print("Response:", response.text)
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_login()
