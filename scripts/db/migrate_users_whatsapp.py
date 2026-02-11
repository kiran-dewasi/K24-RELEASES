import sys
import os
# Ensure project root is in path
sys.path.append(os.getcwd())

from backend.database import engine
from sqlalchemy import text, inspect

def run_migration():
    print(f"Checking database: {engine.url}")
    inspector = inspect(engine)
    
    # Check if 'users' table exists
    if not inspector.has_table("users"):
        print("Table 'users' does not exist. create_all() should have created it. Run init_db first if needed.")
        return

    columns = [c['name'] for c in inspector.get_columns("users")]
    print(f"Existing columns: {columns}")
    
    is_sqlite = "sqlite" in str(engine.url)
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. whatsapp_number
            if "whatsapp_number" not in columns:
                print("Adding whatsapp_number...")
                conn.execute(text("ALTER TABLE users ADD COLUMN whatsapp_number TEXT"))
            else:
                print("✓ whatsapp_number exists")

            # 2. whatsapp_verification_code
            if "whatsapp_verification_code" not in columns:
                print("Adding whatsapp_verification_code...")
                conn.execute(text("ALTER TABLE users ADD COLUMN whatsapp_verification_code TEXT"))
            else:
                print("✓ whatsapp_verification_code exists")

            # 3. is_whatsapp_verified
            if "is_whatsapp_verified" not in columns:
                print("Adding is_whatsapp_verified...")
                conn.execute(text("ALTER TABLE users ADD COLUMN is_whatsapp_verified BOOLEAN DEFAULT FALSE"))
            else:
                print("✓ is_whatsapp_verified exists")

            # 4. whatsapp_linked_at
            if "whatsapp_linked_at" not in columns:
                print("Adding whatsapp_linked_at...")
                if is_sqlite:
                    conn.execute(text("ALTER TABLE users ADD COLUMN whatsapp_linked_at DATETIME"))
                else:
                    conn.execute(text("ALTER TABLE users ADD COLUMN whatsapp_linked_at TIMESTAMP WITH TIME ZONE"))
            else:
                print("✓ whatsapp_linked_at exists")

            # 5. Index
            indexes = [i['name'] for i in inspector.get_indexes("users")]
            if "idx_users_whatsapp_number" not in indexes:
                print("Creating unique index idx_users_whatsapp_number...")
                # SQLite supports partial indexes in modern versions, Postgres does too.
                conn.execute(text("CREATE UNIQUE INDEX idx_users_whatsapp_number ON users(whatsapp_number) WHERE whatsapp_number IS NOT NULL"))
            else:
                print("✓ Index idx_users_whatsapp_number exists")

            trans.commit()
            print("\nSUCCESS: All WhatsApp columns and constraints are present.")
        except Exception as e:
            trans.rollback()
            print(f"\nERROR: Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
