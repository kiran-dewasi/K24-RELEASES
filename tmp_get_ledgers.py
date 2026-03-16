import requests

def get_ledgers():
    xml = """<ENVELOPE>
<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY><EXPORTDATA><REQUESTDESC>
<REPORTNAME>List of Accounts</REPORTNAME>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
<ACCOUNTTYPE>Ledgers</ACCOUNTTYPE>
</STATICVARIABLES>
</REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>"""
    try:
        resp = requests.post("http://localhost:9000", data=xml, timeout=10)
        with open("ledgers_raw.xml", "wb") as f:
            f.write(resp.content)
        print("Done. Saved to ledgers_raw.xml")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_ledgers()
