import requests
import json
import os

API_URL = "http://localhost:8001/chat"
API_KEY = "k24-secret-key-123"

def test_gstin_update():
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }
    
    # Test case 1: Valid request
    payload = {
        "message": "Update GSTIN for Prince Enterprises to 27ABCDE1234F1Z5",
        "user_id": "test_user"
    }
    
    print(f"Sending request: {payload['message']}")
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        print(f"Status Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Request failed: {e}")

    # Test case 2: Missing GSTIN
    payload = {
        "message": "Update GSTIN for Prince Enterprises",
        "user_id": "test_user"
    }
    
    print(f"\nSending request: {payload['message']}")
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        print(f"Status Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_gstin_update()
