import requests
import json

API_URL = "http://localhost:8001/chat"
API_KEY = "k24-secret-key-123"

def test_gstin_update_real_party():
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }
    
    # Test with actual party that exists in Tally
    payload = {
        "message": "Update GSTIN for Prince Ent to 27ABCDE1234F1Z5",
        "user_id": "test_user"
    }
    
    print(f"📤 Sending request: {payload['message']}")
    print(f"🔑 TALLY_LIVE_UPDATE_ENABLED should be: true")
    print("-" * 60)
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        print(f"\n✅ Status Code: {response.status_code}")
        print("\n📥 Response:")
        result = response.json()
        print(json.dumps(result, indent=2))
        
        # Check if workflow executed
        if result.get("workflow_result"):
            workflow = result["workflow_result"]
            print(f"\n📊 Workflow Status: {workflow.get('status')}")
            print(f"💬 Message: {workflow.get('message')}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING GSTIN UPDATE WITH REAL TALLY PARTY")
    print("=" * 60)
    print()
    test_gstin_update_real_party()
    print()
    print("=" * 60)
    print("NEXT: Check Tally to verify the GSTIN was actually updated!")
    print("=" * 60)
