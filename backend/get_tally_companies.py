"""
Get actual company names from Tally using proper TDL Collection
"""
import requests

# TDL-based request to get all open companies
xml = '''<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>Export</TALLYREQUEST>
<TYPE>Collection</TYPE>
<ID>CompanyList</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES></STATICVARIABLES>
<TDL>
<TDLMESSAGE>
<COLLECTION NAME="CompanyList">
<TYPE>Company</TYPE>
<FETCH>Name, FormalName, CompanyNumber</FETCH>
</COLLECTION>
</TDLMESSAGE>
</TDL>
</DESC>
</BODY>
</ENVELOPE>'''

print("Fetching company list from Tally using TDL Collection...")
response = requests.post("http://localhost:9000", data=xml, timeout=30)
print(f"Response:\n{response.text}")

# Also try the simpler method
print("\n" + "="*50)
print("Trying simpler method - Active Company...")

xml2 = '''<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>Export</TALLYREQUEST>
<TYPE>Data</TYPE>
<ID>Company</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
</STATICVARIABLES>
</DESC>
</BODY>
</ENVELOPE>'''

response2 = requests.post("http://localhost:9000", data=xml2, timeout=30)
print(f"Response:\n{response2.text[:3000]}")
