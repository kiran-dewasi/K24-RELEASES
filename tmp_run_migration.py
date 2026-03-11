"""End-to-end test: table check + create intent + submit payment"""
import httpx
from dotenv import dotenv_values

env = dotenv_values("backend/.env")
URL = env.get("SUPABASE_URL", "https://gxukvnoiyzizienswgni.supabase.co")
KEY = (env.get("SUPABASE_SERVICE_KEY") or
       env.get("SUPABASE_SERVICE_ROLE_KEY") or
       env.get("SUPABASE_ANON_KEY") or "")

H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}

# 1. Verify table exists
print("=== 1. Table check ===")
r = httpx.get(URL + "/rest/v1/subscription_intents?limit=1", headers=H, timeout=10)
print("Status:", r.status_code)
if r.status_code == 200:
    print("Table EXISTS. Rows:", r.json())
else:
    print("FAIL:", r.text[:200])
    raise SystemExit("Table not found - did the SQL run successfully?")

# 2. Test the backend endpoint directly
print("\n=== 2. Backend /public/subscribe/intent POST ===")
r2 = httpx.post(
    "http://localhost:8001/public/subscribe/intent",
    json={
        "plan_id":      "pro",
        "name":         "Test User",
        "company_name": "Test Co Pvt Ltd",
        "email":        "test@example.com",
        "phone":        "9876543210",
    },
    timeout=15
)
print("Status:", r2.status_code)
print("Body:", r2.text[:400])

if r2.status_code == 200:
    intent_id = r2.json()["intent_id"]
    print("\nIntent ID:", intent_id)

    # 3. Submit payment
    print("\n=== 3. Submit payment ref ===")
    r3 = httpx.patch(
        f"http://localhost:8001/public/subscribe/intent/{intent_id}/payment",
        json={"upi_ref": "412345678901"},
        timeout=15
    )
    print("Status:", r3.status_code)
    print("Body:", r3.text[:400])

    if r3.status_code == 200:
        print("\nFULL FLOW WORKS! The subscribe form will now work end-to-end.")
    else:
        print("\nPayment step failed.")
else:
    print("\nIntent creation failed.")
