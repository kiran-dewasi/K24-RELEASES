"""Test Tally Response"""
import requests

xml = '''<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME>
<STATICVARIABLES>
    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
    <ACCOUNTTYPE>Groups</ACCOUNTTYPE> 
</STATICVARIABLES>
</REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>'''

try:
    print('Testing Tally connectivity...')
    resp = requests.post('http://localhost:9000', data=xml, timeout=5)
    print(f'STATUS: {resp.status_code}')
    print('Tally is responding!')
except Exception as e:
    print(f'ERROR: Tally is NOT responding. Details: {type(e).__name__} - {e}')
