
import sys
import asyncio
from html import escape
from backend.tally_connector import TallyConnector

async def debug():
    tally = TallyConnector()
    cname = tally.company_name or "SHREEJI SALES CORPORATION"
    
    print(f"Fetching List of Accounts for Company: {cname}")

    xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>List of Accounts</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <ACCOUNTTYPE>Ledgers</ACCOUNTTYPE>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""

    print("Sending Request...")
    resp_xml = tally.send_request(xml)
    
    # Save to file to grep
    with open("debug_all_ledgers.xml", "w", encoding="utf-8") as f:
        f.write(resp_xml)
    
    print("Saved to debug_all_ledgers.xml")

if __name__ == "__main__":
    asyncio.run(debug())
