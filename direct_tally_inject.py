"""
Direct Tally Injector (Inventory Mode).
Constructs an ITEM INVOICE (Purchase) with Stock Items and Units.
"""
import requests
import datetime

TALLY_URL = "http://localhost:9000"

def post_xml(xml):
    try:
        resp = requests.post(TALLY_URL, data=xml)
        if hasattr(resp, 'text'):
            if "<CREATED>1</CREATED>" in resp.text or "<ALTERED>1</ALTERED>" in resp.text:
                return True, resp.text
            else:
                return False, resp.text
    except Exception as e:
        return False, str(e)

def create_unit(name):
    print(f"Creating Unit: {name}...")
    xml = f"""<ENVELOPE>
        <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
        <BODY><IMPORTDATA>
            <REQUESTDESC><REPORTNAME>All Masters</REPORTNAME></REQUESTDESC>
            <REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF">
                <UNIT NAME="{name}" ACTION="Create">
                    <NAME>{name}</NAME>
                    <ISSIMPLEUNIT>Yes</ISSIMPLEUNIT>
                </UNIT>
            </TALLYMESSAGE></REQUESTDATA>
        </IMPORTDATA></BODY>
    </ENVELOPE>"""
    success, _ = post_xml(xml)
    if success: print(" -> Unit OK.")
    else: print(" -> Unit Failed (might exist).")

def create_stock_item(name, unit):
    print(f"Creating Stock Item: {name} ({unit})...")
    xml = f"""<ENVELOPE>
        <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
        <BODY><IMPORTDATA>
            <REQUESTDESC><REPORTNAME>All Masters</REPORTNAME></REQUESTDESC>
            <REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF">
                <STOCKITEM NAME="{name}" ACTION="Create">
                    <NAME.LIST><NAME>{name}</NAME></NAME.LIST>
                    <PARENT></PARENT>
                    <BASEUNITS>{unit}</BASEUNITS>
                    <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>
                </STOCKITEM>
            </TALLYMESSAGE></REQUESTDATA>
        </IMPORTDATA></BODY>
    </ENVELOPE>"""
    success, resp_text = post_xml(xml)
    if success: print(" -> Item OK.")
    else: print(f" -> Item Failed: {resp_text}")

def create_ledger(name, parent="Sundry Creditors"):
    print(f"Creating Ledger: {name}...")
    xml = f"""<ENVELOPE>
        <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
        <BODY><IMPORTDATA>
            <REQUESTDESC><REPORTNAME>All Masters</REPORTNAME></REQUESTDESC>
            <REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF">
                <LEDGER NAME="{name}" ACTION="Create">
                    <NAME.LIST><NAME>{name}</NAME></NAME.LIST>
                    <PARENT>{parent}</PARENT>
                </LEDGER>
            </TALLYMESSAGE></REQUESTDATA>
        </IMPORTDATA></BODY>
    </ENVELOPE>"""
    post_xml(xml)

def push_inventory_voucher():
    print(f"\nPushing INVENTORY Voucher to {TALLY_URL}...")
    
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    party = "Ramesh Traders"
    item_name = "PVC Pipe 4inch"
    unit = "Nos"
    qty = 10
    rate = 500
    amount = qty * rate # 5000
    
    # 1. Setup Masters
    create_ledger(party, "Sundry Creditors")
    create_ledger("Purchase Account", "Purchase Accounts")
    create_unit(unit)
    create_stock_item(item_name, unit)
    
    # 2. Build Inventory XML
    xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC><REPORTNAME>All Masters</REPORTNAME></REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Purchase" ACTION="Create" OBJVIEW="Invoice Voucher View">
                        <DATE>{date_str}</DATE>
                        <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
                        <PARTYLEDGERNAME>{party}</PARTYLEDGERNAME>
                        <NARRATION>Item Invoice Auto-posted</NARRATION>
                        <FBTPAYMENTTYPE>Default</FBTPAYMENTTYPE>
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        <VCHENTRYMODE>Item Invoice</VCHENTRYMODE>

                        <ALLINVENTORYENTRIES.LIST>
                            <STOCKITEMNAME>{item_name}</STOCKITEMNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <RATE>{rate}/{unit}</RATE>
                            <AMOUNT>-{amount}.00</AMOUNT>
                            <ACTUALQTY> {qty} {unit}</ACTUALQTY>
                            <BILLEDQTY> {qty} {unit}</BILLEDQTY>
                            
                            <BATCHALLOCATIONS.LIST>
                                <GODOWNNAME>Main Location</GODOWNNAME>
                                <BATCHNAME>Primary Batch</BATCHNAME>
                                <AMOUNT>-{amount}.00</AMOUNT>
                                <ACTUALQTY> {qty} {unit}</ACTUALQTY>
                                <BILLEDQTY> {qty} {unit}</BILLEDQTY>
                            </BATCHALLOCATIONS.LIST>
                            
                            <ACCOUNTINGALLOCATIONS.LIST>
                                <LEDGERNAME>Purchase Account</LEDGERNAME>
                                <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                                <AMOUNT>-{amount}.00</AMOUNT>
                            </ACCOUNTINGALLOCATIONS.LIST>
                        </ALLINVENTORYENTRIES.LIST>
                        
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{party}</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{amount}.00</AMOUNT>
                        </LEDGERENTRIES.LIST>
                        
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
    </ENVELOPE>"""
    
    print("\nSending XML...")
    success, resp_text = post_xml(xml)
    
    if success:
        print("\nSUCCESS! Inventory Voucher Created.")
        print(f"Check Tally for '{item_name}' x {qty} {unit}")
    else:
        print("\nFAILURE!")
        print(resp_text)

if __name__ == "__main__":
    push_inventory_voucher()
