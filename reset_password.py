import sqlite3
import os
import sys

# Ensure backend can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.auth import get_password_hash

def reset_password():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'k24_shadow.db')
    print(f"Connecting to: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    email = "kittu@krishasales.com"
    plain_password = "password123"
    
    # Hash using the APP'S logic
    hashed = get_password_hash(plain_password)
    print(f"Generated Hash: {hashed}")

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        print(f"Resetting password for {email}...")
        cursor.execute("UPDATE users SET hashed_password = ? WHERE email = ?", (hashed, email))
    else:
        print(f"User {email} not found. Creating...")
        cursor.execute("""
            INSERT INTO users (email, full_name, hashed_password, role, tenant_id, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (email, "Kittu", hashed, "admin", "12345", 1))

    conn.commit()
    conn.close()
    print("[OK] Password reset successfully.")

if __name__ == "__main__":
    reset_password()
