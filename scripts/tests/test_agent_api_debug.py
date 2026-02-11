# K24 AI Agent - API Test Script (Debug Mode)
# ===========================================
# Test the agent system via API calls to debug "Unknown error"

import requests
import json

BASE_URL = "http://127.0.0.1:8001"
HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": "k24-secret-key-123"
}

def test_chat_message(message, test_name):
    """Test a specific chat message"""
    print("\n" + "="*60)
    print(f"TEST: {test_name}")
    print(f"Message: '{message}'")
    print("="*60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/agent/chat",
            json={"message": message, "auto_approve": False},
            headers=HEADERS
        )
        
        print(f"Status Code: {response.status_code}")
        
        try:
            result = response.json()
            print(f"Response JSON:")
            print(json.dumps(result, indent=2))
            return result
        except json.JSONDecodeError:
            print(f"Response Text (Not JSON):")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"Request Failed: {e}")
        return None

if __name__ == "__main__":
    print("🚀 K24 AI Agent - Debug Testing")
    
    # Test 1: "hey" (The message that caused the error)
    test_chat_message("hey", "Greeting / Unknown Intent")
    
    # Test 2: "Create receipt for Test Customer for 5000" (Known working intent)
    test_chat_message("Create receipt for Test Customer for 5000", "Valid Intent")
