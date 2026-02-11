import sys
import os

# Ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal, Company, User

def verify_encryption():
    print("Verifying Encryption Access...")
    db = SessionLocal()
    
    # 1. Check Company
    company = db.query(Company).first()
    if company:
        print(f"Prop: Company ID: {company.id}")
        print(f"Prop: Phone: {company.phone}") # Should auto-decrypt
        print(f"Prop: GSTIN: {company.gstin}") # Should auto-decrypt
        print(f"Raw: _phone: {company._phone}") # Should be encrypted token
    else:
        print("No company found.")

    # 2. Check User
    user = db.query(User).first()
    if user:
        print(f"Prop: User ID: {user.id}")
        print(f"Prop: WhatsApp: {user.whatsapp_number}") # Should auto-decrypt
        print(f"Raw: _whatsapp: {user._whatsapp_number}") # Should be encrypted token
    else:
        print("No user found.")
        
    db.close()

if __name__ == "__main__":
    verify_encryption()
