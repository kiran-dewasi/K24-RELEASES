import requests

def dump_jeera():
    # Helper to fetch using collection for better reliability
    xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>ODBC Report</REPORTNAME> 
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                </STATICVARIABLES>
                <TDL>
                    <COLLECTION NAME="MyVouchers">
                        <TYPE>Voucher</TYPE>
                        <FETCH>*, AllInventoryEntries.*, LedgerEntries.*, AllInventoryEntries.BatchAllocations.*</FETCH>
                    </COLLECTION>
                    <REPORT NAME="ODBC Report">
                        <FORMS>ODBC Form</FORMS>
                    </REPORT>
                    <FORM NAME="ODBC Form">
                        <PARTS>ODBC Part</PARTS>
                    </FORM>
                    <PART NAME="ODBC Part">
                        <LINES>ODBC Line</LINES>
                        <REPEAT>ODBC Line : MyVouchers</REPEAT>
                    </PART>
                    <LINE NAME="ODBC Line">
                        <FIELDS>XML Dump</FIELDS>
                    </LINE>
                    <FIELD NAME="XML Dump">
                        <SET>$XML:Voucher</SET> <!-- Dump the full XML representation of the voucher -->
                    </FIELD>
                </TDL>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""

    # Simpler approach: Just ask for Daybook first, sometimes custom TDL fails if not careful
    simple_xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Voucher Register</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT> 
                    <SVFROMDATE>20230401</SVFROMDATE>
                    <SVTODATE>20260331</SVTODATE>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""

    try:
        print("Sending request to Tally...")
        # Let's try the simple one first as it's less prone to syntax errors if TDL is strict
        r = requests.post("http://localhost:9000", data=simple_xml)
        
        with open("backend/full_dump.xml", "w", encoding="utf-8") as f:
            f.write(r.text)
            
        print(f"Dump saved to backend/full_dump.xml ({len(r.text)} bytes)")

        if "Super Jeera" in r.text:
            print("✅ FOUND SUPER JEERA VOUCHER!")
            # Extract the specific voucher block
            start = r.text.find("<VOUCHER")
            # Find the voucher containing super jeera
            # This is a naive search, finding the voucher block surrounding the substring would be better
            # But let's just print the file path for the user to inspect or a snippet.
            
            # Simple snippet extraction
            idx = r.text.find("Super Jeera")
            start_vroch = r.text.rfind("<VOUCHER", 0, idx)
            end_vroch = r.text.find("</VOUCHER>", idx) + 10
            
            if start_vroch != -1 and end_vroch != -1:
                print(r.text[start_vroch:end_vroch])
            else:
                print("Could not isolate voucher block. See full_dump.xml")
        else:
            print("❌ 'Super Jeera' not found in the dump. Check full_dump.xml for what WAS found.")
            print("Snippet of response:")
            print(r.text[:500])

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_jeera()
