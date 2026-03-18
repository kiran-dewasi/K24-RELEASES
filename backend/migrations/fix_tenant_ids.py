"""
One-time migration: re-assigns all 'default' tenant_id records
to the real tenant_id from the active User.
Run once from project root: python -m backend.migrations.fix_tenant_ids
"""
from backend.database import SessionLocal, Ledger, Voucher, User

def run():
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.is_active == True,
            User.tenant_id != None,
            User.tenant_id != "default",
            User.tenant_id != "offline-default"
        ).order_by(User.last_login.desc()).first()

        if not user:
            print("[ERROR] No active user with valid tenant_id found. Login first.")
            return

        real_tenant = user.tenant_id
        print(f"[OK] Real tenant_id: {real_tenant}")

        # Fix Ledgers
        ledger_count = db.query(Ledger).filter(
            Ledger.tenant_id == "default"
        ).update({"tenant_id": real_tenant})
        print(f"[OK] Fixed {ledger_count} ledgers")

        # Fix Vouchers
        voucher_count = db.query(Voucher).filter(
            Voucher.tenant_id == "default"
        ).update({"tenant_id": real_tenant})
        print(f"[OK] Fixed {voucher_count} vouchers")

        # Fix NULL is_active on ledgers
        from sqlalchemy import update
        db.execute(
            update(Ledger)
            .where(Ledger.is_active == None)
            .values(is_active=True)
        )
        print("[OK] Fixed NULL is_active on ledgers")

        db.commit()
        print("[OK] Migration complete.")
    finally:
        db.close()

if __name__ == "__main__":
    run()
