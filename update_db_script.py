import sqlite3
import os

db_path = r"C:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare\k24_shadow.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 1. Fix Narayan's tenant + role
cur.execute("""
    UPDATE users 
    SET tenant_id = 'TENANT-2965af26', role = 'owner'
    WHERE email = 'xhide3073@gmail.com'
""")
print("Narayan updated:", cur.rowcount)

# 2. Fix Kiran's tenant + role
cur.execute("""
    UPDATE users 
    SET tenant_id = 'TENANT-2965af26', role = 'owner'
    WHERE email = 'kirankdewasi19@gmail.com'
""")
print("Kiran updated:", cur.rowcount)

# 3. Rest → viewer
cur.execute("""
    UPDATE users 
    SET role = 'viewer'
    WHERE email NOT IN ('xhide3073@gmail.com', 'kirankdewasi19@gmail.com')
""")
print("Others set to viewer:", cur.rowcount)

# 4. Insert real tenant_config row
cur.execute("""
    INSERT OR REPLACE INTO tenant_config 
    (tenant_id, whatsapp_number, is_whatsapp_active)
    VALUES ('TENANT-2965af26', '917339906200', 1)
""")
print("tenant_config row inserted:", cur.rowcount)

conn.commit()

# Verify
print("\n=== USERS AFTER ===")
cur.execute("SELECT id, full_name, email, role, tenant_id FROM users")
for row in cur.fetchall():
    print(row)

print("\n=== TENANT_CONFIG AFTER ===")
cur.execute("SELECT * FROM tenant_config")
for row in cur.fetchall():
    print(row)

conn.close()
