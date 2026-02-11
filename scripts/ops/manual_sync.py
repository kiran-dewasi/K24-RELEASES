
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from backend.tally_connector import TallyConnector
from supabase import create_client

# Load Env
load_dotenv()

import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from backend.tally_connector import TallyConnector
from sqlalchemy import create_engine, text

# Load Env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
TENANT_ID = "TENANT-12345"

if not DATABASE_URL:
    print("Error: DATABASE_URL not set")
    exit(1)

engine = create_engine(DATABASE_URL)
tally = TallyConnector() 

async def sync_vouchers():
    print(f"\n{'='*50}")
    print("🔄 MANUAL SYNC (SQL Bypassed): TALLY -> WEB DB")
    print(f"{'='*50}")
    
    # Use Robust TallyReader
    from backend.tally_reader import TallyReader
    reader = TallyReader()
    
    print("📡 Fetching Vouchers from Tally (Last 30 Days + Future)...")
    try:
        # Fetch broad range
        txns = reader.get_transactions(start_date="20240401", end_date="20260331")
        
        if not txns:
            print("❌ No vouchers returned from Tally.")
            return

        print(f"✅ Found {len(txns)} vouchers in Tally.")
        
        count = 0
        with engine.connect() as conn:
            for txn in txns:
                # Construct DB Record
                v_type = txn.get('type')
                v_num = txn.get('number') or f"TALLY-{int(datetime.now().timestamp())}-{count}"
                party = txn.get('party') or "Unknown"
                date_str = txn.get('date') # YYYYMMDD typically
                
                # Convert Date Format YYYYMMDD -> YYYY-MM-DD
                if date_str and len(date_str) == 8:
                    date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                
                # Calculate Amount: Use the Party Ledger's amount or Max amount
                # TallyReader returns 'ledger_entries'.
                amount = 0.0
                entries = txn.get('ledger_entries', [])
                if entries:
                    # Heuristic: Try to find amount matching the party
                    for entry in entries:
                         # Clean amount string
                         amt_str = str(entry.get('amount', '0')).replace("Dr", "").replace("Cr", "").strip()
                         try:
                             val = abs(float(amt_str))
                             if val > amount: amount = val
                         except: pass
                
                narration = txn.get('narration')
                
                print(f"   Processing: {v_type} #{v_num} | {party} | {amount} | {date_str}")
                
                # Check Duplicate
                chk = conn.execute(text("SELECT count(*) FROM vouchers WHERE voucher_number = :vn AND tenant_id = :tid"), 
                    {"vn": v_num, "tid": TENANT_ID})
                
                if chk.scalar() > 0:
                    print(f"   ⚠️  Skipping duplicate: #{v_num}")
                    continue
                    
                # Insert
                sql = text("""
                    INSERT INTO vouchers 
                    (tenant_id, voucher_number, voucher_type, party_name, amount, date, narration, sync_status, tally_voucher_id, source, guid) 
                    VALUES 
                    (:tid, :vn, :vt, :pn, :amt, :dt, :narr, :stat, :tvid, :src, :guid)
                """)
                
                params = {
                    "tid": TENANT_ID,
                    "vn": v_num,
                    "vt": v_type,
                    "pn": party,
                    "amt": amount,
                    "dt": date_str,
                    "narr": narration,
                    "stat": "SYNCED",
                    "tvid": v_num,
                    "src": "sync",
                    "guid": txn.get('guid') or f"SYNC-{v_num}"
                }
                
                conn.execute(sql, params)
                conn.commit()
                print(f"   ✅ Inserted successfully.")
                count += 1

        print(f"\n🎉 Sync Complete. Inserted {count} new vouchers.")

    except Exception as e:
        print(f"❌ Sync Error: {e}")
        import traceback
        traceback.print_exc()

async def sync_masters():
    print(f"\n{'='*50}")
    print("🔄 MASTER SYNC: LEDGERS & CONTACTS")
    print(f"{'='*50}")
    
    from backend.tally_reader import TallyReader
    reader = TallyReader()
    
    print("📡 Fetching Ledger List from Tally...")
    all_names = reader.get_all_ledgers()
    print(f"✅ Found {len(all_names)} ledgers.")
    
    updated_count = 0
    created_count = 0
    
    with engine.connect() as conn:
        for name in all_names:
            try:
                # Fetch deeper info
                # Optimization: In production, we'd use a single large TDL request.
                # Here we do iterative for simplicity/robustness.
                details = reader.get_full_ledger_details(name)
                if not details: continue
                
                # Check for existing
                chk = conn.execute(text("SELECT id FROM ledgers WHERE name = :nm AND tenant_id = :tid"), 
                                   {"nm": name, "tid": TENANT_ID}).fetchone()
                
                # Determine Contact Type based on Group
                grp = details.get('parent', '').lower()
                l_type = 'ledger'
                if 'debtor' in grp: l_type = 'customer'
                elif 'creditor' in grp: l_type = 'vendor'
                elif 'sales' in grp: l_type = 'sales'
                elif 'purchase' in grp: l_type = 'purchase'
                elif 'bank' in grp or 'cash' in grp: l_type = 'bank'
                
                if chk:
                     # UPDATE
                     sql = text("""
                        UPDATE ledgers SET 
                        parent = :par, 
                        gstin = :gst, 
                        closing_balance = :bal, 
                        phone = :ph,
                        email = :em,
                        type = :typ,
                        sync_status = 'SYNCED'
                        WHERE id = :id
                     """)
                     conn.execute(sql, {
                         "par": details.get('parent'),
                         "gst": details.get('gst') or None,
                         "bal": details.get('balance', 0.0),
                         "ph": details.get('phone') or None,
                         "em": details.get('email') or None,
                         "typ": l_type,
                         "id": chk[0]
                     })
                     updated_count += 1
                else:
                     # INSERT
                     sql = text("""
                        INSERT INTO ledgers 
                        (tenant_id, name, parent, gstin, closing_balance, phone, email, type, sync_status)
                        VALUES
                        (:tid, :nm, :par, :gst, :bal, :ph, :em, :typ, 'SYNCED')
                     """)
                     conn.execute(sql, {
                         "tid": TENANT_ID,
                         "nm": name,
                         "par": details.get('parent'),
                         "gst": details.get('gst') or None,
                         "bal": details.get('balance', 0.0),
                         "ph": details.get('phone') or None,
                         "em": details.get('email') or None,
                         "typ": l_type
                     })
                     created_count += 1
                
                conn.commit()
                # print(f"   Processed: {name} ({l_type})") # Verbose off
                
            except Exception as e:
                print(f"   ❌ Failed to sync {name}: {e}")
                
    print(f"🎉 Masters Synced: {created_count} new, {updated_count} updated.")

if __name__ == "__main__":
    asyncio.run(sync_masters())
    asyncio.run(sync_vouchers())

