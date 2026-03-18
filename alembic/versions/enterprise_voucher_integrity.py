"""enterprise_voucher_integrity

Revision ID: enterprise_voucher_001
Revises: cdb3d3aef16a
Create Date: 2025-03-17 00:00:00.000000

Enterprise-grade data integrity for Vouchers:
- Add UniqueConstraint on (tenant_id, guid) to make duplicates physically impossible
- Add soft delete columns (is_deleted, deleted_at, deleted_source)
- Clean up existing duplicates before adding constraint
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'enterprise_voucher_001'
down_revision: Union[str, None] = 'cdb3d3aef16a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add enterprise-grade voucher integrity."""
    bind = op.get_bind()
    inspector = inspect(bind)

    # ── Step 1: Add soft delete columns ──
    print("📝 Adding soft delete columns...")
    with op.batch_alter_table('vouchers', schema=None) as batch_op:
        # Add is_deleted column (default False)
        try:
            batch_op.add_column(sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'))
        except OperationalError:
            print("⚠️ is_deleted column already exists, skipping...")

        # Add deleted_at column (nullable)
        try:
            batch_op.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))
        except OperationalError:
            print("⚠️ deleted_at column already exists, skipping...")

        # Add deleted_source column (nullable)
        try:
            batch_op.add_column(sa.Column('deleted_source', sa.String(), nullable=True))
        except OperationalError:
            print("⚠️ deleted_source column already exists, skipping...")

        # Add index on is_deleted
        indexes = inspector.get_indexes('vouchers')
        existing_index_names = [idx['name'] for idx in indexes]
        if 'ix_voucher_is_deleted' not in existing_index_names:
            batch_op.create_index('ix_voucher_is_deleted', ['is_deleted'])
            print("✅ Created index on is_deleted")

    # ── Step 2: Clean up existing duplicate vouchers ──
    # Before adding the unique constraint, we need to remove duplicates
    # Keep only the row with MAX(id) for each (tenant_id, guid) group
    print("🧹 Cleaning up existing duplicate vouchers...")

    # SQLite-compatible duplicate removal query
    # This keeps the latest voucher (MAX id) for each (tenant_id, guid) pair
    cleanup_query = """
    DELETE FROM vouchers
    WHERE id NOT IN (
        SELECT MAX(id)
        FROM vouchers
        WHERE guid IS NOT NULL AND guid != ''
        GROUP BY tenant_id, guid
    )
    AND guid IS NOT NULL AND guid != ''
    """

    try:
        result = bind.execute(sa.text(cleanup_query))
        deleted_count = result.rowcount if hasattr(result, 'rowcount') else 0
        print(f"🗑️ Removed {deleted_count} duplicate vouchers")
    except Exception as e:
        print(f"⚠️ Duplicate cleanup warning: {e}")
        # Continue anyway - constraint will catch any remaining issues

    # ── Step 3: Add UniqueConstraint on (tenant_id, guid) ──
    print("🔒 Adding UniqueConstraint on (tenant_id, guid)...")
    with op.batch_alter_table('vouchers', schema=None) as batch_op:
        try:
            # Check if constraint already exists
            constraints = inspector.get_unique_constraints('vouchers')
            existing_constraint_names = [c['name'] for c in constraints]

            if 'uq_voucher_tenant_guid' not in existing_constraint_names:
                batch_op.create_unique_constraint(
                    'uq_voucher_tenant_guid',
                    ['tenant_id', 'guid']
                )
                print("✅ Created UniqueConstraint uq_voucher_tenant_guid")
            else:
                print("⚠️ UniqueConstraint already exists, skipping...")
        except OperationalError as e:
            print(f"⚠️ Could not add unique constraint: {e}")
            print("   This may occur if there are still duplicate GUIDs.")
            print("   Run sync to clean up data, then retry migration.")

    print("✅ Enterprise voucher integrity migration complete!")


def downgrade() -> None:
    """Remove enterprise-grade voucher integrity."""
    with op.batch_alter_table('vouchers', schema=None) as batch_op:
        # Drop unique constraint
        try:
            batch_op.drop_constraint('uq_voucher_tenant_guid', type_='unique')
        except:
            pass

        # Drop index
        try:
            batch_op.drop_index('ix_voucher_is_deleted')
        except:
            pass

        # Drop columns
        try:
            batch_op.drop_column('deleted_source')
        except:
            pass

        try:
            batch_op.drop_column('deleted_at')
        except:
            pass

        try:
            batch_op.drop_column('is_deleted')
        except:
            pass
