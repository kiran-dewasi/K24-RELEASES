from backend.tally_connector import TallyConnector
import xml.etree.ElementTree as ET

t = TallyConnector('http://localhost:9000')

xml_request = '''<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY>
<EXPORTDATA>
<REQUESTDESC>
<REPORTNAME>Voucher Register</REPORTNAME>
<STATICVARIABLES>
<SVCURRENTCOMPANY>SHREE JI SALES</SVCURRENTCOMPANY>
</STATICVARIABLES>
</REQUESTDESC>
</EXPORTDATA>
</BODY>
</ENVELOPE>'''

response = t.send_request(xml_request)
response = TallyConnector._sanitize_xml(response)
root = ET.fromstring(response)

# Get all vouchers
vouchers = list(root.iter('VOUCHER'))
print(f"Total vouchers found: {len(vouchers)}\n")

for i, voucher in enumerate(vouchers):
    print(f"=== VOUCHER {i+1} ===")
    print(f"Type: {voucher.attrib.get('VCHTYPE', 'Unknown')}")
    
    # Get DATE
    date_elem = voucher.find('DATE')
    if date_elem is not None and date_elem.text:
        print(f"Date: {date_elem.text}")
    
    # Get VOUCHERNUMBER
    vch_num = voucher.find('VOUCHERNUMBER')
    if vch_num is not None and vch_num.text:
        print(f"Voucher Number: {vch_num.text}")
    
    # Get ledger entries
    ledgers = voucher.findall('.//ALLLEDGERENTRIES.LIST')
    print(f"Ledger Entries: {len(ledgers)}")
    
    for j, ledger in enumerate(ledgers):
        print(f"\n  Ledger Entry {j+1}:")
        # Get ledger name
        ledger_name = ledger.find('LEDGERNAME')
        if ledger_name is not None and ledger_name.text:
            print(f"    Ledger: {ledger_name.text}")
        
        # Get amount
        amount = ledger.find('AMOUNT')
        if amount is not None and amount.text:
            print(f"    Amount: {amount.text}")
        
        # Check for ISDEEMEDPOSITIVE
        deemed_pos = ledger.find('ISDEEMEDPOSITIVE')
        if deemed_pos is not None and deemed_pos.text:
            print(f"    Is Deemed Positive: {deemed_pos.text}")
    
    print("\n")
