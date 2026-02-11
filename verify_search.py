
import requests
import json

BASE_URL = "http://localhost:8000"
HEADERS = {"x-api-key": "k24-secret-key-123"}

def verify_search():
    print("🚀 Verifying Global Search Endpoint...\n")
    
    # 1. Search for something generic like 'a' or '1'
    query = "a"
    print(f"[1/1] Searching for '{query}'...")
    try:
        r = requests.get(f"{BASE_URL}/api/search/global", headers=HEADERS, params={"q": query})
        if r.status_code == 200:
            data = r.json()
            print("✅ Response Received")
            print(f"   - Ledgers Found: {len(data.get('ledgers', []))}")
            print(f"   - Vouchers Found: {len(data.get('vouchers', []))}")
            print(f"   - Items Found: {len(data.get('items', []))}")
            
            if data['ledgers']:
                print(f"   Example Ledger: {data['ledgers'][0]['name']}")
        else:
            print(f"❌ Failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_search()
