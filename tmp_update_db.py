
import sqlite3
import os

db_path = r"C:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare\k24_shadow.db"

if not os.path.exists(db_path):
    print(f"Error: Database file not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Fix 1: Kiran tenant_id uppercase
    cur.execute("""
        UPDATE users SET tenant_id = 'TENANT-2965AF26'
        WHERE email = 'kirankdewasi19@gmail.com'
    """)
    print("Kiran rows updated:", cur.rowcount)

    # Fix 2: Check rows for ai.krisha24@gmail.com
    cur.execute("""
        SELECT id, full_name, email, role, tenant_id 
        FROM users 
        WHERE email = 'ai.krisha24@gmail.com'
    """)
    print("Narayan rows:", cur.fetchall())

    conn.commit()
    conn.close()
    print("\nDatabase changes committed.")
except Exception as e:
    print(f"An error occurred: {e}")
