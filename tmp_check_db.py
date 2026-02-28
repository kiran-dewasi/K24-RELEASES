import sqlite3
db = sqlite3.connect(r'C:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare\k24_shadow.db')
cur = db.cursor()

print("=== ALL LEDGERS WITH BALANCES (non-zero) ===")
cur.execute("""
    SELECT name, parent, closing_balance, tenant_id
    FROM ledgers
    WHERE closing_balance != 0
    ORDER BY parent, closing_balance DESC
""")
rows = cur.fetchall()
for r in rows:
    print(f"  {str(r[0])[:35]:35s} | {str(r[1])[:30]:30s} | bal={r[2] or 0:>15,.2f}")

print()
print("=== SUMMARY BY PARENT GROUP ===")
cur.execute("""
    SELECT parent, COUNT(*) as cnt, SUM(closing_balance) as total, SUM(ABS(closing_balance)) as abs_total
    FROM ledgers
    WHERE closing_balance != 0
    GROUP BY parent
    ORDER BY ABS(SUM(closing_balance)) DESC
""")
for r in cur.fetchall():
    print(f"  {str(r[0])[:35]:35s} | count={r[1]} | sum={r[2] or 0:>15,.2f} | abs_sum={r[3] or 0:>15,.2f}")

db.close()
