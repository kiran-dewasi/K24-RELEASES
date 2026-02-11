from backend.database import engine
from sqlalchemy import text

def run_migration():
    print("🔄 Running Migration: Add source and tally_voucher_id to vouchers...")
    with engine.connect() as conn:
        try:
            # 1. Add source column
            try:
                conn.execute(text("ALTER TABLE vouchers ADD COLUMN source VARCHAR(50) DEFAULT 'web'"))
                print("✅ Added column 'source'")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "no such table" not in str(e).lower(): 
                   print(f"ℹ️ Column 'source' likely exists or other error: {e}")
                else: 
                   print(f"❌ Error adding 'source': {e}")

            # 2. Add tally_voucher_id column
            try:
                conn.execute(text("ALTER TABLE vouchers ADD COLUMN tally_voucher_id VARCHAR(100)"))
                print("✅ Added column 'tally_voucher_id'")
            except Exception as e:
                # SQLite column add might fail if exists
                print(f"ℹ️ Column 'tally_voucher_id' likely exists or other error: {e}")
                
            conn.commit()
            print("✅ Migration Complete (if no errors above).")
            
        except Exception as e:
            print(f"❌ Migration Failed: {e}")

if __name__ == "__main__":
    run_migration()
