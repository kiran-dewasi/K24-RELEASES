import sys; sys.path.insert(0, '.')
from database import SessionLocal, Voucher
from sqlalchemy import text
from datetime import datetime, date

db = SessionLocal()

# Simulate _default_fy_dates
now = datetime.now()
fy_start_year = now.year if now.month >= 4 else now.year - 1
d_from = date(fy_start_year, 4, 1)
d_to = date(fy_start_year + 1, 3, 31)

print(f"Simulating FY query: {d_from} to {d_to}")

q = db.query(Voucher)
q = q.filter(Voucher.date >= datetime.combine(d_from, datetime.min.time()))
q = q.filter(Voucher.date <= datetime.combine(d_to, datetime.max.time()))

results = q.all()
print(f"Total vouchers found in FY range: {len(results)}")

# Group by tenant
from collections import defaultdict
by_tenant = defaultdict(int)
for v in results:
    by_tenant[v.tenant_id] += 1

print("By Tenant:")
for tid, count in by_tenant.items():
    print(f"  {tid}: {count}")

# Check Feb range specifically (as seen in screenshot)
feb_start = date(2026, 2, 1)
feb_end = date(2026, 2, 28)
q2 = db.query(Voucher).filter(Voucher.date >= datetime.combine(feb_start, datetime.min.time()))
q2 = q2.filter(Voucher.date <= datetime.combine(feb_end, datetime.max.time()))
results_feb = q2.all()
print(f"\nTotal vouchers in FEB 2026: {len(results_feb)}")

db.close()

