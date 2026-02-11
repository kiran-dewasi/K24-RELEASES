
import sys
import asyncio
from html import escape
from backend.tally_connector import TallyConnector

async def debug():
    tally = TallyConnector()
    ledger_name = "Ashapuri Provision"
    cname = tally.company_name or "SHREEJI SALES CORPORATION"  # Updated based on improved knowledge
    
    print(f"Querying Ledger: {ledger_name} in Company: {cname}")

    xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Ledger Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <LEDGERNAME>{escape(ledger_name)}</LEDGERNAME>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""

    # Note: Ledger Vouchers report gives transactions. 
    # To get Master data with closing balance, we might use "List of Accounts" filtered?
    # Or just generic Object fetch?
    # Let's try Object fetch first.
    
    object_xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>List of Accounts</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <ACCOUNTTYPE>Ledgers</ACCOUNTTYPE>
                    <SEARCHKEY>{escape(ledger_name)}</SEARCHKEY> <!-- Filter? Not standard Tally XML tag maybe -->
                     <RPTTXT>{escape(ledger_name)}</RPTTXT> <!-- Sometimes works for filtering -->
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""

    # Better approach: Fetch ALL List of Accounts (filtered by name if possible)
    # Tally doesn't easily support single-item fetch via List of Accounts without TDL.
    # But we can try fetching the specific object directly?
    
    # Let's try the TDL query to get Closing Balance of this specific ledger
    tdl_xml = f"""<ENVELOPE>
        <HEADER>
            <TALLYREQUEST>Export Data</TALLYREQUEST>
        </HEADER>
        <BODY>
            <EXPORTDATA>
                <REQUESTDESC>
                    <REPORTNAME>ODBC Report</REPORTNAME>
                    <STATICVARIABLES>
                        <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                    </STATICVARIABLES>
                </REQUESTDESC>
            </EXPORTDATA>
            <TDL>
                <TDLMESSAGE>
                    <REPORT NAME="ODBC Report">
                        <FORMS>ODBC Form</FORMS>
                    </REPORT>
                    <FORM NAME="ODBC Form">
                        <PARTS>ODBC Part</PARTS>
                    </FORM>
                    <PART NAME="ODBC Part">
                        <LINES>ODBC Line</LINES>
                        <REPEAT>ODBC Line : ODBC Collection</REPEAT>
                        <SCROLLED>Vertical</SCROLLED>
                    </PART>
                    <LINE NAME="ODBC Line">
                        <FIELDS>Name Field, Parent Field, ClosingBalance Field</FIELDS>
                    </LINE>
                    <FIELD NAME="Name Field">
                        <SET>$Name</SET>
                    </FIELD>
                    <FIELD NAME="Parent Field">
                        <SET>$Parent</SET>
                    </FIELD>
                    <FIELD NAME="ClosingBalance Field">
                        <SET>$ClosingBalance</SET>
                    </FIELD>
                    <COLLECTION NAME="ODBC Collection">
                        <TYPE>Ledger</TYPE>
                        <FILTERS>NameFilter</FILTERS>
                    </COLLECTION>
                    <SYSTEM TYPE="Formulae" NAME="NameFilter">$Name = "{ledger_name}"</SYSTEM>
                </TDLMESSAGE>
            </TDL>
        </BODY>
    </ENVELOPE>"""
    
    print("Sending TDL Request...")
    resp_xml = tally.send_request(tdl_xml)
    print("\n--- RAW XML RESPONSE ---")
    print(resp_xml)

if __name__ == "__main__":
    asyncio.run(debug())
