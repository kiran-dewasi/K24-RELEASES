import requests
import datetime

url = "http://localhost:9000"

def get_voucher_xml(date_str):
    # Try a simple Payment voucher: Cash -> Cash (or just a dummy structure)
    # If the date is invalid, Tally errors out before validating ledgers.
    return f"""<ENVELOPE>
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
                    <VOUCHER VCHTYPE="Payment" ACTION="Create" OBJVIEW="Accounting Voucher View">
                        <DATE>{date_str}</DATE>
                        <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
                        <PARTYLEDGERNAME>Cash</PARTYLEDGERNAME>
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Cash</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-1</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""

def probe():
    dates_to_test = [
        "20240401", # Start 24-25
        "20250331", # End 24-25
        "20250401", # Start 25-26
        "20250430", # User tried this (Apr 30 25)
        "20251216", # Today
        "20260331", # End 25-26
    ]

    print("--- 🕵️ Tally Date Probe ---")
    print(f"Target: {url}")
    print("Checking which dates are accepted by the Active Company...\n")

    for d in dates_to_test:
        friendly_d = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        xml = get_voucher_xml(d)
        try:
            resp = requests.post(url, data=xml, headers={'Content-Type': 'application/xml'}, timeout=3)
            if "Out of Range" in resp.text:
                print(f"❌ {friendly_d}: OUT OF RANGE")
            elif "<CREATED>1</CREATED>" in resp.text:
                print(f"✅ {friendly_d}: ACCEPTED (Voucher Created)")
            elif "LineError" in resp.text:
                 # Some other error means Date was OK!
                print(f"⚠️ {friendly_d}: Date OK, but other error: {resp.text.split('<LINEERROR>')[1].split('</LINEERROR>')[0]}")
            else:
                print(f"❓ {friendly_d}: Unknown Response: {resp.text[:100]}")
        except Exception as e:
            print(f"💀 Connection Error: {e}")
            break

if __name__ == "__main__":
    probe()
