
import sqlite3
import os

db_path = r"C:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare\k24_shadow.db"

if not os.path.exists(db_path):
    print(f"Error: Database file not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("=== ALL USERS ===")
    cur.execute("SELECT id, full_name, email, role, tenant_id FROM users")
    rows = cur.fetchall()
    for row in rows:
        print(row)

    print("\n=== TOTAL COUNT ===")
    cur.execute("SELECT COUNT(*) FROM users")
    print(cur.fetchone()[0])

    conn.close()
except Exception as e:
    print(f"An error occurred: {e}")
