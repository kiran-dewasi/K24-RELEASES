import asyncio
from backend.services.supabase_service import supabase_service
import sys

async def create_test_user():
    email = "kittu@krishasales.com"
    password = "password123"
    
    print(f"Creating test user: {email}")
    
    if not supabase_service.client:
        print("[FAIL] Supabase client not initialized")
        return

    try:
        # Sign up (creates auth.users entry)
        response = supabase_service.client.auth.sign_up({
            "email": email,
            "password": password,
             "options": {
                "data": {
                    "full_name": "Kittu User",
                    "company_name": "Krishna Sales"
                }
            }
        })
        
        if response.user:
            print(f"[SUCCESS] User created in Supabase! ID: {response.user.id}")
            # Try logging in to verify
            print("Verifying login...")
            login_resp = supabase_service.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            if login_resp.session:
                print("[SUCCESS] Login verified. Token received.")
            else:
                print("[WARN] Login check failed (maybe email needs confirmation?)")
        else:
            # Need to check if user already exists
            print(f"[WARN] User might already exist or require confirmation. ID: {response.user}")
            
    except Exception as e:
        if "User already registered" in str(e):
            print("info: User already exists (OK)")
        else:
            print(f"[FAIL] Error creating user: {e}")

if __name__ == "__main__":
    asyncio.run(create_test_user())
