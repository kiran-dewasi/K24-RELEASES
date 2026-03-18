from backend.database import SessionLocal, Voucher
from datetime import datetime
import os
import sys

# Ensure backend is in path if needed
sys.path.append(os.getcwd())

db = SessionLocal()

try:
    # Check 1: Are March 15 vouchers soft-deleted after sync?
    march15 = db.query(Voucher).filter(
        Voucher.date >= datetime(2026, 3, 15),
        Voucher.date < datetime(2026, 3, 16)
    ).all()
    print(f"March 15 total: {len(march15)}")
    for v in march15:
        print(f"  Vch#{v.voucher_number} | is_deleted={v.is_deleted} | guid={v.guid}")
finally:
    db.close()
