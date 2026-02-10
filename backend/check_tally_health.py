import requests

def check_tally():
    try:
        xml = "<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Companies</REPORTNAME><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"
        r = requests.post("http://localhost:9000", data=xml, timeout=5)
        if r.status_code == 200:
            print("✅ Tally: Connected")
        else:
            print(f"❌ Tally: Error {r.status_code}")
    except Exception as e:
        print("❌ Tally: Unreachable")

if __name__ == "__main__":
    check_tally()
