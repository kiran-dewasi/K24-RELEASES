from backend.database import engine, Base
from sqlalchemy import text
from sqlalchemy.schema import CreateTable
from backend.database import InventoryEntry

def migrate_inventory():
    print("🚀 Starting Inventory Migration...")
    
    with engine.connect() as conn:
        # 1. Update 'items' table columns
        alter_cmds = [
            "ALTER TABLE items ADD COLUMN alias VARCHAR NULL",
            "ALTER TABLE items ADD COLUMN part_number VARCHAR NULL",
            "ALTER TABLE items ADD COLUMN opening_stock FLOAT DEFAULT 0.0",
            "ALTER TABLE items ADD COLUMN cost_price FLOAT DEFAULT 0.0",
            "ALTER TABLE items ADD COLUMN selling_price FLOAT DEFAULT 0.0",
            "ALTER TABLE items ADD COLUMN gst_rate FLOAT DEFAULT 0.0",
            "ALTER TABLE items ADD COLUMN hsn_code VARCHAR NULL",
        ]
        
        for cmd in alter_cmds:
            try:
                conn.execute(text(cmd))
                print(f"✅ Executed: {cmd}")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"ℹ️ Column already exists: {cmd.split('ADD COLUMN')[1].split()[0]}")
                else:
                    print(f"⚠️ Failed: {cmd} -> {e}")

        # 2. Create 'inventory_entries' table
        try:
             # Check if table exists
             conn.execute(text("SELECT 1 FROM inventory_entries LIMIT 1"))
             print("ℹ️ 'inventory_entries' table already exists.")
        except:
             print("🔄 Creating 'inventory_entries' table...")
             # Use SQLAlchemy to generate CREATE TABLE statement
             # But since we are connected via engine, we can just use metadata.create_all for specific tables if bound
             # Or raw SQL. Let's use metadata.create_all with check.
             pass
             
    # Use standard create_all which is idempotent for table creation (skips if exists)
    try:
        target_tables = [InventoryEntry.__table__]
        Base.metadata.create_all(bind=engine, tables=target_tables)
        print("✅ 'inventory_entries' table verified/created.")
    except Exception as e:
        print(f"❌ Failed to create table: {e}")

    print("🏁 Inventory Migration Completed.")

if __name__ == "__main__":
    migrate_inventory()
