import requests

def create_ledger():
    xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>All Masters</REPORTNAME></REQUESTDESC>
    <REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF">
     <LEDGER NAME="Vinayak Enterprises" ACTION="Create">
      <NAME.LIST><NAME>Vinayak Enterprises</NAME></NAME.LIST>
      <PARENT>Sundry Debtors</PARENT>
      <ISBILLWISEON>Yes</ISBILLWISEON>
      <AFFECTSSTOCK>No</AFFECTSSTOCK>
     </LEDGER>
    </TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"""
    
    try:
        r = requests.post("http://localhost:9000", data=xml, headers={'Content-Type': 'text/xml; charset=utf-8'})
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_ledger()
