import httpx, json

SUPABASE_URL = "https://gxukvnoiyzizienswgni.supabase.co"
SERVICE_KEY = "sb_secret_qJuJk2q0_hO144oQLmSYxA_6WB_qtkR"

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}

# Query information_schema for all public tables
query = """
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns c 
     WHERE c.table_name = t.table_name AND c.table_schema = 'public') as col_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
"""

resp = httpx.post(
    f"{SUPABASE_URL}/rest/v1/rpc/",
    headers=headers,
    timeout=15,
)

# Use the SQL endpoint via the pg_tables approach
resp2 = httpx.get(
    f"{SUPABASE_URL}/rest/v1/",
    headers=headers,
    timeout=15,
)

# Try direct SQL via supabase's sql API path
resp3 = httpx.post(
    f"{SUPABASE_URL}/rest/v1/rpc/get_table_list",
    headers=headers,
    json={},
    timeout=15,
)

print("=== Listing all public tables via REST ===")

# List each known table by trying to SELECT from it
known_tables = [
    "users_profile", "business_profile", "contacts",
    "subscriptions", "whatsapp_bindings", "device_licenses",
    "tenants", "plans", "tenant_plans", "billing_cycles",
    "credit_rules", "usage_events", "tenant_usage_summary", "llm_calls",
    "subscription_intents", "onboarding_states",
    "tenant_config", "whatsapp_queue", "tally_operations_log",
]

results = {}
for table in known_tables:
    r = httpx.get(
        f"{SUPABASE_URL}/rest/v1/{table}?select=*&limit=1",
        headers=headers,
        timeout=10,
    )
    exists = r.status_code == 200
    count_r = httpx.get(
        f"{SUPABASE_URL}/rest/v1/{table}?select=count",
        headers={**headers, "Prefer": "count=exact"},
        timeout=10,
    )
    count = count_r.headers.get("content-range", "?").split("/")[-1] if count_r.status_code == 200 else "N/A"
    
    status = f"✅ EXISTS (rows: {count})" if exists else f"❌ NOT FOUND ({r.status_code})"
    results[table] = status
    print(f"  {table:35s} {status}")

print("\n=== Columns for key tables ===")

for table in ["subscriptions", "plans", "tenant_plans", "tenants", "users_profile"]:
    r = httpx.get(
        f"{SUPABASE_URL}/rest/v1/{table}?select=*&limit=1",
        headers=headers,
        timeout=10,
    )
    if r.status_code == 200 and r.json():
        cols = list(r.json()[0].keys())
        print(f"\n{table}: {cols}")
    else:
        print(f"\n{table}: (empty or not found)")
