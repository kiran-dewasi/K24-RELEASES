import sqlite3
import json

db_path = 'k24_shadow.db'
conn = sqlite3.connect(db_path)
cols = [row[1] for row in conn.execute('PRAGMA table_info(vouchers)').fetchall()]
conn.close()

result = [
    f"is_deleted: {'is_deleted' in cols}",
    f"deleted_at: {'deleted_at' in cols}",
    f"deleted_source: {'deleted_source' in cols}",
    f"All voucher columns: {cols}"
]

with open('final_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(result))

print('\n'.join(result))
