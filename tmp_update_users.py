import sqlite3

conn = sqlite3.connect(r"C:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare\k24_shadow.db")
cur = conn.cursor()

print("=== BEFORE ===")
cur.execute("SELECT id, full_name, email, role, tenant_id FROM users")
results_before = cur.fetchall()
for row in results_before:
    print(row)

cur.execute("""
    UPDATE users 
    SET email = 'ai.krisha24@gmail.com'
    WHERE email = 'xhide3073@gmail.com'
""")
print(f"\nRows updated: {cur.rowcount}")

conn.commit()

print("\n=== AFTER ===")
cur.execute("SELECT id, full_name, email, role, tenant_id FROM users")
results_after = cur.fetchall()
for row in results_after:
    print(row)

print("\n=== DONE ===")
conn.close()
