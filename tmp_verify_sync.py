"""
Run this script to trigger a full sync after logging in.
Usage:
    venv311\Scripts\python.exe tmp_verify_sync.py YOUR_EMAIL YOUR_PASSWORD
"""
import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://localhost:8001'

if len(sys.argv) < 3:
    print("Usage: python tmp_verify_sync.py <email> <password>")
    print()
    print("This will:")
    print("  1. Log in and get your JWT token")
    print("  2. Trigger POST /api/sync/full  (stamps Tally data with your tenant_id)")
    print("  3. Check GET /api/dashboard/stats (should show real values)")
    sys.exit(1)

email    = sys.argv[1]
password = sys.argv[2]

# --- 1. Login ---
print(f'[1] Logging in as {email} ...')
r = requests.post(
    f'{BASE}/api/auth/login',
    json={'email': email, 'password': password},
    timeout=20
)
print(f'    Status: {r.status_code}')
if r.status_code != 200:
    print(f'    Error:  {r.text[:600]}')
    sys.exit(1)

data  = r.json()
token = data.get('access_token')
user  = data.get('user', {})
print(f'    tenant_id  = {user.get("tenant_id")}')
print(f'    username   = {user.get("username")}')
print(f'    Token OK   = {bool(token)}')

# --- 2. Full sync with JWT ---
print()
print('[2] POST /api/sync/full  (this may take 30-120 seconds) ...')
r2 = requests.post(
    f'{BASE}/api/sync/full',
    headers={'Authorization': f'Bearer {token}'},
    timeout=300
)
print(f'    Status: {r2.status_code}')
try:
    body = r2.json()
    print(f'    Result: {json.dumps(body, indent=2)[:3000]}')
except Exception:
    print(f'    Body:   {r2.text[:600]}')

# --- 3. Dashboard stats ---
print()
print('[3] GET /api/dashboard/stats ...')
r3 = requests.get(
    f'{BASE}/api/dashboard/stats',
    headers={'Authorization': f'Bearer {token}'},
    timeout=15
)
print(f'    Status: {r3.status_code}')
try:
    stats = r3.json()
    print(f'    Stats:  {json.dumps(stats, indent=2)}')
    if stats.get('sales', 0) == 0 and stats.get('receivables', 0) == 0:
        print()
        print('  ⚠️  Still showing zeros — check backend logs for sync errors.')
    else:
        print()
        print('  ✅ Dashboard showing real data!')
except Exception:
    print(f'    Body:   {r3.text[:400]}')
