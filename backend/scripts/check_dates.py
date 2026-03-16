"""
Check actual date values for voucher 25.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.database import SessionLocal, Voucher

db = SessionLocal()

# Check all voucher 25 rows
rows = db.query(Voucher).filter(
    Voucher.tenant_id == "TENANT-12345",
    Voucher.voucher_number == "25",
    Voucher.voucher_type == "Purchase"
).all()

print(f"All voucher 25 rows: {len(rows)}")
for row in rows:
    print(f"  ID: {row.id}, date: {row.date}, date_type: {type(row.date)}")

db.close()
