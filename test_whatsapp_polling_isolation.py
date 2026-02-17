"""
Test script for WhatsApp polling tenant isolation.

Tests the GET /api/whatsapp/cloud/jobs/{tenant_id} endpoint
to verify tenant validation and subscription enforcement.
"""

import requests
import os
from datetime import datetime, timedelta, timezone

# Configuration
CLOUD_URL = os.getenv("CLOUD_API_URL", "http://localhost:8000")
API_KEY = os.getenv("DESKTOP_API_KEY", "test_api_key")

def test_polling_endpoint():
    """Test the WhatsApp polling endpoint with various scenarios"""
    
    print("="*60)
    print("WhatsApp Polling Tenant Isolation Tests")
    print("="*60)
    
    headers = {"X-API-Key": API_KEY}
    
    # Test 1: Valid tenant with active subscription
    print("\n[Test 1] Valid tenant with active subscription")
    tenant_id = "test_tenant_active_123"
    response = requests.get(
        f"{CLOUD_URL}/api/whatsapp/cloud/jobs/{tenant_id}",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success: {data.get('count')} messages")
        print(f"Response keys: {list(data.keys())}")
    else:
        print(f"Response: {response.json()}")
    
    # Test 2: Non-existent tenant
    print("\n[Test 2] Non-existent tenant")
    tenant_id = "nonexistent_tenant_999"
    response = requests.get(
        f"{CLOUD_URL}/api/whatsapp/cloud/jobs/{tenant_id}",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 404:
        data = response.json()
        print(f"✅ Correct 404: {data['detail']['error']}")
        print(f"Message: {data['detail']['detail']}")
    else:
        print(f"❌ Expected 404, got {response.status_code}")
    
    # Test 3: Tenant with expired subscription
    print("\n[Test 3] Tenant with expired subscription")
    tenant_id = "test_tenant_expired_123"
    response = requests.get(
        f"{CLOUD_URL}/api/whatsapp/cloud/jobs/{tenant_id}",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 403:
        data = response.json()
        print(f"✅ Correct 403: {data['detail']['error']}")
        print(f"Message: {data['detail']['detail']}")
    else:
        print(f"Response: {response.json()}")
    
    # Test 4: Missing API key
    print("\n[Test 4] Missing API key")
    tenant_id = "test_tenant_active_123"
    response = requests.get(
        f"{CLOUD_URL}/api/whatsapp/cloud/jobs/{tenant_id}"
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 401:
        print(f"✅ Correct 401: API key required")
    else:
        print(f"❌ Expected 401, got {response.status_code}")
    
    # Test 5: Invalid API key
    print("\n[Test 5] Invalid API key")
    tenant_id = "test_tenant_active_123"
    response = requests.get(
        f"{CLOUD_URL}/api/whatsapp/cloud/jobs/{tenant_id}",
        headers={"X-API-Key": "invalid_key_123"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 401:
        print(f"✅ Correct 401: Invalid API key")
    else:
        print(f"❌ Expected 401, got {response.status_code}")
    
    print("\n" + "="*60)
    print("Tests completed!")
    print("="*60)

if __name__ == "__main__":
    try:
        test_polling_endpoint()
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
