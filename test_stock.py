import requests
import xml.etree.ElementTree as ET

xml = """<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY>
<EXPORTDATA>
<REQUESTDESC>
<REPORTNAME>Stock Summary</REPORTNAME>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
</STATICVARIABLES>
</REQUESTDESC>
</EXPORTDATA>
</BODY>
</ENVELOPE>"""

r = requests.post('http://localhost:9000', data=xml, timeout=10)
print('Status:', r.status_code)
print('Response preview:', r.text[:3000])
