from backend.database import engine
from sqlalchemy import text

def migrate_db():
    print("[INFO] Checking for missing columns...")
    with engine.connect() as conn:
        # Check users table
        try:
            conn.execute(text("SELECT auto_post_to_tally FROM users LIMIT 1"))
        except Exception:
            print("[INFO] Adding 'auto_post_to_tally' to users table")
            conn.execute(text("ALTER TABLE users ADD COLUMN auto_post_to_tally BOOLEAN DEFAULT 0"))

        try:
            conn.execute(text("SELECT tenant_id FROM users LIMIT 1"))
        except Exception:
            print("[INFO] Adding 'tenant_id' to users table")
            conn.execute(text("ALTER TABLE users ADD COLUMN tenant_id VARCHAR DEFAULT 'offline-default'"))
            
        try:
             conn.execute(text("SELECT google_api_key FROM users LIMIT 1"))
        except Exception:
             print("[INFO] Adding 'google_api_key' to users table")
             conn.execute(text("ALTER TABLE users ADD COLUMN google_api_key VARCHAR"))

        # Check companies table
        try:
             conn.execute(text("SELECT tenant_id FROM companies LIMIT 1"))
        except Exception:
             print("[INFO] Adding 'tenant_id' to companies table")
             conn.execute(text("ALTER TABLE companies ADD COLUMN tenant_id VARCHAR DEFAULT 'offline-default'"))

        # Check ledgers table
        try:
             conn.execute(text("SELECT tenant_id FROM ledgers LIMIT 1"))
        except Exception:
             print("[INFO] Adding 'tenant_id' to ledgers table")
             conn.execute(text("ALTER TABLE ledgers ADD COLUMN tenant_id VARCHAR DEFAULT 'offline-default'"))
             
        conn.commit()
    print("[SUCCESS] Migration checks complete.")

if __name__ == "__main__":
    migrate_db()
