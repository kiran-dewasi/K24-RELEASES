import requests

def test_reports():
    names = ["Day Book", "Voucher Register", "VoucherRegister", "Bank Book", "Cash Book"]
    
    for name in names:
        print(f"\n--- TEST: {name} ---")
        xml = f"<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>{name}</REPORTNAME><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT><SVFROMDATE>20230401</SVFROMDATE><SVTODATE>20260331</SVTODATE></STATICVARIABLES></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"
        
        try:
            r = requests.post("http://localhost:9000", data=xml)
            if r.status_code == 200:
                print(f"Length: {len(r.text)}")
                if len(r.text) > 1000:
                     print("✅ Success! Large response.")
                     print("Snippet:", r.text[:200])
                else:
                     print("❌ Small/Empty response")
                     if "Import Data" in r.text:
                         print("Status: Import Data Fallback (Invalid Report)")
        except Exception as e:
            print(e)

if __name__ == "__main__":
    test_reports()
