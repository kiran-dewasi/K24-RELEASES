import sqlite3
import os

DB_PATH = "k24_shadow.db"

def run_migration():
    print(f"Migrating Stock Items in {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Expand ITEMS table
    columns_to_add = [
        ("description", "VARCHAR"),
        ("stock_group", "VARCHAR"),
        ("stock_category", "VARCHAR"),
        ("item_type", "VARCHAR DEFAULT 'goods'"),
        ("alternate_unit", "VARCHAR"),
        ("conversion_factor", "FLOAT"),
        ("minimum_stock", "FLOAT"),
        ("maximum_stock", "FLOAT"),
        ("reorder_quantity", "FLOAT"),
        ("mrp", "FLOAT"),
        ("valuation_method", "VARCHAR DEFAULT 'Average'"),
        ("taxability", "VARCHAR DEFAULT 'Taxable'"),
        ("cess_rate", "FLOAT DEFAULT 0.0"),
        ("is_godown_tracking", "BOOLEAN DEFAULT 0"),
        ("default_godown", "VARCHAR"),
        ("tally_guid", "VARCHAR"),
        ("created_from", "VARCHAR DEFAULT 'Manual'"),
        ("created_at", "DATETIME"),
        ("updated_at", "DATETIME"),
        ("is_active", "BOOLEAN DEFAULT 1")
    ]
    
    for col, dtype in columns_to_add:
        try:
            print(f"Adding column {col}...")
            cursor.execute(f"ALTER TABLE items ADD COLUMN {col} {dtype}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                print(f"Skipping {col}, already exists.")
            else:
                print(f"Error adding {col}: {e}")

    # Indexes for items
    indexes = [
        ("ix_items_stock_group", "items", "stock_group"),
        ("ix_items_hsn_code", "items", "hsn_code"),
        ("ix_items_tally_guid", "items", "tally_guid"),
    ]
    for idx_name, table, col in indexes:
        try:
             cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({col})")
             print(f"Created index {idx_name}")
        except Exception as e:
             print(f"Index error {idx_name}: {e}")

    # 2. Refactor InventoryEntries -> StockMovements
    # Check if stock_movements exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stock_movements'")
    if cursor.fetchone():
        print("stock_movements table already exists. Skipping recreation.")
    else:
        print("Creating stock_movements table...")
        cursor.execute("""
            CREATE TABLE stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                voucher_id INTEGER,
                movement_date DATETIME,
                movement_type VARCHAR,
                quantity FLOAT,
                rate FLOAT,
                amount FLOAT,
                godown_name VARCHAR,
                batch_name VARCHAR,
                narration VARCHAR,
                tenant_id VARCHAR NOT NULL DEFAULT 'default',
                FOREIGN KEY(item_id) REFERENCES items(id),
                FOREIGN KEY(voucher_id) REFERENCES vouchers(id)
            )
        """)
        
        # Migrate Data if inventory_entries exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inventory_entries'")
        if cursor.fetchone():
            print("Migrating data from inventory_entries...")
            try:
                # Check column structure of old table to be safe
                # Assuming standard: id, item_id, voucher_id, billed_qty, rate, amount, is_inward, godown_name, batch_name, tenant_id
                cursor.execute("""
                    INSERT INTO stock_movements (id, item_id, voucher_id, quantity, rate, amount, movement_type, godown_name, batch_name, tenant_id)
                    SELECT id, item_id, voucher_id, billed_qty, rate, amount, CASE WHEN is_inward THEN 'IN' ELSE 'OUT' END, godown_name, batch_name, tenant_id
                    FROM inventory_entries
                """)
                print("Data migrated. Renaming old table to backup.")
                cursor.execute("ALTER TABLE inventory_entries RENAME TO inventory_entries_backup")
            except Exception as e:
                print(f"Data migration failed: {e}")

        # Indexes for stock_movements
        mv_indexes = [
            ("ix_stock_movements_item_id", "stock_movements", "item_id"),
            ("ix_stock_movements_voucher_id", "stock_movements", "voucher_id"),
            ("ix_stock_movements_movement_date", "stock_movements", "movement_date"),
        ]
        for idx_name, table, col in mv_indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({col})")
            except: pass

    conn.commit()
    conn.close()
    print("Stock Items Migration complete.")

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        run_migration()
    else:
        print(f"Database {DB_PATH} not found.")
