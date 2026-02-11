
import sys
import asyncio
from html import escape
from backend.tally_connector import TallyConnector

async def debug():
    tally = TallyConnector()
    ledger_name = "K PRA FOODS PRIVATE LIMITED"
    cname = tally.company_name or "SHREEJI SALES CORPORATION"
    
    print(f"Querying Monthly Summary for: {ledger_name}")

    xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Ledger Monthly Summary</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <LEDGERNAME>{escape(ledger_name)}</LEDGERNAME>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""

    print("Sending Request...")
    resp_xml = tally.send_request(xml)
    print("\n--- RAW XML RESPONSE (First 2000 chars) ---")
    print(resp_xml[:2000])

if __name__ == "__main__":
    asyncio.run(debug())
