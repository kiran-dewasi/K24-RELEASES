import sqlite3
import os

db_path = r'c:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare\k24_shadow.db'
if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cols = [row[1] for row in conn.execute('PRAGMA table_info(vouchers)').fetchall()]
    print('is_deleted:', 'is_deleted' in cols)
    print('deleted_at:', 'deleted_at' in cols)
    print('deleted_source:', 'deleted_source' in cols)
    print('All voucher columns:', cols)
    conn.close()
