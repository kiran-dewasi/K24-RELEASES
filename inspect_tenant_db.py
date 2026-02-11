import sqlite3

def inspect_db():
    try:
        conn = sqlite3.connect("k24_shadow.db")
        cursor = conn.cursor()
        
        print("--- Table Info: users ---")
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        for col in columns:
            print(col)
            
        print("\n--- Users Data (Limit 1) ---")
        try:
            cursor.execute("SELECT id, email, username FROM users LIMIT 1")
            row = cursor.fetchone()
            print(row)
        except Exception as e:
            print(f"Error fetching users: {e}")

        print("\n--- Tenant Tables ---")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%tenant%'")
        tables = cursor.fetchall()
        for table in tables:
            print(table)
            
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    inspect_db()
