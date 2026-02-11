"""Fetch ledger balances from Tally and update database."""
import requests
import xml.etree.ElementTree as ET
import re
import sys
sys.path.insert(0, '.')

from backend.database import get_db, Ledger

def clean_xml(xml_string):
    """Remove invalid XML characters and entities."""
    xml_string = re.sub(r'&#x[0-9A-Fa-f]+;', '', xml_string)
    xml_string = re.sub(r'&#[0-9]+;', '', xml_string)
    xml_string = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xml_string)
    return xml_string


def fetch_sundry_debtors_with_balance():
    """Fetch Sundry Debtors with closing balance from Tally."""
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
                <REPORT NAME="DebtorBalances">
                    <FORMS>DebtorForm</FORMS>
                </REPORT>
                <FORM NAME="DebtorForm">
                    <PARTS>DebtorPart</PARTS>
                </FORM>
                <PART NAME="DebtorPart">
                    <LINES>DebtorLine</LINES>
                    <REPEAT>DebtorLine:DebtorsColl</REPEAT>
                </PART>
                <LINE NAME="DebtorLine">
                    <FIELDS>FName,FBalance</FIELDS>
                </LINE>
                <FIELD NAME="FName">
                    <SET>$Name</SET>
                </FIELD>
                <FIELD NAME="FBalance">
                    <SET>$ClosingBalance</SET>
                </FIELD>
                <COLLECTION NAME="DebtorsColl">
                    <TYPE>Ledger</TYPE>
                    <CHILDOF>Sundry Debtors</CHILDOF>
                    <FETCH>Name,ClosingBalance</FETCH>
                </COLLECTION>
            </TDLMESSAGE>
        </TDL>
    </REQUESTDESC>
</EXPORTDATA>
</BODY>
</ENVELOPE>"""

    try:
        res = requests.post('http://localhost:9000', data=xml, timeout=15)
        print(f'Tally Response Status: {res.status_code}')
        
        clean_text = clean_xml(res.text)
        
        # Extract balances using regex
        debtors = []
        pattern = r'<FNAME>([^<]+)</FNAME>\s*<FBALANCE>([^<]*)</FBALANCE>'
        for match in re.finditer(pattern, clean_text, re.DOTALL):
            name, balance = match.groups()
            try:
                bal = float(balance.strip()) if balance.strip() else 0.0
            except:
                bal = 0.0
            debtors.append({'name': name, 'balance': bal})
        
        print(f'Found {len(debtors)} Sundry Debtors with balances')
        return debtors
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
        return []


def fetch_sundry_creditors_with_balance():
    """Fetch Sundry Creditors with closing balance from Tally."""
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
                <REPORT NAME="CreditorBalances">
                    <FORMS>CreditorForm</FORMS>
                </REPORT>
                <FORM NAME="CreditorForm">
                    <PARTS>CreditorPart</PARTS>
                </FORM>
                <PART NAME="CreditorPart">
                    <LINES>CreditorLine</LINES>
                    <REPEAT>CreditorLine:CreditorsColl</REPEAT>
                </PART>
                <LINE NAME="CreditorLine">
                    <FIELDS>FName,FBalance</FIELDS>
                </LINE>
                <FIELD NAME="FName">
                    <SET>$Name</SET>
                </FIELD>
                <FIELD NAME="FBalance">
                    <SET>$ClosingBalance</SET>
                </FIELD>
                <COLLECTION NAME="CreditorsColl">
                    <TYPE>Ledger</TYPE>
                    <CHILDOF>Sundry Creditors</CHILDOF>
                    <FETCH>Name,ClosingBalance</FETCH>
                </COLLECTION>
            </TDLMESSAGE>
        </TDL>
    </REQUESTDESC>
</EXPORTDATA>
</BODY>
</ENVELOPE>"""

    try:
        res = requests.post('http://localhost:9000', data=xml, timeout=15)
        
        clean_text = clean_xml(res.text)
        
        creditors = []
        pattern = r'<FNAME>([^<]+)</FNAME>\s*<FBALANCE>([^<]*)</FBALANCE>'
        for match in re.finditer(pattern, clean_text, re.DOTALL):
            name, balance = match.groups()
            try:
                bal = float(balance.strip()) if balance.strip() else 0.0
            except:
                bal = 0.0
            creditors.append({'name': name, 'balance': bal})
        
        print(f'Found {len(creditors)} Sundry Creditors with balances')
        return creditors
        
    except Exception as e:
        print(f'Error: {e}')
        return []


def update_balances(debtors, creditors):
    """Update ledger balances in database."""
    db = next(get_db())
    
    updated = 0
    
    # Update debtors
    for d in debtors:
        ledger = db.query(Ledger).filter(Ledger.name == d['name']).first()
        if ledger:
            ledger.closing_balance = d['balance']
            updated += 1
            print(f"  Updated {d['name']}: {d['balance']}")
    
    # Update creditors
    for c in creditors:
        ledger = db.query(Ledger).filter(Ledger.name == c['name']).first()
        if ledger:
            ledger.closing_balance = c['balance']
            updated += 1
            print(f"  Updated {c['name']}: {c['balance']}")
    
    db.commit()
    print(f'\nTotal balances updated: {updated}')
    
    # Show final state
    print('\nSundry Debtors (Receivables):')
    for l in db.query(Ledger).filter(Ledger.parent == 'Sundry Debtors').all():
        print(f'  {l.name}: {l.closing_balance}')
    
    print('\nSundry Creditors (Payables):')
    for l in db.query(Ledger).filter(Ledger.parent == 'Sundry Creditors').all():
        print(f'  {l.name}: {l.closing_balance}')


if __name__ == "__main__":
    print("=" * 50)
    print("FETCHING LEDGER BALANCES FROM TALLY")
    print("=" * 50)
    
    debtors = fetch_sundry_debtors_with_balance()
    creditors = fetch_sundry_creditors_with_balance()
    
    print("\n" + "=" * 50)
    print("UPDATING DATABASE")
    print("=" * 50)
    update_balances(debtors, creditors)
