from backend.database import SessionLocal, Voucher
from datetime import datetime
db = SessionLocal()

# Check March 15 vouchers — are they soft-deleted now?
march15 = db.query(Voucher).filter(
    Voucher.date >= datetime(2026, 3, 15),
    Voucher.date < datetime(2026, 3, 16)
).all()

print(f"March 15 vouchers total: {len(march15)}")
for v in march15:
    print(f"  Vch#{v.voucher_number} | {v.voucher_type} | is_deleted={v.is_deleted} | deleted_source={v.deleted_source}")

# Also check all March
march_all = db.query(Voucher).filter(
    Voucher.date >= datetime(2026, 3, 1),
    Voucher.is_deleted == False
).all()
print(f"\nActive March vouchers: {len(march_all)}")
for v in march_all:
    print(f"  Vch#{v.voucher_number} | {v.date.date()} | {v.voucher_type}")

db.close()
