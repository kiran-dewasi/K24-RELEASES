import requests
import xml.etree.ElementTree as ET

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
root = ET.fromstring(resp.text)
for item in root.findall('.//STOCKITEM'):
    name = item.get('NAME', '')
    if 'JEERA' in name.upper():
        unit = item.find('BASEUNITS')
        parent = item.find('PARENT')
        u_txt = unit.text if unit is not None else "None"
        p_txt = parent.text if parent is not None else "None"
        print(f"Item: {name}, Parent: {p_txt}, Base Unit: {u_txt}")
