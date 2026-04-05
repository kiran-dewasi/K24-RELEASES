import os
import sys

# Add project root to path so we can import modules
sys.path.append(r"c:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare")

from dotenv import load_dotenv
import httpx

load_dotenv(r"c:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare\.env")

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

headers = {
    "apikey": supabase_key,
    "Authorization": f"Bearer {supabase_key}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

with open("backend/supabase_out_utf8.txt", "w", encoding="utf-8") as f:
    try:
        # Update
        r = httpx.patch(f"{supabase_url}/rest/v1/user_profiles?full_name=eq.NARAYAN", headers=headers, json={"role": "owner"})
        r.raise_for_status()
        f.write(f"Supabase Update Result: {r.json()}\n")

        # Select
        r2 = httpx.get(f"{supabase_url}/rest/v1/user_profiles?select=id,full_name,role&limit=10", headers=headers)
        r2.raise_for_status()
        f.write(f"Supabase Users: {r2.json()}\n")
    except Exception as e:
        f.write(f"Error: {e}\n")
