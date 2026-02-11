import sys
import os
import logging

# Configure logging first
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s', stream=sys.stdout)

sys.path.insert(0, os.getcwd())
from backend.sync_engine import SyncEngine
from backend.database import SessionLocal, Ledger

def debug_sync_error():
    print("--- DEBUGGING SYNC ENGINE ERROR ---")
    eng = SyncEngine()
    
    # Run pull_ledgers directly
    result = eng.pull_ledgers()
    print(f"Sync Result: {result}")
    
    # Check specifically if Dhanlaxmi has balance
    db = SessionLocal()
    dhan = db.query(Ledger).filter(Ledger.name.like("%DHANLAXMI%")).first()
    if dhan:
        print(f"Dhanlaxmi Balance: {dhan.closing_balance}")
    else:
        print("Dhanlaxmi not found in DB.")
        
    db.close()

if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except: pass
    debug_sync_error()
