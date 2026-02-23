"""
Quick verification: DB state + live Customer 360 API test
Run with: python verify_360.py
"""
import sqlite3
import urllib.request
import urllib.error
import json

DB_PATH = "k24_shadow.db"
BASE    = "http://127.0.0.1:8001"
API_KEY = "k24-secret-key-123"

# ── 1. DB CHECK ──────────────────────────────────────────────────────────────
print("=" * 60)
print("1. DATABASE STATE")
print("=" * 60)

db = sqlite3.connect(DB_PATH)

# Users
rows = db.execute("SELECT email, tenant_id FROM users").fetchall()
print(f"\nUsers ({len(rows)} total):")
for email, tid in rows:
    tag = "✅" if tid == "TENANT-12345" else "❌"
    print(f"  {tag}  {email:<32} tenant_id={tid!r}")

# Ledgers
l_real  = db.execute("SELECT COUNT(*) FROM ledgers WHERE tenant_id='TENANT-12345'").fetchone()[0]
l_other = db.execute("SELECT COUNT(*) FROM ledgers WHERE tenant_id!='TENANT-12345' OR tenant_id IS NULL").fetchone()[0]
print(f"\nLedgers: ✅ {l_real} under TENANT-12345   ❌ {l_other} under wrong tenant")

# Vouchers
v_real  = db.execute("SELECT COUNT(*) FROM vouchers WHERE tenant_id='TENANT-12345'").fetchone()[0]
v_other = db.execute("SELECT COUNT(*) FROM vouchers WHERE tenant_id!='TENANT-12345' OR tenant_id IS NULL").fetchone()[0]
print(f"Vouchers: ✅ {v_real} under TENANT-12345   ❌ {v_other} under wrong tenant")

# Pick a real customer for the API test
sample = db.execute(
    "SELECT id, name FROM ledgers WHERE tenant_id='TENANT-12345' "
    "AND parent IN ('Sundry Debtors','Sundry Creditors') LIMIT 1"
).fetchone()
db.close()

# ── 2. LIVE API TEST ─────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("2. LIVE API TEST — Customer 360")
print("=" * 60)

if not sample:
    print("❌ No Sundry Debtors/Creditors found in DB — can't test API")
else:
    cid, cname = sample
    print(f"\nTesting: Customer #{cid} — {cname!r}")
    url = f"{BASE}/api/customers/{cid}/360"
    req = urllib.request.Request(url, headers={"x-api-key": API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            print(f"  HTTP status   : 200 ✅")
            print(f"  name          : {data.get('name')}")
            print(f"  total_business: {data.get('total_business')}")
            print(f"  voucher_count : {len(data.get('recent_vouchers', []))}")
            print(f"  outstanding   : {data.get('summary', {}).get('outstanding_total')}")
            print("\n✅ RESULT: Customer 360 is WORKING CORRECTLY")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP status   : {e.code} ❌")
        print(f"  Error         : {body[:300]}")
        print("\n❌ RESULT: Customer 360 STILL FAILING")
    except Exception as e:
        print(f"  Connection error: {e}")
        print("  (Is the backend running on port 8001?)")
