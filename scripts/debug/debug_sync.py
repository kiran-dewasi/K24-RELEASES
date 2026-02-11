import requests

xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>ODBC Report</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <SVFROMDATE>20230401</SVFROMDATE>
                    <SVTODATE>20260331</SVTODATE>
                </STATICVARIABLES>
                <TDL>
                    <COLLECTION NAME="VoucherList">
                        <TYPE>Voucher</TYPE>
                        <FETCH>Date,VoucherNumber,VoucherTypeName,PartyLedgerName,Amount,Narration,Guide</FETCH>
                    </COLLECTION>
                </TDL>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""

print("Sending request to Tally...")
try:
    r = requests.post("http://localhost:9000", data=xml)
    print(f"Response Status: {r.status_code}")
    print(f"Response Body Snippet:\n{r.text[:2000]}")
except Exception as e:
    print(f"Error: {e}")
