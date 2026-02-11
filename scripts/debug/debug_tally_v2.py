import requests
import xml.etree.ElementTree as ET

def clean_xml(xml_string):
    return xml_string.strip()

def test_daybook_enhanced():
    print("\n--- TEST: Daybook with Injected Fields ---")
    xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Daybook</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <SVFROMDATE>20200401</SVFROMDATE>
                    <SVTODATE>20251231</SVTODATE>
                </STATICVARIABLES>
                <TDL>
                    <OBJECT NAME="Voucher">
                        <FETCH>Date,VoucherNumber,VoucherTypeName,PartyLedgerName,Amount,Narration</FETCH>
                    </OBJECT>
                </TDL>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
    
    try:
        r = requests.post("http://localhost:9000", data=xml)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print(f"Response Length: {len(r.text)}")
            print(f"Sample: {r.text[:500]}")
            
            # Check for fields
            if "PARTYLEDGERNAME" in r.text.upper():
                print("✅ Found PARTYLEDGERNAME")
            else:
                print("❌ Missing PARTYLEDGERNAME")
                
            if "AMOUNT" in r.text.upper():
                print("✅ Found AMOUNT")
            else:
                print("❌ Missing AMOUNT")
    except Exception as e:
        print(f"Error: {e}")

def test_ledgers_enhanced():
    print("\n--- TEST: Ledgers with Injected Fields ---")
    xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>List of Accounts</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <ACCOUNTTYPE>Ledgers</ACCOUNTTYPE>
                </STATICVARIABLES>
                <TDL>
                    <OBJECT NAME="Ledger">
                        <FETCH>Name,Parent,ClosingBalance,PartyGSTIN,Email,LedgerMobile</FETCH>
                    </OBJECT>
                </TDL>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
    
    try:
        r = requests.post("http://localhost:9000", data=xml)
        if r.status_code == 200:
            print(f"Response Length: {len(r.text)}")
            if "PARTYGSTIN" in r.text.upper():
                print("✅ Found PARTYGSTIN")
            else:
                print("❌ Missing PARTYGSTIN")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_daybook_enhanced()
    test_ledgers_enhanced()
