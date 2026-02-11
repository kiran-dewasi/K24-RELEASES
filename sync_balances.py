"""
Complete Ledger Sync with Balances
Uses TallyConnector to fetch each ledger with its closing balance.
"""
import sys
sys.path.insert(0, '.')

from backend.tally_connector import TallyConnector
from backend.database import get_db, Ledger
from datetime import datetime

def main():
    print("=" * 50)
    print("LEDGER SYNC WITH BALANCES")
    print("=" * 50)
    
    connector = TallyConnector()
    db = next(get_db())
    
    # First get all ledgers in DB
    ledgers = db.query(Ledger).filter(
        Ledger.parent.in_(['Sundry Debtors', 'Sundry Creditors'])
    ).all()
    
    print(f"\nFound {len(ledgers)} party ledgers to update")
    
    updated = 0
    for ld in ledgers:
        print(f"\nFetching: {ld.name}...")
        
        # Fetch complete details from Tally
        details = connector.fetch_ledger_complete(ld.name)
        
        if details:
            bal = details.get('closing_balance', 0)
            ld.closing_balance = bal
            ld.gstin = details.get('gstin') or ld.gstin
            ld.email = details.get('email') or ld.email
            ld.phone = details.get('phone') or ld.phone
            ld.address = details.get('address') or ld.address
            ld.last_synced = datetime.now()
            updated += 1
            print(f"  -> Balance: Rs.{abs(bal):,.2f} {'Cr' if bal >= 0 else 'Dr'}")
        else:
            print(f"  -> NOT FOUND in Tally")
    
    db.commit()
    print(f"\n{'='*50}")
    print(f"Updated {updated} ledgers")
    
    # Show final balances
    print(f"\n{'='*50}")
    print("SUNDRY DEBTORS (RECEIVABLES):")
    print("=" * 50)
    total_recv = 0
    for ld in db.query(Ledger).filter(Ledger.parent == 'Sundry Debtors').all():
        status = "Cr" if ld.closing_balance >= 0 else "Dr"
        print(f"  {ld.name}: Rs.{abs(ld.closing_balance):,.2f} {status}")
        if ld.closing_balance > 0:  # Cr balance = they owe us
            total_recv += ld.closing_balance
    print(f"\n  TOTAL RECEIVABLES: Rs.{total_recv:,.2f}")
    
    print(f"\n{'='*50}")
    print("SUNDRY CREDITORS (PAYABLES):")
    print("=" * 50)
    total_pay = 0
    for ld in db.query(Ledger).filter(Ledger.parent == 'Sundry Creditors').all():
        status = "Cr" if ld.closing_balance >= 0 else "Dr"
        print(f"  {ld.name}: Rs.{abs(ld.closing_balance):,.2f} {status}")
        if ld.closing_balance < 0:  # Dr balance = we owe them
            total_pay += abs(ld.closing_balance)
    print(f"\n  TOTAL PAYABLES: Rs.{total_pay:,.2f}")

if __name__ == "__main__":
    main()
