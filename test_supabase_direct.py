"""
Test Supabase API directly using the new key format
"""
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
anon_key = os.getenv("SUPABASE_ANON_KEY")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print("Testing Supabase API with new key format...")
print(f"URL: {url}")
print(f"Anon Key: {anon_key[:30]}...")
print(f"Service Key: {service_key[:30]}...")

# Test with anon key
headers = {
    "apikey": anon_key,
    "Authorization": f"Bearer {anon_key}"
}

print("\n1. Testing with Anon Key...")
try:
    response = httpx.get(f"{url}/rest/v1/", headers=headers, timeout=10)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"   Error: {e}")

# Test with service role key
headers_service = {
    "apikey": service_key,
    "Authorization": f"Bearer {service_key}"
}

print("\n2. Testing with Service Role Key...")
try:
    response = httpx.get(f"{url}/rest/v1/", headers=headers_service, timeout=10)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"   Error: {e}")

# Test auth endpoint
print("\n3. Testing Auth Health...")
try:
    response = httpx.get(f"{url}/auth/v1/health", headers=headers, timeout=10)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"   Error: {e}")
