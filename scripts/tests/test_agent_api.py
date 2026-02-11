# K24 AI Agent - API Test Script
# ===============================
# Test the agent system via API calls

import requests
import json

BASE_URL = "http://127.0.0.1:8001"

def test_health():
    """Test agent health endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/api/v1/agent/health")
    result = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(result, indent=2))
    
    return response.status_code == 200


def test_capabilities():
    """Test capabilities endpoint"""
    print("\n" + "="*60)
    print("TEST 2: Get Capabilities")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/api/v1/agent/capabilities")
    result = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(f"Supported Intents: {len(result.get('capabilities', {}).get('supported_intents', []))}")
    print(f"Features: {len(result.get('capabilities', {}).get('features', []))}")
    
    return response.status_code == 200


def test_chat_simple():
    """Test simple chat request"""
    print("\n" + "="*60)
    print("TEST 3: Simple Chat - Receipt")
    print("="*60)
    
    payload = {
        "message": "Create receipt for Test Customer for ₹5000",
        "auto_approve": False  # Just preview
    }
    
    # Get token first (you may need to adjust this based on your auth)
    # For testing, we'll try without auth first
    headers = {
        "Content-Type": "application/json",
        "x-api-key": "k24-secret-key-123"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/agent/chat",
        json=payload,
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nResponse Status: {result.get('status')}")
        print(f"Message: {result.get('message')}")
        
        if result.get('preview'):
            print(f"\nPreview:")
            print(json.dumps(result.get('preview'), indent=2))
        
        return True
    else:
        print(f"Error: {response.text}")
        return False


def test_chat_query():
    """Test query intent"""
    print("\n" + "="*60)
    print("TEST 4: Query Intent - Outstanding")
    print("="*60)
    
    payload = {
        "message": "Show me outstanding receivables"
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": "k24-secret-key-123"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/agent/chat",
        json=payload,
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nResponse:")
        print(json.dumps(result, indent=2))
        return True
    else:
        print(f"Error: {response.text}")
        return False


if __name__ == "__main__":
    print("🚀 K24 AI Agent - API Testing")
    print("Testing against: " + BASE_URL)
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    results.append(("Capabilities", test_capabilities()))
    results.append(("Chat - Receipt", test_chat_simple()))
    results.append(("Chat -Query", test_chat_query()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED! The agent API is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
