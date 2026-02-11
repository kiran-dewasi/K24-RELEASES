from backend.tally_connector import TallyConnector
import xml.etree.ElementTree as ET

t = TallyConnector('http://localhost:9000')

# Fetch vouchers XML
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
print(f"Response length: {len(response)} bytes\n")

# Sanitize XML before parsing
response = TallyConnector._sanitize_xml(response)
print(f"After sanitization: {len(response)} bytes\n")

# Parse XML
root = ET.fromstring(response)
print(f"Root tag: {root.tag}\n")

# Find all TALLYMESSAGE tags
tallymessages = list(root.iter('TALLYMESSAGE'))
print(f"Found {len(tallymessages)} TALLYMESSAGE tags\n")

if tallymessages:
    print("First TALLYMESSAGE structure:")
    msg = tallymessages[0]
    print(f"  Tag: {msg.tag}")
    print(f"  Attributes: {msg.attrib}")
    print(f"  Children ({len(list(msg))} total):")
    for i, child in enumerate(list(msg)[:15]):
        print(f"    {i+1}. {child.tag} = {child.text[:50] if child.text else '(no text)'}")
    
    # Look for VOUCHER tags
    vouchers = msg.findall('VOUCHER')
    print(f"\n  Direct VOUCHER children: {len(vouchers)}")
    
    if vouchers:
        print("\n  First VOUCHER structure:")
        v = vouchers[0]
        print(f"    Attributes: {v.attrib}")
        print(f"    Children ({len(list(v))} total):")
        for i, child in enumerate(list(v)[:20]):
            text = child.text[:30] if child.text and child.text.strip() else '(empty)'
            print(f"      {i+1}. {child.tag} = {text}")

# Also check for REQUESTDATA structure
requestdata = list(root.iter('REQUESTDATA'))
print(f"\n\nFound {len(requestdata)} REQUESTDATA tags")
if requestdata:
    rd = requestdata[0]
    print(f"REQUESTDATA children: {[c.tag for c in list(rd)[:10]]}")
