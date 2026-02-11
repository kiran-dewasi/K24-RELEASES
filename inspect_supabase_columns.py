"""
Get detailed column info for existing Supabase tables
"""
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

headers = {
    "apikey": service_key,
    "Authorization": f"Bearer {service_key}",
    "Content-Type": "application/json"
}

print("=" * 70)
print("DETAILED SCHEMA INSPECTION")
print("=" * 70)

# Get the OpenAPI spec which has column info
response = httpx.get(
    f"{url}/rest/v1/",
    headers=headers,
    timeout=30
)

if response.status_code == 200:
    swagger = response.json()
    definitions = swagger.get('definitions', {})
    
    tables_of_interest = ['users_profile', 'subscriptions', 'whatsapp_bindings', 'tenants']
    
    for table in tables_of_interest:
        if table in definitions:
            print(f"\n[TABLE: {table}]")
            print("-" * 50)
            props = definitions[table].get('properties', {})
            required = definitions[table].get('required', [])
            for col, info in props.items():
                col_type = info.get('type', info.get('format', 'unknown'))
                req = "(required)" if col in required else ""
                desc = info.get('description', '')
                print(f"  {col}: {col_type} {req}")
                if 'default' in info:
                    print(f"       default: {info['default']}")
        else:
            print(f"\n[TABLE: {table}] - Not found in schema")
else:
    print(f"Failed to get schema: {response.status_code}")
    print(response.text[:500])

print("\n" + "=" * 70)
