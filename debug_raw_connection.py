import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")

target = f"{url}/rest/v1/"
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}

print(f"Testing connectivity to: {target}")

try:
    resp = requests.get(target, headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
