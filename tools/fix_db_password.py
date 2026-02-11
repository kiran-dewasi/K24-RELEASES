from passlib.context import CryptContext
import sqlite3
import os

DB_PATH = os.path.join(os.getcwd(), "k24_shadow.db")
print(f"Updating DB at: {DB_PATH}")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
new_hash = pwd_context.hash("password123")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("UPDATE users SET hashed_password = ? WHERE email = ?", 
               (new_hash, "kittu@krishasales.com"))
if cursor.rowcount > 0:
    print(f"[OK] Password updated for kittu@krishasales.com")
else:
    print(f"[X] User kittu@krishasales.com not found")

conn.commit()
conn.close()
