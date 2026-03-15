import requests
import re

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

# Use regex since XML includes invalid control chars
items = re.findall(r'<STOCKITEM NAME="([^"]+)"[^>]*>(.*?)</STOCKITEM>', text, re.DOTALL)
for name, content in items:
    if 'JEERA' in name.upper():
        unit_match = re.search(r'<BASEUNITS>([^<]+)</BASEUNITS>', content)
        parent_match = re.search(r'<PARENT>([^<]+)</PARENT>', content)
        unit = unit_match.group(1) if unit_match else "None"
        parent = parent_match.group(1) if parent_match else "None"
        print(f"Item: {name}, Parent: {parent}, Base Unit: {unit}")
