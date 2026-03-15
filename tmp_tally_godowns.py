import requests
import re

xml = '''<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME>
<STATICVARIABLES>
  <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
  <ACCOUNTTYPE>Godowns</ACCOUNTTYPE>
</STATICVARIABLES>
</REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>'''

try:
    resp = requests.post('http://localhost:9000', data=xml, timeout=5)
    names = re.findall(r'<NAME>([^<]+)</NAME>', resp.text)
    print("Godowns:", names)
except Exception as e:
    print('Error:', e)
