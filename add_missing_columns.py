import sqlite3
conn = sqlite3.connect('k24_shadow.db')
cursor = conn.cursor()

# Add missing columns one by one (ALTER TABLE is safe — ignores if column exists via try/except)
columns_to_add = [
    "ALTER TABLE vouchers ADD COLUMN is_deleted BOOLEAN DEFAULT 0",
    "ALTER TABLE vouchers ADD COLUMN deleted_at DATETIME",
    "ALTER TABLE vouchers ADD COLUMN deleted_source VARCHAR",
]

for sql in columns_to_add:
    try:
        cursor.execute(sql)
        print(f"[OK] Done: {sql}")
    except Exception as e:
        print(f"[SKIP] Skipped: {e}")

conn.commit()

# Verify
cols = [row[1] for row in cursor.execute('PRAGMA table_info(vouchers)').fetchall()]
print('is_deleted:', 'is_deleted' in cols)
print('deleted_at:', 'deleted_at' in cols)
print('deleted_source:', 'deleted_source' in cols)
conn.close()
