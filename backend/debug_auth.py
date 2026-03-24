import sys
import os

# Fix path: Add ROOT directory (parent of backend/)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, User
from auth import verify_password, get_password_hash

def debug_auth():
    print("--- AUTH DEBUGGER ---")
    
    # Check DB Connection
    try:
        db = next(get_db())
        print(f"DB Connected. Engine: {db.bind.url}")
    except Exception as e:
        print(f"DB Connect Fail: {e}")
        return

    email = "kittu@krishasales.com"
    password = "password123"

    print(f"\nLooking for user: {email}")
    user = db.query(User).filter(User.email == email).first()

    if not user:
        print("[X] User NOT FOUND in DB.")
        print("Listing all users:")
        all_users = db.query(User).all()
        for u in all_users:
            print(f" - {u.email} (ID: {u.id})")
        return

    print(f"[OK] User Found: {user.username} (ID: {user.id})")
    print(f"Stored Hash: {user.hashed_password}")
    
    print(f"\nVerifying password: '{password}'")
    is_valid = verify_password(password, user.hashed_password)
    
    if is_valid:
        print("[OK] Password MATCHES!")
    else:
        print("[X] Password DOES NOT MATCH.")
        
        print("\nDiagnostic Check:")
        test_hash = get_password_hash(password)
        print(f"New Hash of '{password}': {test_hash}")
        print(f"Lengths: Stored={len(user.hashed_password)}, New={len(test_hash)}")
        
        if len(user.hashed_password) != 60:
             print("[!] Stored hash length looks wrong (Should be 60 for bcrypt)")

if __name__ == "__main__":
    debug_auth()

