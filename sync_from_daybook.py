"""
Sync all ledger balances from Day Book vouchers - Fixed parsing
"""
import sys
sys.path.insert(0, '.')
import requests
import re
from collections import defaultdict
from backend.database import get_db, Ledger
from datetime import datetime
import xml.etree.ElementTree as ET

def clean_xml(text):
    """Remove invalid XML characters."""
    text = re.sub(r'&#x[0-9A-Fa-f]+;', '', text)
    text = re.sub(r'&#[0-9]+;', '', text)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return text

def fetch_all_vouchers():
    """Fetch all vouchers and calculate party balances."""
    
    xml = """<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY>
<EXPORTDATA>
    <REQUESTDESC>
        <REPORTNAME>Day Book</REPORTNAME>
        <STATICVARIABLES>
            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
    </REQUESTDESC>
</EXPORTDATA>
</BODY>
</ENVELOPE>"""
    
    print("=" * 60)
    print("FETCHING ALL VOUCHERS FROM TALLY")
    print("=" * 60)
    
    try:
        res = requests.post('http://localhost:9000', data=xml, timeout=30)
        print(f"Status: {res.status_code}")
        print(f"Response length: {len(res.text)} chars")
        
        # Clean and parse XML
        clean_text = clean_xml(res.text)
        
        # Use ElementTree for proper parsing
        try:
            root = ET.fromstring(clean_text)
        except ET.ParseError as e:
            print(f"XML Parse Error: {e}")
            # Fallback to regex
            return parse_with_regex(res.text)
        
        # Dictionary to accumulate balances
        party_credits = defaultdict(float)
        party_debits = defaultdict(float)
        
        voucher_count = 0
        
        # Find all VOUCHER elements
        for voucher in root.iter('VOUCHER'):
            voucher_count += 1
            
            # Get party name
            party_name = voucher.findtext('PARTYNAME') or voucher.findtext('PARTYLEDGERNAME')
            if not party_name:
                continue
            
            vtype = voucher.findtext('VOUCHERTYPENAME') or ''
            
            # Find ledger entries
            for ledger_list in ['ALLLEDGERENTRIES.LIST', 'LEDGERENTRIES.LIST']:
                for led in voucher.findall(ledger_list):
                    led_name = led.findtext('LEDGERNAME') or ''
                    amt_str = led.findtext('AMOUNT') or '0'
                    
                    # Match party name
                    if led_name == party_name:
                        try:
                            amt = float(amt_str.replace(',', ''))
                            # In Tally ledger entries: negative = credit, positive = debit
                            if amt < 0:
                                party_credits[party_name] += abs(amt)
                            else:
                                party_debits[party_name] += amt
                        except:
                            pass
        
        print(f"Parsed {voucher_count} vouchers using ElementTree")
        
        # If ElementTree found nothing, try regex
        if voucher_count == 0:
            return parse_with_regex(res.text)
        
        # Calculate net balances
        party_balances = {}
        for party in set(list(party_credits.keys()) + list(party_debits.keys())):
            cr = party_credits[party]
            dr = party_debits[party]
            # Net = Cr - Dr (positive = they owe us)
            net = cr - dr
            party_balances[party] = net
        
        return party_balances
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {}


def parse_with_regex(text):
    """Fallback regex parsing."""
    print("\nUsing regex fallback...")
    
    party_credits = defaultdict(float)
    party_debits = defaultdict(float)
    
    # Find all party names with their ledger entry amounts
    # Pattern: PARTYNAME followed by ALLLEDGERENTRIES with LEDGERNAME=same party and AMOUNT
    
    parties = re.findall(r'<PARTYNAME>([^<]+)</PARTYNAME>', text)
    print(f"Found {len(parties)} party references")
    
    # Find all ledger entries with amounts
    entries = re.findall(r'<LEDGERNAME>([^<]+)</LEDGERNAME>.*?<AMOUNT>([^<]+)</AMOUNT>', text, re.DOTALL)
    print(f"Found {len(entries)} ledger entries")
    
    for led_name, amt_str in entries:
        try:
            amt = float(amt_str.replace(',', ''))
            if amt < 0:
                party_credits[led_name] += abs(amt)
            else:
                party_debits[led_name] += amt
        except:
            pass
    
    # Calculate balances
    party_balances = {}
    for party in set(list(party_credits.keys()) + list(party_debits.keys())):
        cr = party_credits[party]
        dr = party_debits[party]
        net = cr - dr
        party_balances[party] = net
    
    return party_balances


def update_database(party_balances):
    """Update ledger balances in database."""
    
    print("\n" + "=" * 60)
    print("ALL PARTY BALANCES:")
    print("=" * 60)
    
    # Filter to show only significant balances
    sig_balances = {k: v for k, v in party_balances.items() if abs(v) > 100}
    
    for party, bal in sorted(sig_balances.items(), key=lambda x: abs(x[1]), reverse=True):
        status = "Cr" if bal > 0 else "Dr"
        print(f"  {party}: Rs.{abs(bal):,.2f} {status}")
    
    # Update database
    db = next(get_db())
    updated = 0
    
    for party, bal in party_balances.items():
        ledger = db.query(Ledger).filter(Ledger.name == party).first()
        if ledger:
            ledger.closing_balance = bal
            ledger.last_synced = datetime.now()
            updated += 1
    
    db.commit()
    print(f"\nUpdated {updated} ledgers in database")
    
    # Show summary
    print("\n" + "=" * 60)
    print("SUNDRY DEBTORS (RECEIVABLES):")
    print("=" * 60)
    total_recv = 0
    for ld in db.query(Ledger).filter(Ledger.parent == 'Sundry Debtors').all():
        bal = ld.closing_balance
        status = "Cr" if bal > 0 else "Dr"
        print(f"  {ld.name}: Rs.{abs(bal):,.2f} {status}")
        if bal > 0:
            total_recv += bal
    print(f"\n  TOTAL RECEIVABLES: Rs.{total_recv:,.2f}")
    
    print("\n" + "=" * 60)
    print("SUNDRY CREDITORS (PAYABLES):")  
    print("=" * 60)
    total_pay = 0
    for ld in db.query(Ledger).filter(Ledger.parent == 'Sundry Creditors').all():
        bal = ld.closing_balance
        status = "Cr" if bal > 0 else "Dr"
        print(f"  {ld.name}: Rs.{abs(bal):,.2f} {status}")
        if bal > 0:  # Cr balance on Sundry Creditor = we owe them
            total_pay += bal
    print(f"\n  TOTAL PAYABLES: Rs.{total_pay:,.2f}")


if __name__ == "__main__":
    balances = fetch_all_vouchers()
    update_database(balances)
