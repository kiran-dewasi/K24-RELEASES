"""
Supabase Schema Inspector
Check what tables and columns already exist in your Supabase project
"""
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

headers = {
    "apikey": service_key,
    "Authorization": f"Bearer {service_key}",
    "Content-Type": "application/json"
}

print("=" * 70)
print("SUPABASE SCHEMA INSPECTOR")
print("=" * 70)
print(f"URL: {url}")
print()

# List of tables we need to check
tables_to_check = [
    "user_profiles",
    "users_profile", 
    "subscriptions",
    "device_licenses",
    "whatsapp_bindings",
    "tenants"
]

print("CHECKING EXISTING TABLES:")
print("-" * 70)

for table in tables_to_check:
    try:
        # Try to get table info by querying it
        response = httpx.get(
            f"{url}/rest/v1/{table}?limit=0",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"  [EXISTS] {table}")
            
            # Try to get a sample row to see columns
            sample_response = httpx.get(
                f"{url}/rest/v1/{table}?limit=1",
                headers=headers,
                timeout=10
            )
            
            if sample_response.status_code == 200:
                data = sample_response.json()
                if data:
                    columns = list(data[0].keys())
                    print(f"           Columns: {', '.join(columns)}")
                    print(f"           Sample: {data[0]}")
                else:
                    print(f"           (empty table - can't determine columns)")
        elif response.status_code == 404:
            print(f"  [MISSING] {table}")
        else:
            print(f"  [ERROR] {table}: {response.status_code} - {response.text[:100]}")
            
    except Exception as e:
        print(f"  [ERROR] {table}: {e}")

print()

# Also check auth.users indirectly
print("CHECKING AUTH USERS (indirect):")
print("-" * 70)
try:
    # We can't directly query auth.users, but we can check if sign-in works
    response = httpx.post(
        f"{url}/auth/v1/token?grant_type=password",
        headers=headers,
        json={"email": "test@nonexistent.com", "password": "fake"},
        timeout=10
    )
    if "Invalid" in response.text:
        print("  [OK] Auth endpoint is working")
    else:
        print(f"  [INFO] Auth response: {response.text[:200]}")
except Exception as e:
    print(f"  [ERROR] {e}")

print()
print("=" * 70)
print("INSPECTION COMPLETE")
print("=" * 70)
print()
print("NEXT STEPS:")
print("- Review which tables exist and their current structure")
print("- The migration should ADD missing tables, not DROP existing ones")
print("- If a table exists but has wrong columns, we need ALTER statements")
