import requests

xml = '''<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME>
<STATICVARIABLES>
    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
    <ACCOUNTTYPE>Stock Items</ACCOUNTTYPE> 
</STATICVARIABLES>
</REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>'''

resp = requests.post('http://localhost:9000', data=xml, timeout=5)
text = resp.text

import re
import xml.etree.ElementTree as ET

# Clean Tally proprietary garbage at the start if it exists
if not text.lstrip().startswith('<'):
    text = text[text.find('<'):]

try:
    root = ET.fromstring(text)
    for item in root.findall('.//STOCKITEM'):
        name = item.get('NAME') or item.findtext('NAME')
        if name and 'JEERA' in name.upper():
            unit = item.find('BASEUNITS')
            parent = item.find('PARENT')
            u_txt = unit.text if unit is not None else "None"
            p_txt = parent.text if parent is not None else "None"
            print(f"Item: {name}, Parent: {p_txt}, Base Unit: {u_txt}")
except Exception as e:
    print("FAILED TO PARSE XML.", e)
    print("RESPONSE HEAD:", text[:200])
