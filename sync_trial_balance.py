"""
Parse Tally Trial Balance and update ledger balances.
Based on actual Tally XML response format.
"""
import sys
sys.path.insert(0, '.')
import requests
import re
from backend.database import get_db, Ledger
from datetime import datetime

def fetch_trial_balance():
    """Fetch Trial Balance from Tally and extract account balances."""
    
    xml = """<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY>
<EXPORTDATA>
    <REQUESTDESC>
        <REPORTNAME>Trial Balance</REPORTNAME>
        <STATICVARIABLES>
            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
    </REQUESTDESC>
</EXPORTDATA>
</BODY>
</ENVELOPE>"""
    
    print("=" * 60)
    print("FETCHING TRIAL BALANCE FROM TALLY")
    print("=" * 60)
    
    try:
        res = requests.post('http://localhost:9000', data=xml, timeout=15)
        print(f"Status: {res.status_code}")
        
        # Parse account names and balances using the actual response format
        # Format: <DSPACCNAME><DSPDISPNAME>account</DSPDISPNAME></DSPACCNAME>
        # followed by <DSPACCINFO><DSPCLDRAMT><DSPCLDRAMTA>dr_amt</DSPCLDRAMTA></DSPCLDRAMT>
        #            <DSPCLCRAMT><DSPCLCRAMTA>cr_amt</DSPCLCRAMTA></DSPCLCRAMT></DSPACCINFO>
        
        # Extract all account names
        names = re.findall(r'<DSPDISPNAME>([^<]+)</DSPDISPNAME>', res.text)
        
        # Extract all debit amounts
        dr_amounts = re.findall(r'<DSPCLDRAMTA>([^<]*)</DSPCLDRAMTA>', res.text)
        
        # Extract all credit amounts
        cr_amounts = re.findall(r'<DSPCLCRAMTA>([^<]*)</DSPCLCRAMTA>', res.text)
        
        print(f"Found {len(names)} accounts")
        print(f"Found {len(dr_amounts)} debit amounts")
        print(f"Found {len(cr_amounts)} credit amounts")
        
        # Build account list with balances
        accounts = []
        for i, name in enumerate(names):
            dr_str = dr_amounts[i] if i < len(dr_amounts) else ''
            cr_str = cr_amounts[i] if i < len(cr_amounts) else ''
            
            # Parse amounts
            try:
                dr = float(dr_str) if dr_str.strip() else 0
            except:
                dr = 0
            
            try:
                cr = float(cr_str) if cr_str.strip() else 0
            except:
                cr = 0
            
            # Net balance (Dr - Cr for Tally convention)
            # In Tally: Positive = Dr (Receivable/Asset), Negative = Cr (Payable/Liability)
            # For Sundry Debtors: Cr balance means they owe us (receivable)
            net_balance = dr - cr  # This will be negative if Cr > Dr
            
            accounts.append({
                'name': name,
                'dr': dr,
                'cr': cr,
                'balance': net_balance
            })
        
        return accounts
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []


def update_database(accounts):
    """Update ledger balances in database."""
    if not accounts:
        print("\nNo accounts to update")
        return
    
    db = next(get_db())
    updated = 0
    
    # Print all accounts with balances
    print("\n" + "=" * 60)
    print("ACCOUNT BALANCES FROM TRIAL BALANCE:")
    print("=" * 60)
    for acc in accounts:
        if acc['balance'] != 0:
            status = "Dr" if acc['balance'] > 0 else "Cr"
            print(f"  {acc['name']}: Rs.{abs(acc['balance']):,.2f} {status}")
    
    # Update database
    print("\n" + "=" * 60)
    print("UPDATING DATABASE")
    print("=" * 60)
    
    for acc in accounts:
        name = acc['name']
        balance = acc['balance']
        
        # Find in DB (case-insensitive match)
        ledger = db.query(Ledger).filter(Ledger.name.ilike(f"%{name}%")).first()
        
        if not ledger:
            # Try exact match
            ledger = db.query(Ledger).filter(Ledger.name == name).first()
        
        if ledger:
            old_bal = ledger.closing_balance
            ledger.closing_balance = balance
            ledger.last_synced = datetime.now()
            updated += 1
            if old_bal != balance:
                print(f"  Updated {name}: {old_bal} -> {balance}")
    
    db.commit()
    print(f"\nUpdated {updated} ledgers")
    
    # Show final Sundry Debtors
    print("\n" + "=" * 60)
    print("SUNDRY DEBTORS (RECEIVABLES):")
    print("=" * 60)
    total_recv = 0
    for ld in db.query(Ledger).filter(Ledger.parent == 'Sundry Debtors').all():
        # In Tally: Cr balance for Sundry Debtors = they owe us (receivable)
        # Our DB stores: positive = credit (they owe us)
        bal = ld.closing_balance
        status = "Cr" if bal < 0 else "Dr"  # Negative in our format = Cr
        
        # Actually for sundry debtors, Cr balance means receivable (they owe us)
        # Tally convention: Sundry Debtor with Cr balance = outstanding receivable
        print(f"  {ld.name}: Rs.{abs(bal):,.2f} {status}")
        if bal < 0:  # Cr balance = receivable
            total_recv += abs(bal)
    
    print(f"\n  TOTAL RECEIVABLES: Rs.{total_recv:,.2f}")
    
    # Show Sundry Creditors
    print("\n" + "=" * 60)
    print("SUNDRY CREDITORS (PAYABLES):")
    print("=" * 60)
    total_pay = 0
    for ld in db.query(Ledger).filter(Ledger.parent == 'Sundry Creditors').all():
        bal = ld.closing_balance
        status = "Cr" if bal < 0 else "Dr"
        print(f"  {ld.name}: Rs.{abs(bal):,.2f} {status}")
        if bal < 0:  # Cr balance = we owe them
            total_pay += abs(bal)
    
    print(f"\n  TOTAL PAYABLES: Rs.{total_pay:,.2f}")


if __name__ == "__main__":
    accounts = fetch_trial_balance()
    update_database(accounts)
