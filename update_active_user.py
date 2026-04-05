import sys
import os
import httpx

# Add paths for local modules
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import SessionLocal, User

def fix_user():
    db = SessionLocal()
    email_to_fix = "ai.krisha24@gmail.com"
    user = db.query(User).filter(User.email == email_to_fix).first()
    
    if not user:
        print(f"User {email_to_fix} not found in local DB.")
        return
        
    print(f"Found user in local DB! ID: {user.id}, email: {user.email}")
    
    # Update local DB
    user.is_verified = True
    user.is_active = True
    supabase_id = user.google_api_key  # This stores the Supabase UUID
    
    db.commit()
    print("Local DB updated: is_verified=True, is_active=True.")
    db.close()
    
    # Update Supabase users_profile table
    if not supabase_id:
        print("No Supabase ID found for user.")
        return
        
    print(f"Updating Supabase profile for ID: {supabase_id}")
    
    supabase_url = os.getenv("VITE_SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not service_key:
        print("Missing Supabase credentials in .env")
        return
        
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    url = f"{supabase_url}/rest/v1/users_profile?id=eq.{supabase_id}"
    payload = {
        "is_verified": True,
        "is_active": True
    }
    
    resp = httpx.patch(url, headers=headers, json=payload, timeout=10)
    
    if resp.status_code in (200, 204):
        print("✅ Supabase users_profile updated successfully.")
    else:
        print(f"❌ Supabase update failed: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    fix_user()
