import sys
sys.path.append('.')

from backend.tally_connector import TallyConnector
import logging

logging.basicConfig(level=logging.DEBUG)

# Test if sanitization is working
tc = TallyConnector("http://localhost:9000", company_name="SHREE JI SALES")

print("=" * 60)
print("TESTING XML SANITIZATION")
print("=" * 60)

xml_request = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY>
    <EXPORTDATA>
        <REQUESTDESC>
            <REPORTNAME>Ledger</REPORTNAME>
            <STATICVARIABLES>
                <SVCURRENTCOMPANY>SHREE JI SALES</SVCURRENTCOMPANY>
            </STATICVARIABLES>
        </REQUESTDESC>
    </EXPORTDATA>
</BODY>
</ENVELOPE>"""

print("\n1. Fetching raw XML...")
raw_xml = tc.send_request(xml_request)
print(f"Raw XML length: {len(raw_xml)}")
print(f"First 300 chars: {raw_xml[:300]}")

print("\n2. Sanitizing XML...")
sanitized = TallyConnector._sanitize_xml(raw_xml)
print(f"Sanitized XML length: {len(sanitized)}")
print(f"First 300 chars: {sanitized[:300]}")

print("\n3. Trying to parse...")
import xml.etree.ElementTree as ET
try:
    root = ET.fromstring(sanitized)
    print("✅ XML parsed successfully!")
    
    # Count LEDGER elements
    ledgers = list(root.iter("LEDGER"))
    print(f"Found {len(ledgers)} LEDGER elements")
    
    # Show first ledger
    if ledgers:
        print("\nFirst ledger:")
        for child in ledgers[0]:
            print(f"  {child.tag}: {child.text}")
except Exception as e:
    print(f"❌ Parse failed: {e}")
    
print("\n" + "=" * 60)
