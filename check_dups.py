import sqlite3

conn = sqlite3.connect("k24_shadow.db")
cur = conn.cursor()
cur.execute("SELECT id, voucher_number, date, amount, narration, guid FROM vouchers WHERE voucher_number IN ('102','103','104') ORDER BY voucher_number, id")
rows = cur.fetchall()
for r in rows:
    print(r)
conn.close()
