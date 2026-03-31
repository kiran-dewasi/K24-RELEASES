
import requests
import json
import time

def test_auth_and_config():
    base_url = "http://localhost:8000/api"
    
    # 1. Test Login with Lowercase and Whitespace (Testing Change 1)
    print("--- Testing Change 1: Case-insensitive & Strip Login ---")
    login_payload = {
        "email": "  AI.KRISHA24@GMAIL.COM  ", # Test case sensitivity and whitespace
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{base_url}/auth/login", json=login_payload)
        print(f"Login Status: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Login failed: {response.text}")
            return
        
        data = response.json()
        token = data.get("access_token")
        user_role = data.get("user", {}).get("role")
        print(f"✅ Login success! Role: {user_role}")
        
        if user_role != "owner":
            print(f"❌ Expected 'owner' role but got '{user_role}'")
        else:
            print("✅ Role verification passed.")
            
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Test PUT /api/tenant/whatsapp-config
        print("\n--- Testing PUT /api/tenant/whatsapp-config ---")
        config_payload = {
            "whatsapp_number": "919999988888",
            "is_active": True
        }
        
        put_response = requests.put(f"{base_url}/tenant/whatsapp-config", json=config_payload, headers=headers)
        print(f"PUT Status: {put_response.status_code}")
        if put_response.status_code == 200:
            print("✅ PUT success!")
            print("Response:", json.dumps(put_response.json(), indent=2))
        else:
            print(f"❌ PUT failed: {put_response.text}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    # Give server a moment to settle if needed
    time.sleep(1)
    test_auth_and_config()
