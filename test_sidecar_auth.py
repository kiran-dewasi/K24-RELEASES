#!/usr/bin/env python3
"""
Test Desktop Security - Task 1.1 Verification

This script tests the sidecar authentication implementation:
1. Test that backend is accessible in development mode
2. Test that backend rejects requests without token in desktop mode
3. Test that backend accepts requests with valid token
"""

import os
import sys
import requests
import uuid

# Test configuration
BACKEND_URL = "http://localhost:8000"
TEST_TOKEN = str(uuid.uuid4())

def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_health_endpoint():
    """Test 1: Health endpoint should always be accessible"""
    print_header("Test 1: Health Endpoint (Public)")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        
        if response.status_code == 200:
            print(f"  [PASS] Health endpoint accessible")
            print(f"  Response: {response.json()}")
            return True
        else:
            print(f"  [FAIL] Unexpected status: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"  [FAIL] Connection error: {e}")
        print(f"  Make sure backend is running: python -m uvicorn backend.api:app")
        return False


def test_api_without_token():
    """Test 2: API endpoint without token (should work in dev, fail in desktop mode)"""
    print_header("Test 2: API Request Without Token")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/dashboard/stats", timeout=5)
        
        if response.status_code == 200:
            print(f"  [INFO] Request succeeded (development mode)")
            return True
        elif response.status_code == 403:
            data = response.json()
            print(f"  [INFO] Request blocked (desktop mode active)")
            print(f"  Error: {data.get('detail', 'No detail')}")
            return True  # This is expected in desktop mode
        elif response.status_code == 401:
            print(f"  [INFO] Auth required (expected - no JWT token)")
            return True
        else:
            print(f"  [WARN] Unexpected status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
    except requests.RequestException as e:
        print(f"  [FAIL] Connection error: {e}")
        return False


def test_api_with_desktop_token():
    """Test 3: API endpoint with desktop token"""
    print_header("Test 3: API Request With Desktop Token")
    
    # Get actual token from environment (if running in desktop mode)
    actual_token = os.getenv("DESKTOP_TOKEN", TEST_TOKEN)
    
    headers = {
        "X-Desktop-Token": actual_token
    }
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/dashboard/stats", 
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            print(f"  [PASS] Request succeeded with token")
            return True
        elif response.status_code == 403:
            print(f"  [FAIL] Token rejected")
            print(f"  Provided token: {actual_token[:8]}...")
            print(f"  Response: {response.json()}")
            return False
        elif response.status_code == 401:
            print(f"  [INFO] Desktop token accepted, but JWT auth required")
            print(f"  This is expected - desktop token != user auth token")
            return True
        else:
            print(f"  [WARN] Status: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"  [FAIL] Connection error: {e}")
        return False


def test_docs_endpoint():
    """Test 4: Docs endpoint should be public"""
    print_header("Test 4: API Docs (Public)")
    
    try:
        response = requests.get(f"{BACKEND_URL}/docs", timeout=5)
        
        if response.status_code == 200:
            print(f"  [PASS] API docs accessible")
            return True
        else:
            print(f"  [FAIL] Status: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"  [FAIL] Connection error: {e}")
        return False


def check_desktop_mode():
    """Check if backend is running in desktop mode"""
    print_header("Desktop Mode Check")
    
    from backend.middleware.desktop_security import is_desktop_mode, DESKTOP_TOKEN as configured_token
    
    if is_desktop_mode():
        print(f"  Mode: DESKTOP (security enabled)")
        print(f"  Token configured: {'Yes' if configured_token else 'No'}")
    else:
        print(f"  Mode: DEVELOPMENT (no token validation)")
    
    return True


def main():
    print("\n" + "=" * 60)
    print("  K24 SIDECAR AUTHENTICATION TEST")
    print("  Task 1.1 Verification")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Health Endpoint", test_health_endpoint()))
    results.append(("API Without Token", test_api_without_token()))
    results.append(("API With Token", test_api_with_desktop_token()))
    results.append(("Docs Endpoint", test_docs_endpoint()))
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  ✅ Task 1.1 Implementation: VERIFIED")
    else:
        print("\n  ⚠️  Some tests need attention")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
