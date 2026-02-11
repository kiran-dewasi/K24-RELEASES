"""
Test script to verify the fixed follow-up logic
"""

import requests
import json

API_URL = "http://127.0.0.1:8001/chat"
HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": "k24-secret-key-123"
}

def test_greeting():
    """Test that casual greetings don't trigger follow-ups"""
    print("=" * 60)
    print("TEST 1: Casual Greeting (should NOT ask follow-up)")
    print("=" * 60)
    
    response = requests.post(
        API_URL,
        headers=HEADERS,
        json={"message": "hii whats up", "user_id": "test_user_1"}
    )
    
    data = response.json()
    print(f"User: hii whats up")
    print(f"Response Type: {data.get('type')}")
    print(f"Response: {data.get('response', 'N/A')[:200]}")
    
    if data.get('type') == 'follow_up':
        print("❌ FAIL: Should not ask follow-up for greeting!")
    else:
        print("✅ PASS: Responded normally without follow-up")
    print()

def test_incomplete_intent():
    """Test that incomplete transaction intent asks for missing info"""
    print("=" * 60)
    print("TEST 2: Incomplete Transaction (SHOULD ask follow-up)")
    print("=" * 60)
    
    response = requests.post(
        API_URL,
        headers=HEADERS,
        json={"message": "Create a sale for Prince Ent", "user_id": "test_user_2"}
    )
    
    data = response.json()
    print(f"User: Create a sale for Prince Ent")
    print(f"Response Type: {data.get('type')}")
    print(f"Response: {data.get('response', 'N/A')[:200]}")
    
    if data.get('type') == 'follow_up':
        print(f"✅ PASS: Asked follow-up - {data.get('response')}")
        print(f"Missing slots: {data.get('missing_slots', [])}")
    else:
        print("❌ FAIL: Should ask for missing amount!")
    print()

def test_generic_query():
    """Test that data queries work normally"""
    print("=" * 60)
    print("TEST 3: Data Query (should answer normally)")
    print("=" * 60)
    
    response = requests.post(
        API_URL,
        headers=HEADERS,
        json={"message": "Show me today's sales", "user_id": "test_user_3"}
    )
    
    data = response.json()
    print(f"User: Show me today's sales")
    print(f"Response Type: {data.get('type')}")
    print(f"Response: {data.get('response', 'N/A')[:200]}...")
    
    if data.get('type') != 'follow_up':
        print("✅ PASS: Responded with data/text, no follow-up")
    else:
        print("❌ FAIL: Should not ask follow-up for queries!")
    print()

if __name__ == "__main__":
    try:
        test_greeting()
        test_incomplete_intent()
        test_generic_query()
        
        print("=" * 60)
        print("SUMMARY: Follow-up logic verification complete")
        print("=" * 60)
    except Exception as e:
        print(f"Error during testing: {e}")
