"""
Verify deduplication worked - check a known duplicate set.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from database import SessionLocal, Voucher
from datetime import datetime

db = SessionLocal()

# Check voucher 25, Purchase, 2026-03-15 (had 53 duplicates)
rows = db.query(Voucher).filter(
    Voucher.tenant_id == "TENANT-12345",
    Voucher.voucher_number == "25",
    Voucher.voucher_type == "Purchase",
    Voucher.date == datetime(2026, 3, 15)
).all()

print(f"Voucher 25 (Purchase, 2026-03-15) - Rows remaining: {len(rows)}")
if rows:
    for row in rows:
        print(f"  ID: {row.id}, has_inventory: {bool(row.inventory_entries)}, has_ledger: {bool(row.ledger_entries)}, last_synced: {row.last_synced}")

# Check voucher 102, Receipt, 2026-02-27 (had 2 duplicates)
rows2 = db.query(Voucher).filter(
    Voucher.tenant_id == "TENANT-12345",
    Voucher.voucher_number == "102",
    Voucher.voucher_type == "Receipt",
    Voucher.date == datetime(2026, 2, 27)
).all()

print(f"\nVoucher 102 (Receipt, 2026-02-27) - Rows remaining: {len(rows2)}")
if rows2:
    for row in rows2:
        print(f"  ID: {row.id}, has_inventory: {bool(row.inventory_entries)}, has_ledger: {bool(row.ledger_entries)}, last_synced: {row.last_synced}")

db.close()

