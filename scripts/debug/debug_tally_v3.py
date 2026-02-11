import requests

def test_minified_daybook():
    print("\n--- TEST: Minified Daybook ---")
    xml = "<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>Daybook</REPORTNAME><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT><SVFROMDATE>20230401</SVFROMDATE><SVTODATE>20260331</SVTODATE></STATICVARIABLES></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"
    
    try:
        r = requests.post("http://localhost:9000", data=xml)
        print(f"Status: {r.status_code}")
        print(f"Length: {len(r.text)}")
        print(f"Snippet: {r.text[:500]}")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test_minified_daybook()
