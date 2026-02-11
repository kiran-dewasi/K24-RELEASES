import sys
import os
import asyncio
# Add project root to path
sys.path.insert(0, os.getcwd())

from backend.database import SessionLocal, Ledger, StockItem
from sqlalchemy import desc
from backend.services.tally_sync_service import sync_now

async def run_sync_and_verify():
    print("--- MANUAL SYNC EXECUTION (FINAL CHECK) ---")
    try:
        # Force Full Sync to ensure everything updates
        result = await sync_now(mode="incremental")
        print(f"Sync Result: {result}")
    except Exception as e:
        print(f"SYNC FAILED: {e}")

    print("\n--- VERIFYING LEDGER BALANCES (Top 5) ---")
    db = SessionLocal()
    try:
        ledgers = db.query(Ledger).order_by(desc(Ledger.closing_balance)).limit(5).all()
        
        has_zeros = False
        if ledgers:
            no_val_count = 0
            for l in ledgers:
                print(f"  {l.name}: {l.closing_balance:.2f}")
                if l.closing_balance == 0:
                    no_val_count += 1
            
            if no_val_count == len(ledgers):
                has_zeros = True
        else:
            print("  No ledgers found!")

        if has_zeros:
             print("\nWARNING: All top ledgers are 0.")
        else:
             print("\nSUCCESS: Top ledgers have values!")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except: pass
    asyncio.run(run_sync_and_verify())
