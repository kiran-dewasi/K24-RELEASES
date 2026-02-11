import requests
import random

url = "http://localhost:9000"

def create_ledger():
    xml = """<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <LEDGER NAME="TestParty" ACTION="Create">
                        <NAME>TestParty</NAME>
                        <PARENT>Sundry Debtors</PARENT>
                        <OPENINGBALANCE>0</OPENINGBALANCE>
                        <ISBILLWISEON>No</ISBILLWISEON>
                    </LEDGER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
    </ENVELOPE>"""
    try:
        resp = requests.post(url, data=xml, headers={'Content-Type': 'application/xml'}, timeout=5)
        if "<CREATED>1</CREATED>" in resp.text or "<IGNORED>1</IGNORED>" in resp.text:
            print("✅ Ledger 'TestParty' Created/Exists")
            return True
        else:
            print(f"❌ Failed to create Ledger: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Ledger Connection Error: {e}")
        return False

def create_voucher():
    vch_no = str(random.randint(1000, 9999))
    xml = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Receipt" ACTION="Create" OBJVIEW="Accounting Voucher View">
                        <DATE>20251216</DATE>
                        <NARRATION>Test Voucher Final Verification {vch_no}</NARRATION>
                        <VOUCHERTYPENAME>Receipt</VOUCHERTYPENAME>
                        <PARTYLEDGERNAME>TestParty</PARTYLEDGERNAME>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>TestParty</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>100</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                         <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Cash</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-100</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""

    print(f"--- Creating Receipt (Date: 2025-12-16) ---")
    try:
        resp = requests.post(url, data=xml, headers={'Content-Type': 'application/xml'}, timeout=5)
        if "<CREATED>1</CREATED>" in resp.text:
            print("✅ SUCCESS: Tally returned CREATED=1")
            print(f"Check Daybook for Dec 16. Look for 'Test Voucher... {vch_no}'")
        else:
            print("❌ FAILURE: Tally response:")
            print(resp.text)
    except Exception as e:
        print(f"💀 Connection Error: {e}")

if __name__ == "__main__":
    if create_ledger():
        create_voucher()
