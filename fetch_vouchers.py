import requests
import json

url = "http://localhost:8001/vouchers"
headers = {
    "x-api-key": "k24-secret-key-123"
}

print("Fetching vouchers from", url)
try:
    response = requests.get(url, headers=headers)
    print("Response Status:", response.status_code)
    if response.status_code == 200:
        vouchers = response.json().get("vouchers", [])
        print(f"Found {len(vouchers)} vouchers.")
        for v in vouchers[:10]: # Print first 10
            print(json.dumps(v, indent=2))
    else:
        print("Error:", response.text)
except Exception as e:
    print("Exception:", e)
