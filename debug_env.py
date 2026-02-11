import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
url = os.getenv("SUPABASE_URL")

print(f"URL: {url}")
if key:
    print(f"Key Length: {len(key)}")
    print(f"Key Start: '{key[:10]}...'")
    print(f"Key End: '...{key[-5:]}'")
else:
    print("Key is None")

try:
    from supabase import create_client
    client = create_client(url, key)
    print("Client init success")
except Exception as e:
    print(f"Client init failed: {e}")
