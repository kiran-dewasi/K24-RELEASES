
import sys
import asyncio
from html import escape
from backend.tally_connector import TallyConnector

async def debug():
    tally = TallyConnector()
    cname = tally.company_name or "SHREEJI SALES CORPORATION"
    
    print(f"Fetching Bills Outstanding for: {cname}")

    xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Bills Receivable</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""

    print("Sending Request...")
    resp_xml = tally.send_request(xml)
    
    print("\n--- RAW XML RESPONSE (First 5000 chars) ---")
    print(resp_xml[:5000])

if __name__ == "__main__":
    asyncio.run(debug())
