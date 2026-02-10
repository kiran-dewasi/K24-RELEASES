"""
Enable Auto-Post to Tally for the default tenant.
"""
from sqlalchemy.orm import Session
from backend.database import get_db, Tenant, engine
from backend.database import Base # Ensure models are loaded

def enable_auto_post():
    from backend.database import SessionLocal # Use direct session
    db = SessionLocal()
    try:
        # Find the tenant (assuming default or the one used in testing)
        tenant_id = "TENANT-12345" # The forced override ID in baileys.py
        
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            print(f"Tenant {tenant_id} not found. Creating it...")
            tenant = Tenant(id=tenant_id, name="Krisha Sales", auto_post_to_tally=True)
            db.add(tenant)
        else:
            print(f"Found tenant {tenant.id}. Updating auto_post_to_tally = True")
            tenant.auto_post_to_tally = True
            
        db.commit()
        print("✅ Auto-Post Enabled successfully!")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    enable_auto_post()
