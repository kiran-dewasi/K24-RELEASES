import requests

def test_tallyscql():
    print("\n--- TEST: Tally SQL ---")
    xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>ODBC Report</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                </STATICVARIABLES>
                <SQLREQUEST TYPE="General">
                    <SQLQUERY>SELECT $Date, $VoucherNumber, $PartyLedgerName, $Amount, $Narration FROM Voucher</SQLQUERY>
                </SQLREQUEST>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""

    try:
        r = requests.post("http://localhost:9000", data=xml)
        print(f"Status: {r.status_code}")
        print(f"Size: {len(r.text)}")
        print(f"Snippet: {r.text[:500]}")
        if "PartyLedgerName" in r.text or "PARTYLEDGERNAME" in r.text:
            print("✅ SQL Success")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_tallyscql()
