import requests
import json

url = "http://127.0.0.1:8001/chat"
headers = {
    "Content-Type": "application/json",
    "x-api-key": "k24-secret-key-123"
}
payload = {
    "message": "Create a sale to Sharma for 5000",
    "user_id": "test_debug",
    "client_context": {"page": "cash-book"}
}

try:
    response = requests.post(url, headers=headers, json=payload)
    print(f"Status: {response.status_code}")
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
