"""
Complete Ledger Sync Script
Fetches ledger data with closing balances from Tally and updates database.
"""
import sys
sys.path.insert(0, '.')

from backend.tally_reader import TallyReader
from backend.database import get_db, Ledger
from datetime import datetime

# XML with FETCH directive for closing balance
LEDGER_XML = """<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME>
<STATICVARIABLES>
    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
    <ACCOUNTTYPE>Ledgers</ACCOUNTTYPE>
</STATICVARIABLES>
<TDL><OBJECT NAME="Ledger">
    <FETCH>Name,Parent,ClosingBalance,PartyGSTIN,Email,LedgerMobile</FETCH>
</OBJECT></TDL>
</REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>"""

def main():
    print("=" * 50)
    print("COMPLETE LEDGER SYNC FROM TALLY")
    print("=" * 50)
    
    reader = TallyReader()
    
    # Fetch data
    print("\nFetching ledgers with closing balances...")
    data = reader._fetch_and_parse(
        LEDGER_XML, 
        'LEDGER', 
        ['Name', 'Parent', 'ClosingBalance', 'PartyGSTIN', 'Email', 'LedgerMobile']
    )
    
    print(f"Fetched {len(data)} ledgers from Tally")
    
    if not data:
        print("No data fetched! Check Tally connection.")
        return
    
    # Show sample
    print("\nSample Data:")
    for d in data[:5]:
        print(f"  {d}")
    
    # Update database
    db = next(get_db())
    added = 0
    updated = 0
    
    for l in data:
        name = l.get('Name')
        if not name:
            continue
        
        # Parse closing balance
        try:
            bal = float(l.get('ClosingBalance') or 0)
        except (ValueError, TypeError):
            bal = 0.0
        
        parent = l.get('Parent', '')
        gstin = l.get('PartyGSTIN', '')
        email = l.get('Email', '')
        phone = l.get('LedgerMobile', '')
        
        existing = db.query(Ledger).filter(Ledger.name == name).first()
        if existing:
            existing.parent = parent
            existing.closing_balance = bal
            existing.gstin = gstin
            existing.email = email
            existing.phone = phone
            existing.last_synced = datetime.now()
            updated += 1
        else:
            new_ledger = Ledger(
                tenant_id="default",
                name=name,
                parent=parent,
                closing_balance=bal,
                gstin=gstin,
                email=email,
                phone=phone,
                last_synced=datetime.now()
            )
            db.add(new_ledger)
            added += 1
    
    db.commit()
    
    print(f"\nSync Complete: Added {added}, Updated {updated}")
    
    # Show Sundry Debtors
    print("\n" + "=" * 50)
    print("SUNDRY DEBTORS (RECEIVABLES):")
    print("=" * 50)
    for ld in db.query(Ledger).filter(Ledger.parent == 'Sundry Debtors').all():
        status = "Dr" if ld.closing_balance < 0 else "Cr"
        print(f"  {ld.name}: Rs.{abs(ld.closing_balance):,.2f} {status}")
    
    # Show Sundry Creditors  
    print("\n" + "=" * 50)
    print("SUNDRY CREDITORS (PAYABLES):")
    print("=" * 50)
    for ld in db.query(Ledger).filter(Ledger.parent == 'Sundry Creditors').all():
        status = "Dr" if ld.closing_balance < 0 else "Cr"
        print(f"  {ld.name}: Rs.{abs(ld.closing_balance):,.2f} {status}")

if __name__ == "__main__":
    main()
