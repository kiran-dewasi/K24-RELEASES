"""
Test the new Supabase HTTP Service
"""
import sys
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

from backend.services.supabase_service import supabase_service, supabase_http_service

print("=" * 60)
print("TESTING NEW SUPABASE HTTP SERVICE")
print("=" * 60)

# Test 1: Check if service is initialized
print("\n1. Service Initialization:")
print(f"   Client configured: {supabase_service.client is not None}")
print(f"   HTTP Service URL: {supabase_http_service.url}")

# Test 2: Try to fetch user_profiles (even if empty)
print("\n2. Testing user_profiles table access:")
try:
    result = supabase_service.get_user_profile("test-nonexistent-id")
    print(f"   [OK] Query succeeded (result: {result})")
except Exception as e:
    print(f"   [FAIL] Error: {e}")

# Test 3: Try to fetch subscriptions
print("\n3. Testing subscriptions table access:")
try:
    result = supabase_service.get_user_subscription("test-nonexistent-id")
    print(f"   [OK] Query succeeded (result: {result})")
except Exception as e:
    print(f"   [FAIL] Error: {e}")

# Test 4: Test auth signup (will fail with existing email, but proves connection works)
print("\n4. Testing Auth API:")
try:
    result = supabase_http_service.sign_in("fake@nonexistent.com", "wrong-password")
    print(f"   Result: {result}")
except Exception as e:
    error_str = str(e)
    if "Invalid" in error_str or "credentials" in error_str.lower():
        print(f"   [OK] Auth API responding (invalid credentials as expected)")
    else:
        print(f"   [WARN] Auth error: {error_str}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
