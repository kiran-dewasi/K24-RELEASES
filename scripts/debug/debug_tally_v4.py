import requests

def test_voucher_register_content():
    print("\n--- TEST: Voucher Register Content ---")
    xml = """<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>Voucher Register</REPORTNAME><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT><SVFROMDATE>20230401</SVFROMDATE><SVTODATE>20260331</SVTODATE></STATICVARIABLES></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"""

    try:
        r = requests.post("http://localhost:9000", data=xml)
        if r.status_code == 200:
            print(f"Length: {len(r.text)}")
            if "VOUCHER" in r.text or "<VOUCHER>" in r.text:
                print("✅ Found VOUCHER tag")
                print("Sample:", r.text[:500])
            else:
                print("❌ No VOUCHER tag found")
                print("Snippet:", r.text[:500])
                
                if "LEDGER" in r.text:
                    print("Found LEDGER tag (Masters Dump?)")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_voucher_register_content()
