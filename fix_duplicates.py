"""
One-time script: removes duplicate vouchers from k24_shadow.db
Keeps the lowest-ID row per (voucher_number, voucher_type, DATE(date))
"""
import sqlite3

DB_PATH = "k24_shadow.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM vouchers")
before = cur.fetchone()[0]
print(f"BEFORE: {before} total vouchers")

cur.execute("SELECT voucher_number, voucher_type, DATE(date), COUNT(*) FROM vouchers GROUP BY voucher_number, voucher_type, DATE(date) HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC LIMIT 10")
rows = cur.fetchall()
print("Top duplicates BEFORE:")
for r in rows:
    print(f"  #{r[0]} ({r[1]}) on {r[2]}: {r[3]} copies")

# Delete keeping only MIN(id) per group
cur.execute("""
    DELETE FROM vouchers
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM vouchers
        GROUP BY voucher_number, voucher_type, DATE(date)
    )
""")
deleted = cur.rowcount
conn.commit()

cur.execute("SELECT COUNT(*) FROM vouchers")
after = cur.fetchone()[0]
print(f"\nDeleted {deleted} duplicate rows.")
print(f"AFTER: {after} vouchers remaining.")

cur.execute("SELECT voucher_number, COUNT(*) FROM vouchers WHERE voucher_number IN ('102','103','104') GROUP BY voucher_number")
print("Spot check:")
for r in cur.fetchall():
    print(f"  #{r[0]}: {r[1]} copy")

conn.close()
print("Done!")
