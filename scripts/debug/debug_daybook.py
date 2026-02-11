import requests

def test_daybook_standard():
    print("\n--- TEST: Daybook Standard ---")
    xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Daybook</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <SVFROMDATE>20200401</SVFROMDATE>
                    <SVTODATE>20251231</SVTODATE>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""

    try:
        r = requests.post("http://localhost:9000", data=xml)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print(f"Response Length: {len(r.text)}")
            print(f"Sample: {r.text[:500]}")
            
            # Check fields
            if "PARTYLEDGERNAME" in r.text.upper():
                print("✅ Found PARTYLEDGERNAME")
            else:
                print("❌ Missing PARTYLEDGERNAME (Might be 'LEDGERNAME' in ALLLEDGERENTRIES)")
            
            if "VOUCHERNUMBER" in r.text.upper():
                print("✅ Found VOUCHERNUMBER")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_daybook_standard()
