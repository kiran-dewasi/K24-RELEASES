from sqlalchemy.orm import Session
from database import SessionLocal, User, Company, UserSettings, Tenant, Ledger, WhatsAppMapping, init_db
from auth import get_password_hash
from datetime import datetime
import uuid

def create_default_user():
    init_db() # Ensure tables exist
    db = SessionLocal()
    try:
        # 1. Check if user exists
        username = "kittu"
        if db.query(User).filter(User.username == username).first():
            print(f"User '{username}' already exists.")
            return

        # 2. Create Company/Tenant (if not exists)
        company_name = "Krishna Sales"
        tally_name = "Krishna Sales" # Adjust if needed
        
        # Check existing company
        company = db.query(Company).filter(Company.name == company_name).first()
        if not company:
            company = Company(
                name=company_name,
                tally_company_name=tally_name,
                gstin="27ABCDE1234F1Z5", # DUMMY GST
                city="Pune",
                state="Maharashtra"
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            print(f"âœ“ Created Company: {company_name}")

        # 3. Create Tenant Record (for Multi-tenancy)
        tenant_id = "TENANT-12345"
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            tenant = Tenant(
                id=tenant_id,
                company_name=company_name,
                tally_company_name=tally_name,
                whatsapp_number="+919999999999" # Placeholder
            )
            db.add(tenant)
            db.commit()
            print(f"[SUCCESS] Created Tenant: {tenant_id}")

        # 4. Create User
        password = "password123"
        hashed_pw = get_password_hash(password)
        
        user = User(
            email="kittu@krishasales.com",
            username=username,
            hashed_password=hashed_pw,
            full_name="Kittu",
            role="admin",
            company_id=company.id,
            tenant_id=tenant_id, # Link to tenant
            is_verified=True,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # 5. Create Settings
        settings = UserSettings(user_id=user.id, tenant_id=tenant_id)
        db.add(settings)
        db.commit()

        print("\n [SUCCESS] Default User Created Successfully!")
        print(f"Username: {username}")
        print(f"Password: {password}")
        print(f"Tenant ID: {tenant_id}")

    except Exception as e:
        print(f"[ERROR] Error creating default user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_default_user()

