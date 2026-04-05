import sqlite3

db_path = 'k24_shadow.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in c.fetchall()]

for table in tables:
    try:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"Table {table} rows: {c.fetchone()[0]}")
        
        c.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in c.fetchall()]
        
        if 'tenant_id' in columns:
            c.execute(f"SELECT tenant_id, COUNT(*) FROM {table} GROUP BY tenant_id")
            for t_id, cnt in c.fetchall():
                print(f"  [{t_id}]: {cnt}")
        else:
            print("  (no tenant_id column)")
    except Exception as e:
        print(f"Error on table {table}: {e}")
