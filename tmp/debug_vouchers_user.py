from backend.database import SessionLocal, Voucher
db = SessionLocal()

# Check: what does _build_voucher_filters actually return for Sales?
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.types import Date

# Simulate exactly what get_sales_register does
from backend.routers.reports import _build_voucher_filters

q = _build_voucher_filters(
    db.query(Voucher),
    "20250401",
    "20260331", 
    ["Sales", "Credit Note"],
    None,
    "TENANT-12345"
)
results = q.all()
print(f"Total returned by _build_voucher_filters: {len(results)}")

march_results = [v for v in results if v.date and v.date.month == 3 and v.date.year == 2026]
print(f"March 2026 in results: {len(march_results)}")
for v in march_results:
    print(f"  Vch#{v.voucher_number} | is_deleted={v.is_deleted} | date={v.date.date()}")

db.close()
