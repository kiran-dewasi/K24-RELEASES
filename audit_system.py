import requests
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# --- 1. Audit Tally ---
def audit_tally():
    url = "http://localhost:9000"
    print("\n--- 🔍 Auditing Tally (Port 9000) ---")
    
    # Fetch ALL Vouchers for the year
    xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Voucher Register</REPORTNAME>
                <STATICVARIABLES>
                     <SVFROMDATE>20250401</SVFROMDATE>
                     <SVTODATE>20260331</SVTODATE>
                     <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
    </ENVELOPE>"""
    
    try:
        resp = requests.post(url, data=xml, headers={'Content-Type': 'application/xml'}, timeout=5)
        # Parse simple count or presence
        if "<VOUCHER" in resp.text:
            print("✅ FOUND VOUCHERS IN TALLY API!")
            # Extract basic details (naive parsing)
            snippets = resp.text.split('<VOUCHER')
            print(f"Total Vouchers Found: {len(snippets)-1}")
            for i, snip in enumerate(snippets[1:4]): # Show first 3
                date = snip.split('<DATE>')[1].split('</DATE>')[0] if '<DATE>' in snip else "N/A"
                party = snip.split('<PARTYLEDGERNAME>')[1].split('</PARTYLEDGERNAME>')[0] if '<PARTYLEDGERNAME>' in snip else "N/A"
                print(f"   [{i+1}] Date: {date}, Party: {party}")
        else:
            print("❌ Tally API says: NO VOUCHERS found for 2025-26.")
            print(f"Snippet: {resp.text[:200]}")

    except Exception as e:
        print(f"❌ Connection Failed: {e}")

# --- 2. Audit Database ---
def audit_db():
    print("\n--- 🔍 Auditing Database (Supabase) ---")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Skipping DB (No URL)")
        return

    try:
        conn = create_engine(db_url).connect()
        # Check Vouchers
        res = conn.execute(text("SELECT id, voucher_number, date, amount, tenant_id FROM vouchers ORDER BY created_at DESC LIMIT 5"))
        rows = list(res)
        if rows:
            print(f"✅ Found {len(rows)} vouchers in DB:")
            for r in rows:
                print(f"   DB Row: {r}")
        else:
            print("❌ No vouchers found in DB 'vouchers' table.")
        
        conn.close()
    except Exception as e:
        print(f"❌ DB Error: {e}")

if __name__ == "__main__":
    audit_tally()
    audit_db()
