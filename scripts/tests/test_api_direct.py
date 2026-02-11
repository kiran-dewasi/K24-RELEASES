import requests
import json

url = "http://localhost:8001/vouchers/receipt"
headers = {
    "Content-Type": "application/json",
    "x-api-key": "k24-secret-key-123"
}
data = {
    "party_name": "ApiDirectTest",
    "amount": 555,
    "deposit_to": "Cash",
    "narration": "Testing Direct API",
    "date": "2025-11-29"
}

print("Sending POST request to", url)
print("Data:", json.dumps(data, indent=2))

response = requests.post(url, headers=headers, json=data)

print("\nResponse Status:", response.status_code)
print("Response Body:")
print(json.dumps(response.json(), indent=2))
