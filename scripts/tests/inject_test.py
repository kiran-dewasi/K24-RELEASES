
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
TENANT_ID = "TENANT-12345"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Injecting Test Voucher...")
try:
    record = {
        "tenant_id": TENANT_ID,
        "voucher_number": "FORCE-TEST-001",
        "voucher_type": "Receipt",
        "party_name": "Sagar Traders Dhule",
        "amount": 100.0,
        "date": "2025-12-16",
        "narration": "Forced Test Entry to Verify Dashboard Visibility",
        "sync_status": "SYNCED",
        "source": "manual_test"
    }
    
    count = supabase.table("vouchers").select("*", count="exact").eq("voucher_number", "FORCE-TEST-001").execute().count
    if count == 0:
        res = supabase.table("vouchers").insert(record).execute()
        print(f"Inserted: {res.data}")
    else:
        print("Test voucher already exists.")
        
except Exception as e:
    print(f"Error: {e}")
