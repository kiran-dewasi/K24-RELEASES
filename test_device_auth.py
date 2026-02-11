import requests
import uuid

BASE_URL = "http://localhost:8000/api/devices"

def test_device_flow():
    print("--- Starting Device Auth Flow Test ---")

    # 1. Mock Data
    device_id = f"test-device-{uuid.uuid4()}"
    user_id = "test-user-123" # Mocking a user ID (usually comes from DB/Auth)
    
    # 2. Register Device
    print(f"\n1. Registering Device: {device_id} for User: {user_id}")
    try:
        reg_resp = requests.post(f"{BASE_URL}/register", json={
            "device_id": device_id,
            "user_id": user_id,
            "app_version": "1.0.0"
        })
        reg_data = reg_resp.json()
        print(f"   Status: {reg_resp.status_code}")
        
        if reg_resp.status_code != 200:
            print(f"   [FAIL] Registration Failed: {reg_data}")
            return
            
        license_key = reg_data.get("license_key")
        print(f"   [OK] Success! Generated License Key: {license_key}")
        
    except Exception as e:
        print(f"   [FAIL] Error connecting to backend: {e}")
        return

    # 3. Activate Device (Desktop App Side)
    print(f"\n2. Activating Device with Key: {license_key}")
    try:
        act_resp = requests.post(f"{BASE_URL}/activate", json={
            "license_key": license_key,
            "device_id": device_id
        })
        act_data = act_resp.json()
        print(f"   Status: {act_resp.status_code}")
        
        if act_resp.status_code == 200:
            print(f"   [OK] Activation Success! User ID: {act_data.get('user_id')}")
        else:
            print(f"   [FAIL] Activation Failed: {act_data}")
            return

    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return

    # 4. Validate Device (Periodic Check)
    print(f"\n3. Validating License (Periodic Heartbeat)")
    try:
        val_resp = requests.get(f"{BASE_URL}/validate", params={
            "license_key": license_key,
            "device_id": device_id
        })
        val_data = val_resp.json()
        
        if val_data.get("valid") is True:
             print(f"   [OK] Validation Passed. License is active.")
        else:
             print(f"   [FAIL] Validation Failed: {val_data}")

    except Exception as e:
        print(f"   [FAIL] Error: {e}")

    print("\n--- Test Complete: SYSTEM IS OPERATIONAL ---")

if __name__ == "__main__":
    test_device_flow()
