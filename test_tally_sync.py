"""Quick sync of ledgers from Tally to the database."""
import requests
import xml.etree.ElementTree as ET
import re
import sys
sys.path.insert(0, '.')

from backend.database import get_db, Ledger

def clean_xml(xml_string):
    """Remove invalid XML characters and entities."""
    # Remove invalid XML char references
    xml_string = re.sub(r'&#x[0-9A-Fa-f]+;', '', xml_string)
    xml_string = re.sub(r'&#[0-9]+;', '', xml_string)
    # Remove control characters
    xml_string = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xml_string)
    return xml_string


def fetch_ledgers_with_balance():
    """Fetch all ledgers with their balances from Tally."""
    xml = """<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY>
<EXPORTDATA>
    <REQUESTDESC>
        <REPORTNAME>List of Accounts</REPORTNAME>
        <STATICVARIABLES>
            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
            <ACCOUNTTYPE>Ledgers</ACCOUNTTYPE>
        </STATICVARIABLES>
    </REQUESTDESC>
</EXPORTDATA>
</BODY>
</ENVELOPE>"""

    try:
        res = requests.post('http://localhost:9000', data=xml, timeout=15)
        print(f'Tally Response Status: {res.status_code}')
        
        # Clean the XML
        clean_text = clean_xml(res.text)
        
        # Parse XML
        try:
            root = ET.fromstring(clean_text)
        except ET.ParseError as e:
            print(f'XML Parse Error: {e}')
            # Fallback to regex
            ledgers = []
            pattern = r'<LEDGER NAME="([^"]+)"[^>]*>.*?<PARENT>([^<]*)</PARENT>.*?<CLOSINGBALANCE>([^<]*)</CLOSINGBALANCE>'
            for match in re.finditer(pattern, clean_text, re.DOTALL):
                name, parent, balance = match.groups()
                try:
                    bal = float(balance)
                except:
                    bal = 0.0
                ledgers.append({
                    'name': name,
                    'parent': parent,
                    'closing_balance': bal
                })
            print(f'Extracted {len(ledgers)} ledgers using regex fallback')
            return ledgers
        
        ledgers = []
        for ledger_elem in root.iter('LEDGER'):
            name = ledger_elem.get('NAME', '')
            parent = ''
            closing = 0.0
            
            # Get child elements
            for child in ledger_elem:
                if child.tag == 'PARENT':
                    parent = child.text or ''
                elif child.tag == 'CLOSINGBALANCE':
                    try:
                        closing = float(child.text or 0)
                    except:
                        pass
            
            if name:
                ledgers.append({
                    'name': name,
                    'parent': parent,
                    'closing_balance': closing
                })
        
        print(f'Parsed {len(ledgers)} ledgers from Tally')
        return ledgers
        
    except Exception as e:
        print(f'Error fetching from Tally: {e}')
        import traceback
        traceback.print_exc()
        return []


def sync_to_database(ledgers):
    """Sync ledgers to the database."""
    db = next(get_db())
    
    added = 0
    updated = 0
    
    for l in ledgers:
        existing = db.query(Ledger).filter(Ledger.name == l['name']).first()
        
        if existing:
            # Update existing
            existing.parent = l['parent']
            existing.closing_balance = l['closing_balance']
            updated += 1
        else:
            # Add new
            ledger = Ledger(
                name=l['name'],
                parent=l['parent'],
                closing_balance=l['closing_balance'],
                tenant_id="default",
                is_active=True
            )
            db.add(ledger)
            added += 1
    
    db.commit()
    
    print(f'Sync complete: Added {added}, Updated {updated}')
    
    # Show totals
    total = db.query(Ledger).count()
    debtors = db.query(Ledger).filter(Ledger.parent == 'Sundry Debtors').count()
    creditors = db.query(Ledger).filter(Ledger.parent == 'Sundry Creditors').count()
    
    print(f'\nDatabase Totals:')
    print(f'  Total Ledgers: {total}')
    print(f'  Sundry Debtors: {debtors}')
    print(f'  Sundry Creditors: {creditors}')
    
    # Show Sundry Debtors
    print('\nSundry Debtors in DB:')
    for l in db.query(Ledger).filter(Ledger.parent == 'Sundry Debtors').all():
        print(f'  ID {l.id}: {l.name} -> Balance: {l.closing_balance}')


if __name__ == "__main__":
    print("=" * 50)
    print("TALLY TO DATABASE SYNC")
    print("=" * 50)
    
    ledgers = fetch_ledgers_with_balance()
    
    if ledgers:
        print("\nSample ledgers from Tally:")
        for l in ledgers[:10]:
            print(f"  {l['name']} ({l['parent']}) -> {l['closing_balance']}")
        
        print("\n" + "=" * 50)
        print("SYNCING TO DATABASE")
        print("=" * 50)
        sync_to_database(ledgers)
    else:
        print("No ledgers fetched from Tally!")
