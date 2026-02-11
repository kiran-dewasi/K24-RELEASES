"""
Raw Tally response dumper - to understand the actual XML structure
"""
import requests

def dump_raw_response():
    """Dump raw response from multiple report types."""
    
    reports = [
        ("Trial Balance", """<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY>
<EXPORTDATA>
    <REQUESTDESC>
        <REPORTNAME>Trial Balance</REPORTNAME>
        <STATICVARIABLES>
            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
    </REQUESTDESC>
</EXPORTDATA>
</BODY>
</ENVELOPE>"""),
        
        ("Day Book", """<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY>
<EXPORTDATA>
    <REQUESTDESC>
        <REPORTNAME>Day Book</REPORTNAME>
        <STATICVARIABLES>
            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
    </REQUESTDESC>
</EXPORTDATA>
</BODY>
</ENVELOPE>"""),
        
        ("List of Ledgers", """<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY>
<EXPORTDATA>
    <REQUESTDESC>
        <REPORTNAME>List of Ledgers</REPORTNAME>
        <STATICVARIABLES>
            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
    </REQUESTDESC>
</EXPORTDATA>
</BODY>
</ENVELOPE>"""),
        
        ("Ledger Vouchers", """<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY>
<EXPORTDATA>
    <REQUESTDESC>
        <REPORTNAME>Ledger Vouchers</REPORTNAME>
        <STATICVARIABLES>
            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
            <LEDGERNAME>SHREE SARNESHWAR TRADING COMPANY</LEDGERNAME>
        </STATICVARIABLES>
    </REQUESTDESC>
</EXPORTDATA>
</BODY>
</ENVELOPE>"""),
    ]
    
    for name, xml in reports:
        print("=" * 70)
        print(f"REPORT: {name}")
        print("=" * 70)
        
        try:
            res = requests.post('http://localhost:9000', data=xml, timeout=15)
            print(f"Status: {res.status_code}")
            print(f"Length: {len(res.text)} chars")
            print("\nFull Response (first 5000 chars):")
            print("-" * 70)
            print(res.text[:5000])
            print("-" * 70)
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n\n")


if __name__ == "__main__":
    dump_raw_response()
