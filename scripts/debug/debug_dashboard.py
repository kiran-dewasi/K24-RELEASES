
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Supabase credentials missing (check .env)")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print(f"\n{'='*50}")
print("🔍 DASHBOARD DIAGNOSTIC TOOL")
print(f"{'='*50}\n")

# 1. Check Users
print("--- USERS ---")
try:
    users = supabase.table("users").select("*").execute()
    for u in users.data:
        print(f"User: {u.get('username')} | Role: {u.get('role')} | Tenant: {u.get('tenant_id')} | ID: {u.get('id')}")
except Exception as e:
    print(f"Error fetching users: {e}")

# 2. Check Vouchers
print("\n--- VOUCHERS (Showing All) ---")
try:
    # Use raw generic query to see everything
    vouchers = supabase.table("vouchers").select("*").order("date", desc=True).limit(10).execute()
    if not vouchers.data:
        print("NO VOUCHERS FOUND IN DB!")
    for v in vouchers.data:
        print(f"Voucher: {v.get('voucher_number')} | Type: {v.get('voucher_type')} | Date: {v.get('date')} | Amount: {v.get('amount')} | Tenant: {v.get('tenant_id')} | Party: {v.get('party_name')}")
except Exception as e:
    print(f"Error fetching vouchers: {e}")

print(f"\n{'='*50}")
