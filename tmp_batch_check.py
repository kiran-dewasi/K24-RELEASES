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

try:
    resp = requests.post('http://localhost:9000', data=xml, timeout=5)
    items = re.findall(r'<STOCKITEM NAME=\"([^\"]+)\"[^>]*>(.*?)</STOCKITEM>', resp.text, re.DOTALL)
    for name, content in items:
        if 'JEERA' in name.upper():
            batch = re.search(r'<ISBATCHWISEON>([^<]+)</ISBATCHWISEON>', content)
            print(f"Item: {name}, Batch enabled: {batch.group(1) if batch else 'No tag found'}")
except Exception as e:
    print(f"Error: {e}")
