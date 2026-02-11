
import sys
import asyncio
from html import escape
from backend.tally_connector import TallyConnector

async def debug():
    tally = TallyConnector()
    group_name = "Sundry Debtors"
    cname = tally.company_name or "SHREE JI SALES" # Fallback or use what connector uses
    if not cname:
        # Try to guess or just use generic if connector has default
        from backend.tally_connector import DEFAULT_COMPANY
        cname = DEFAULT_COMPANY
        
    print(f"Using Company: {cname}")

    xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Group Summary</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <GROUPNAME>{escape(group_name)}</GROUPNAME>

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
