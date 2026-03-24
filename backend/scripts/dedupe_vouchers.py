"""
One-time script to deduplicate existing voucher rows in local DB.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from database import SessionLocal, Voucher, get_db_path
from sqlalchemy import func
from datetime import datetime

def dedupe_vouchers():
    db = SessionLocal()

    try:
        print(f"Using DB: {get_db_path()}\n")

        # Get all vouchers
        all_vouchers = db.query(Voucher).all()

        # Group by logical key
        groups = {}
        for v in all_vouchers:
            # Use date string for consistent grouping
            date_str = v.date.strftime('%Y-%m-%d') if v.date else 'null'
            key = (v.tenant_id, v.voucher_number, v.voucher_type, date_str)
            if key not in groups:
                groups[key] = []
            groups[key].append(v)

        # Find duplicates
        duplicate_groups = {k: v for k, v in groups.items() if len(v) > 1}

        print(f"Total duplicate groups found: {len(duplicate_groups)}\n")

        if len(duplicate_groups) == 0:
            print("No duplicates found!")
            return

        # Show examples
        print("Sample duplicate groups (first 5):")
        for i, (key, rows) in enumerate(list(duplicate_groups.items())[:5]):
            tenant_id, voucher_num, voucher_type, date_str = key
            print(f"  {i+1}. tenant={tenant_id}, voucher={voucher_num}, type={voucher_type}, date={date_str}, count={len(rows)}")
        print()

        total_deleted = 0

        # Process each duplicate group
        for key, rows in duplicate_groups.items():
            # Priority 1: Prefer rows with non-empty inventory_entries or ledger_entries
            rows_with_data = [r for r in rows if (r.inventory_entries and len(r.inventory_entries) > 0) or (r.ledger_entries and len(r.ledger_entries) > 0)]

            if rows_with_data:
                candidates = rows_with_data
            else:
                candidates = rows

            # Priority 2: Keep most recently synced/updated
            candidates.sort(key=lambda x: x.last_synced or datetime.min, reverse=True)

            # Keep first, delete rest
            keep = candidates[0]
            to_delete = [r for r in rows if r.id != keep.id]

            for row in to_delete:
                db.delete(row)
                total_deleted += 1

        db.commit()
        print(f"Total rows deleted: {total_deleted}\n")
        print("DEDUPE_DONE")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print("DEDUPE_FAILED")
    finally:
        db.close()

if __name__ == "__main__":
    dedupe_vouchers()

