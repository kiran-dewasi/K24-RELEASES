import sqlite3
import os

db_path = r"c:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare\k24_shadow.db"

def check():
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Check users
    print("--- USERS ---")
    cur.execute("SELECT id, username, email, role, tenant_id FROM users")
    for row in cur.fetchall():
        print(row)
    
    # Check tenants
    print("\n--- TENANTS ---")
    cur.execute("SELECT id, name FROM tenants")
    for row in cur.fetchall():
        print(row)
        
    conn.close()

if __name__ == "__main__":
    check()
