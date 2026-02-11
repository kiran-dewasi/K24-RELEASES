import sqlite3
import os

DB_PATH = "k24_shadow.db"

def run_migration():
    print(f"Migrating {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    columns_to_add = [
        ("alias", "VARCHAR"),
        ("ledger_type", "VARCHAR"),
        ("balance_type", "VARCHAR"),
        ("city", "VARCHAR"),
        ("state", "VARCHAR"),
        ("pincode", "VARCHAR"),
        ("country", "VARCHAR DEFAULT 'India'"),
        ("contact_person", "VARCHAR"),
        ("pan", "VARCHAR"),
        ("gst_registration_type", "VARCHAR"),
        ("is_gst_applicable", "BOOLEAN DEFAULT 0"),
        ("credit_limit", "FLOAT"),
        ("credit_days", "INTEGER"),
        ("tally_guid", "VARCHAR"),
        ("created_from", "VARCHAR DEFAULT 'Manual'")
    ]
    
    for col, dtype in columns_to_add:
        try:
            print(f"Adding column {col}...")
            cursor.execute(f"ALTER TABLE ledgers ADD COLUMN {col} {dtype}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                print(f"Skipping {col}, already exists.")
            else:
                print(f"Error adding {col}: {e}")
                
    # Indexes
    indexes = [
        ("ix_ledgers_ledger_type", "ledgers", "ledger_type"),
        ("ix_ledgers_tally_guid", "ledgers", "tally_guid"),
        ("ix_ledgers_gstin", "ledgers", "gstin"),
    ]
    
    for idx_name, table, col in indexes:
        try:
             cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({col})")
             print(f"Created index {idx_name}")
        except Exception as e:
             print(f"Index error {idx_name}: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        run_migration()
    else:
        print(f"Database {DB_PATH} not found.")
