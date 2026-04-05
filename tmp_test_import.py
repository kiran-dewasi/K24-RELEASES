import sys
try:
    from cloud_backend.database import get_supabase_client
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
