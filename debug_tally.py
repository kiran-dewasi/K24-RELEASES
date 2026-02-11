"""
Debug Tally XML - Using TDL Custom Reports
"""
import sys
sys.path.insert(0, '.')
import requests
import re

def test_tdl_ledger_with_balance():
    """Use TDL to fetch ledgers with closing balance."""
    
    xml = """<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY>
<EXPORTDATA>
    <REQUESTDESC>
        <STATICVARIABLES>
            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
        <TDL>
            <TDLMESSAGE>
                <REPORT NAME="LedgerBalances">
                    <FORMS>LedgerForm</FORMS>
                </REPORT>
                <FORM NAME="LedgerForm">
                    <PARTS>LedgerPart</PARTS>
                </FORM>
                <PART NAME="LedgerPart">
                    <LINES>LedgerLine</LINES>
                    <REPEAT>LedgerLine:AllLedgers</REPEAT>
                </PART>
                <LINE NAME="LedgerLine">
                    <FIELDS>FldName,FldParent,FldBalance</FIELDS>
                </LINE>
                <FIELD NAME="FldName">
                    <SET>$Name</SET>
                </FIELD>
                <FIELD NAME="FldParent">
                    <SET>$Parent</SET>
                </FIELD>
                <FIELD NAME="FldBalance">
                    <SET>$ClosingBalance</SET>
                </FIELD>
                <COLLECTION NAME="AllLedgers">
                    <TYPE>Ledger</TYPE>
                    <FETCH>Name,Parent,ClosingBalance</FETCH>
                </COLLECTION>
            </TDLMESSAGE>
        </TDL>
    </REQUESTDESC>
</EXPORTDATA>
</BODY>
</ENVELOPE>"""
    
    print("=" * 60)
    print("TDL: LEDGERS WITH CLOSING BALANCE")
    print("=" * 60)
    
    try:
        res = requests.post('http://localhost:9000', data=xml, timeout=15)
        print(f"Status: {res.status_code}")
        print(f"Response length: {len(res.text)} chars")
        
        # Parse the TDL field outputs
        names = re.findall(r'<FLDNAME>([^<]+)</FLDNAME>', res.text)
        parents = re.findall(r'<FLDPARENT>([^<]+)</FLDPARENT>', res.text)
        balances = re.findall(r'<FLDBALANCE>([^<]*)</FLDBALANCE>', res.text)
        
        print(f"\nFound {len(names)} ledgers with balance data")
        
        # Print all with balance
        print("\nLedger Balances:")
        for i, name in enumerate(names):
            parent = parents[i] if i < len(parents) else ''
            balance = balances[i] if i < len(balances) else '0'
            
            # Only show parties
            if 'Sundry' in parent:
                try:
                    bal = float(balance.strip()) if balance.strip() else 0
                except:
                    bal = 0
                status = "Cr" if bal >= 0 else "Dr"
                print(f"  {name} ({parent}): Rs.{abs(bal):,.2f} {status}")
        
        return names, parents, balances
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return [], [], []


def test_trial_balance():
    """Use Trial Balance report which always has ledger balances."""
    
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
    
    print("\n" + "=" * 60)
    print("TRIAL BALANCE REPORT")
    print("=" * 60)
    
    try:
        res = requests.post('http://localhost:9000', data=xml, timeout=15)
        print(f"Status: {res.status_code}")
        print(f"Response length: {len(res.text)} chars")
        
        # Look for DSP fields (Display fields in Trial Balance)
        names = re.findall(r'<DSPACCNAME>([^<]+)</DSPACCNAME>', res.text)
        closings = re.findall(r'<DSPCLAMT>([^<]*)</DSPCLAMT>', res.text)
        
        print(f"\nFound {len(names)} entries")
        
        # Print first 20
        print("\nTrial Balance entries (first 20):")
        for i, name in enumerate(names[:20]):
            closing = closings[i] if i < len(closings) else '0'
            print(f"  {name}: {closing}")
        
    except Exception as e:
        print(f"Error: {e}")


def update_database(names, parents, balances):
    """Update ledger balances in database."""
    if not names:
        print("\nNo data to update")
        return
        
    from backend.database import get_db, Ledger
    from datetime import datetime
    
    db = next(get_db())
    updated = 0
    
    for i, name in enumerate(names):
        parent = parents[i] if i < len(parents) else ''
        balance_str = balances[i] if i < len(balances) else '0'
        
        try:
            bal = float(balance_str.strip()) if balance_str.strip() else 0
        except:
            bal = 0
        
        # Find in DB
        ledger = db.query(Ledger).filter(Ledger.name == name).first()
        if ledger:
            ledger.closing_balance = bal
            ledger.parent = parent or ledger.parent
            ledger.last_synced = datetime.now()
            updated += 1
        else:
            # Create new
            new_ledger = Ledger(
                tenant_id="default",
                name=name,
                parent=parent,
                closing_balance=bal,
                last_synced=datetime.now()
            )
            db.add(new_ledger)
            updated += 1
    
    db.commit()
    print(f"\n{'='*60}")
    print(f"Updated {updated} ledgers in database")
    
    # Show Sundry Debtors
    print("\nSUNDRY DEBTORS:")
    for ld in db.query(Ledger).filter(Ledger.parent == 'Sundry Debtors').all():
        status = "Cr" if ld.closing_balance >= 0 else "Dr"
        print(f"  {ld.name}: Rs.{abs(ld.closing_balance):,.2f} {status}")
    
    print("\nSUNDRY CREDITORS:")
    for ld in db.query(Ledger).filter(Ledger.parent == 'Sundry Creditors').all():
        status = "Cr" if ld.closing_balance >= 0 else "Dr"
        print(f"  {ld.name}: Rs.{abs(ld.closing_balance):,.2f} {status}")


if __name__ == "__main__":
    names, parents, balances = test_tdl_ledger_with_balance()
    test_trial_balance()
    
    if names:
        print("\n" + "=" * 60)
        print("UPDATING DATABASE")
        print("=" * 60)
        update_database(names, parents, balances)
