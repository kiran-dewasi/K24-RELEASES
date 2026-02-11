
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import datetime

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL not found")
    exit(1)

print(f"Connecting to DB: {DATABASE_URL.split('@')[1]}") # Hide password

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Check if exists
        check = conn.execute(text("SELECT count(*) FROM vouchers WHERE voucher_number = 'FORCE-SQL-001'"))
        if check.scalar() == 0:
            # Generate GUID?
            # Vouchers table might require more fields? 
            # Let's inspect columns or just try minimal.
            # Usually Supabase tables have defaults.
            
            sql = text("""
                INSERT INTO vouchers 
                (tenant_id, voucher_number, voucher_type, date, amount, party_name, sync_status, narration, source, guid) 
                VALUES 
                (:tid, :vnum, :vtype, :date, :amt, :party, :status, :narr, :src, :guid)
            """)
            
            params = {
                "tid": "TENANT-12345",
                "vnum": "FORCE-SQL-001",
                "vtype": "Receipt",
                "date": datetime.datetime.now(),
                "amt": 500.0,
                "party": "Sagar Traders - TEST",
                "status": "SYNCED",
                "narr": "Forced via SQL bypass RLS",
                "src": "manual_sql",
                "guid": "RESTORED-1"
            }
            conn.execute(sql, params)
            conn.commit()
            print("✅ SQL INSERT SUCCESS!")
        else:
            print("⚠️ Already Exists.")
            
except Exception as e:
    print(f"❌ SQL Error: {e}")
