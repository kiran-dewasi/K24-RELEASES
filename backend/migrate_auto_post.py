"""
Add missing auto_post_to_tally column to tenants table.
"""
import sqlite3
import os

DB_PATH = "k24_shadow.db"

def migrate_db():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(tenants)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "auto_post_to_tally" not in columns:
            print("Adding auto_post_to_tally column...")
            cursor.execute("ALTER TABLE tenants ADD COLUMN auto_post_to_tally BOOLEAN DEFAULT 0")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column auto_post_to_tally already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
