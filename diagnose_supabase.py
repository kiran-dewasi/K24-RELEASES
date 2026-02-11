"""
Supabase Connection Diagnostic
Tests the actual connection to your Supabase project
"""
import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()

def test_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
    
    print("=" * 60)
    print("SUPABASE CONNECTION DIAGNOSTIC")
    print("=" * 60)
    
    print(f"\n1. Environment Variables:")
    print(f"   SUPABASE_URL: {url[:50]}..." if url else "   SUPABASE_URL: NOT SET")
    print(f"   SUPABASE_ANON_KEY: {key[:30]}..." if key else "   SUPABASE_ANON_KEY: NOT SET")
    
    if not url or not key:
        print("\n[FAIL] Missing Supabase credentials!")
        return
    
    print("\n2. Testing Connection...")
    try:
        from supabase import create_client
        client = create_client(url, key)
        print("   [OK] Supabase client created successfully")
    except Exception as e:
        print(f"   [FAIL] Failed to create client: {e}")
        return
    
    print("\n3. Testing user_profiles Table...")
    try:
        # Try to query user_profiles (should exist per your schema)
        result = client.table('user_profiles').select('*').limit(1).execute()
        print(f"   [OK] user_profiles table accessible")
    except Exception as e:
        error_str = str(e)
        if "does not exist" in error_str or "relation" in error_str:
            print(f"   [FAIL] Table 'user_profiles' does not exist!")
            print(f"   [INFO] Trying 'users_profile' instead...")
            try:
                result = client.table('users_profile').select('*').limit(1).execute()
                print(f"   [OK] users_profile table accessible (different name)")
            except Exception as e2:
                print(f"   [FAIL] Neither table exists: {e2}")
        else:
            print(f"   [FAIL] Query error: {e}")
    
    print("\n4. Testing subscriptions Table...")
    try:
        result = client.table('subscriptions').select('*').limit(1).execute()
        print(f"   [OK] subscriptions table accessible")
    except Exception as e:
        print(f"   [FAIL] subscriptions table error: {e}")
    
    print("\n5. Testing Auth Signup (Dry Run)...")
    try:
        # We can't actually sign up without a real email, but we can check if auth is responding
        # by attempting to sign in with fake creds (will fail but prove connectivity)
        result = client.auth.sign_in_with_password({
            "email": "test-diagnostic@fake.com",
            "password": "fake-password-123"
        })
    except Exception as e:
        error_str = str(e)
        if "Invalid login credentials" in error_str:
            print("   [OK] Auth endpoint responding (credentials rejected = working)")
        elif "Email not confirmed" in error_str:
            print("   [OK] Auth endpoint responding (email confirmation required)")
        else:
            print(f"   [WARN] Auth error: {error_str[:100]}")
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_supabase()
