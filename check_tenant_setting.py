"""
Check tenant settings using backend models.
"""
from backend.database import get_db, Tenant, SessionLocal

def check_setting():
    db = SessionLocal() # Direct session
    try:
        tenant_id = "TENANT-12345"
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        
        print(f"Checking Tenant: {tenant_id}")
        if tenant:
            print(f"Found Tenant: {tenant.tally_company_name}")
            if hasattr(tenant, 'auto_post_to_tally'):
                 print(f"auto_post_to_tally: {tenant.auto_post_to_tally}")
            else:
                 print("Attribute 'auto_post_to_tally' NOT FOUND in Object!")
                 
            # Force update again just in case
            if not tenant.auto_post_to_tally:
                print("Forcing to True...")
                tenant.auto_post_to_tally = True
                db.commit()
                print("Committed True.")
        else:
            print("Tenant not found.")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_setting()
