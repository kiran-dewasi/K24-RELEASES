import sqlite3
import os

DB_FILE = "k24_shadow.db"

def fix_schema():
    print(f"Fixing schema for {DB_FILE}...")
    
    if not os.path.exists(DB_FILE):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Add auto_post_to_tally to user_settings
    try:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN auto_post_to_tally BOOLEAN DEFAULT 0")
        print("✅ Added auto_post_to_tally to user_settings")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("ℹ️ auto_post_to_tally already exists in user_settings")
        else:
            print(f"❌ Failed to add auto_post_to_tally: {e}")

    # 2. Add tenant_id to user_settings if missing (based on previous logs, it seemed present, but checking)
    try:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN tenant_id VARCHAR DEFAULT 'default'")
        print("✅ Added tenant_id to user_settings")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            pass # Already exists
        else:
            print(f"❌ Failed to add tenant_id: {e}")

    conn.commit()
    conn.close()
    print("Schema fix complete.")

if __name__ == "__main__":
    fix_schema()
