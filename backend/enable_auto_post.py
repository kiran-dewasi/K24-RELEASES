"""
Enable Auto-Post to Tally for the default tenant.
"""
from sqlalchemy.orm import Session
from database import get_db, Tenant, engine
from database import Base # Ensure models are loaded

def enable_auto_post(tenant_id: str):
    from database import SessionLocal # Use direct session
    db = SessionLocal()
    try:
        # Find the tenant (assuming default or the one used in testing)
        
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            print(f"Tenant {tenant_id} not found. Creating it...")
            tenant = Tenant(id=tenant_id, name="Krisha Sales", auto_post_to_tally=True)
            db.add(tenant)
        else:
            print(f"Found tenant {tenant.id}. Updating auto_post_to_tally = True")
            tenant.auto_post_to_tally = True
            
        db.commit()
        print("âœ… Auto-Post Enabled successfully!")
        
    except Exception as e:
        print(f"âŒ Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    enable_auto_post("TENANT-12345")

