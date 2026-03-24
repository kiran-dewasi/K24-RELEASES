from sqlalchemy.orm import Session
from database import SessionLocal, User

def update_user_whatsapp():
    db = SessionLocal()
    try:
        username = "kittu"
        # We will set regular format and ensure it matches what Baileys sends (usually CC + Number)
        # User gave 7339906200. Assuming IN (+91).
        target_number = "917339906200" 
        
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"âŒ User '{username}' not found.")
            return

        print(f"Found User: {user.username} (Current WA: {user.whatsapp_number})")
        
        # Update
        user.whatsapp_number = target_number
        user.is_whatsapp_verified = True
        
        db.commit()
        print(f"âœ… Updated User '{username}' with WhatsApp Number: {target_number}")
        print("You can now send messages from this number and be recognized as Admin.")

    except Exception as e:
        print(f"âŒ Error updating user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_user_whatsapp()

