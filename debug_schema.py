
import sqlite3

def check_schema():
    conn = sqlite3.connect('k24_shadow.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='tenants'")
        result = cursor.fetchone()
        if result:
            print("Schema for tenants table:")
            print(result[0])
        else:
            print("Table 'tenants' does not exist.")
            
        print("\nColumns in users table:")
        cursor.execute("PRAGMA table_info(users)")
        for col in cursor.fetchall():
            print(col)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_schema()
