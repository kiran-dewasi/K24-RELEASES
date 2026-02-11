import requests
import os
from datetime import datetime

# Configuration
TALLY_URL = "http://localhost:9000"
COMPANY = "SHREE JI SALES"

def send_xml(xml):
    try:
        headers = {"Content-Type": "application/xml"}
        response = requests.post(TALLY_URL, data=xml, headers=headers)
        return response.text
    except Exception as e:
        return str(e)

def check_connection():
    print(f"Checking connection to {TALLY_URL}...")
    # Request to list all companies
    xml = """<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Companies</REPORTNAME><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"""
    response = send_xml(xml)
    print("Full Response:")
    print(response)
    if "SHREE JI SALES" in response:
        print("✅ Company 'SHREE JI SALES' found!")
        return True
    else:
        print("⚠️ 'SHREE JI SALES' not found in response. Check open companies.")
        return False

def create_test_receipt(party_name, amount, date_str):
    print(f"\nAttempting to create receipt for {party_name} on {date_str}...")
    
    # 1. Create Ledger First (Just in case)
    ledger_xml = f"""<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>All Masters</REPORTNAME><STATICVARIABLES><SVCURRENTCOMPANY>{COMPANY}</SVCURRENTCOMPANY></STATICVARIABLES></REQUESTDESC><REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF"><LEDGER NAME="{party_name}" ACTION="Create"><NAME.LIST TYPE="String"><NAME>{party_name}</NAME></NAME.LIST><PARENT>Sundry Debtors</PARENT></LEDGER></TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"""
    print("Creating Ledger...")
    print(send_xml(ledger_xml))

    # 2. Create Voucher
    voucher_xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{COMPANY}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER ACTION="Create">
                        <DATE>{date_str}</DATE>
                        <VOUCHERTYPENAME>Receipt</VOUCHERTYPENAME>
                        <NARRATION>Debug Test</NARRATION>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>{party_name}</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>-{amount}</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Cash</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>{amount}</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
    </ENVELOPE>"""
    
    print("\nPushing Voucher...")
    response = send_xml(voucher_xml)
    print("Response:")
    print(response)

if __name__ == "__main__":
    print("--- STARTING DIRECT TEST ---")
    # Skip check_connection() since we know Tally is reachable (returned error previously)
    
    # Try 1: Current Year (2025)
    create_test_receipt("DebugUser2025", 100, "20251101")
    
    print("-" * 50)
    
    # Try 2: Previous Year (2024)
    create_test_receipt("DebugUser2024", 100, "20240401")
