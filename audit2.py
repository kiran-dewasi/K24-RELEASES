import os
import urllib.request
import json

def parse_env():
    env = {}
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#") and "=" in line:
                    k, v = line.strip().split("=", 1)
                    env[k] = v
    return env

env = parse_env()
SUPABASE_URL = env.get("SUPABASE_URL")
SUPABASE_KEY = env.get("SUPABASE_SERVICE_ROLE_KEY") or env.get("SUPABASE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def query(table, select="*", order="", limit=10):
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}"
    if order:
        url += f"&order={order}"
    url += f"&limit={limit}"
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return str(e)

data = {
    "USER_PROFILES": query("user_profiles", "id,full_name,email,role,tenant_id", "created_at.desc", 15),
    "TENANTS": query("tenants", "id,name,whatsapp_number,created_at", "created_at.desc", 10),
    "TENANT_CONFIG": query("tenant_config", "tenant_id,whatsapp_number,user_email,subscription_status,trial_ends_at", "", 10),
    "WHATSAPP_MESSAGE_QUEUE": query("whatsapp_message_queue", "id,tenant_id,customer_phone,message_type,status,created_at", "created_at.desc", 5)
}

with open("audit2_result.json", "w") as f:
    json.dump(data, f, indent=2)
