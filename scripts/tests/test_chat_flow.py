"""
Test Conversational AI Flow
Verifies that /chat endpoint correctly handles intents and context.
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8001"

def test_chat():
    print("="*60)
    print("KITTU  ")
    print("="*60)
    
    # 1. Test Reconciliation Intent
    print("\n1. Testing Reconciliation Request...")
    payload = {
        "user_id": "test_user_1",
        "message": "Reconcile invoices for Vasudev Enterprises",
        "company": "SHREE JI SALES"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Intent: {data['intent']['action']} (Confidence: {data['intent']['confidence']:.2f})")
        print(f"✅ Entity: {data['intent']['entity']}")
        print(f"✅ Response: {data['response']}")
        
        if "context" in data:
            print(f"✅ Context Updated: Company={data['context']['company']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Detail: {e.response.text}")

    # 2. Test Context Persistence (Follow-up)
    print("\n2. Testing Context Persistence...")
    payload = {
        "user_id": "test_user_1",
        "message": "What is the status?" # Ambiguous, but should have context
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=payload)
        data = response.json()
        print(f"✅ Response: {data['response']}")
        print(f"✅ History Length: {len(data['context']['conversation_history'])}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

    # 3. Test General Query (Fallback to Agent)
    print("\n3. Testing General Query...")
    payload = {
        "user_id": "test_user_1",
        "message": "Who are my top creditors?"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=payload)
        data = response.json()
        print(f"✅ Intent: {data['intent']['action']}")
        print(f"✅ Response: {data['response'][:100]}...") # Truncate
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_chat()
