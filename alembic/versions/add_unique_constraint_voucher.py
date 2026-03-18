"""add unique constraint on voucher number type party

Revision ID: add_vch_unique_001
Revises: 194033013b04, enterprise_voucher_001
Create Date: 2026-03-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError


# revision identifiers, used by Alembic.
revision: str = 'add_vch_unique_001'
down_revision = ('194033013b04', 'enterprise_voucher_001')
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Step 1: Deduplicate existing rows (keep MIN id per combo)
    print("🧹 Deduplicating vouchers by (tenant_id, voucher_number, voucher_type, party_name)...")
    try:
        result = bind.execute(sa.text("""
            DELETE FROM vouchers
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM vouchers
                GROUP BY tenant_id, voucher_number, voucher_type, party_name
            )
        """))
        deleted = result.rowcount if hasattr(result, 'rowcount') else 0
        print(f"✅ Removed {deleted} duplicate voucher rows")
    except Exception as e:
        print(f"⚠️ Dedup warning: {e}")

    # Step 2: Add unique constraint via batch_alter_table (SQLite-safe)
    inspector = inspect(bind)
    existing_constraints = [c['name'] for c in inspector.get_unique_constraints('vouchers')]

    if 'uq_voucher_num_type_party' not in existing_constraints:
        print("🔒 Adding unique constraint uq_voucher_num_type_party...")
        try:
            with op.batch_alter_table('vouchers', schema=None) as batch_op:
                batch_op.create_unique_constraint(
                    'uq_voucher_num_type_party',
                    ['tenant_id', 'voucher_number', 'voucher_type', 'party_name']
                )
            print("✅ Unique constraint added successfully")
        except (OperationalError, Exception) as e:
            print(f"⚠️ Could not add unique constraint: {e}")
    else:
        print("⚠️ Constraint uq_voucher_num_type_party already exists, skipping")


def downgrade() -> None:
    with op.batch_alter_table('vouchers', schema=None) as batch_op:
        try:
            batch_op.drop_constraint('uq_voucher_num_type_party', type_='unique')
        except Exception:
            pass
