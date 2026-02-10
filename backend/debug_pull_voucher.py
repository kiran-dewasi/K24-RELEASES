import requests
import datetime

def get_vouchers():
    xml = """<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Export Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Day Book</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <SVFROMDATE>20240401</SVFROMDATE>
                    <SVTODATE>20251219</SVTODATE>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""

    print("Sending Day Book Request to Tally for XML Dump...")
    try:
        r = requests.post("http://localhost:9000", data=xml)
        r.raise_for_status()
        with open("backend/voucher_dump.xml", "w", encoding="utf-8") as f:
            f.write(r.text)
        print("Dumped to backend/voucher_dump.xml")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_vouchers()
