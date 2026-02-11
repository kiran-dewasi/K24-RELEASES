import sqlite3
import os
import sys
import requests
from passlib.context import CryptContext

# Configuration
DB_PATH = os.path.join(os.getcwd(), "k24_shadow.db")
API_URL = "http://localhost:8001/api/auth/login"
TEST_EMAIL = "kittu@krishasales.com"
TEST_PASSWORD = "password123"

# Setup Passlib
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        return False

def check_db():
    print(f"Checking Database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("❌ Database file not found!")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check Users Table
        try:
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            if not columns:
                print("[X] 'users' table does not exist or is empty schema.")
            else:
                print("[OK] 'users' table exists.")
                print("Schema columns:", [col[1] for col in columns])
        except Exception as e:
            print(f"[X] Error checking schema: {e}")
            
        # Check Default User
        print(f"\nSearching for user: {TEST_EMAIL}")
        cursor.execute("SELECT id, username, email, hashed_password, role, is_active FROM users WHERE email = ?", (TEST_EMAIL,))
        user = cursor.fetchone()
        
        if user:
            print(f"[OK] User found: ID={user[0]}, Username={user[1]}, Email={user[2]}, Role={user[4]}, Active={user[5]}")
            hashed_pw = user[3]
            if hashed_pw:
                is_valid = verify_password(TEST_PASSWORD, hashed_pw)
                if is_valid:
                     print(f"[OK] Password verification (local simulation): SUCCESS for '{TEST_PASSWORD}'")
                else:
                     print(f"[X] Password verification (local simulation): FAILED for '{TEST_PASSWORD}'")
            else:
                print("[X] No password hash found for user.")
        else:
            print("[X] User not found in database.")
            
        conn.close()
    except Exception as e:
        print(f"[X] Database error: {e}")

def check_api():
    print(f"\nChecking API Endpoint: {API_URL}")
    try:
        payload = {"username": TEST_EMAIL, "password": TEST_PASSWORD} # OAuth2PasswordRequestForm usually expects 'username' field to carry the email if that's how it's set up, implies form-data.
        # However, backend/routers/auth.py 'login' takes `LoginRequest(BaseModel)` with JSON body {email, password}.
        # Let's check backend/routers/auth.py again.
        # line 113: def login(login_data: LoginRequest ...
        # line 108: class LoginRequest(BaseModel): email: str, password: str
        
        json_payload = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
        
        response = requests.post(API_URL, json=json_payload, timeout=2)
        
        if response.status_code == 200:
            print("[OK] API Login Success!")
            print("Response:", response.json())
        else:
            print(f"[X] API Login Failed. Status: {response.status_code}")
            print("Response:", response.text)
            
    except requests.exceptions.ConnectionError:
        print("[X] Could not connect to server (Connection Refused). Server likely not running.")
    except Exception as e:
        print(f"[X] API Check Error: {e}")

if __name__ == "__main__":
    check_db()
    check_api()
