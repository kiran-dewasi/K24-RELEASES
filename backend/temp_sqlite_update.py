import sqlite3

conn = sqlite3.connect(r"C:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare\k24_shadow.db")
cur = conn.cursor()
cur.execute("UPDATE users SET role = 'owner' WHERE full_name = 'NARAYAN'")
conn.commit()

with open("backend/sqlite_out_utf8.txt", "w", encoding="utf-8") as f:
    f.write(f"ROWS UPDATED: {cur.rowcount}\n")
    cur.execute("SELECT id, full_name, role, tenant_id FROM users")
    f.write(f"CURRENT USERS: {cur.fetchall()}\n")

conn.close()
