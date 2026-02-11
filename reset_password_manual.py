from sqlalchemy.orm import Session
from backend.database import SessionLocal, User
from backend.auth import get_password_hash

def reset_password(email, new_password):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User {email} not found!")
            return
        
        print(f"Found user: {user.username} (ID: {user.id})")
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        print(f"✅ Password reset to '{new_password}' successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    db = SessionLocal()
    users = db.query(User).all()
    print("Existing Users:")
    for u in users:
        print(f" - {u.email} ({u.username})")
    db.close()
    
    email = "kirankdewasi19@gmail.com"
    reset_password(email, "password")
