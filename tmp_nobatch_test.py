import requests
import time

ref = f"TEST-{int(time.time())}"
xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>
    <REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF">
        <VOUCHER VCHTYPE="Purchase" ACTION="Create" OBJVIEW="Invoice Voucher View">
            <DATE>20260315</DATE>
            <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
            <PARTYLEDGERNAME>VINAYAK ENETRPRISES</PARTYLEDGERNAME>
            <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
            <ISINVOICE>Yes</ISINVOICE>
            <LEDGERENTRIES.LIST>
                <LEDGERNAME>VINAYAK ENETRPRISES</LEDGERNAME>
                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                <AMOUNT>-1000.00</AMOUNT>
                <BILLALLOCATIONS.LIST>
                    <NAME>{ref}</NAME>
                    <BILLTYPE>New Ref</BILLTYPE>
                    <AMOUNT>-1000.00</AMOUNT>
                </BILLALLOCATIONS.LIST>
            </LEDGERENTRIES.LIST>
            <ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>CUMIN SEEDS ( JEERA )</STOCKITEMNAME>
                <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                <RATE>100.0/KGS</RATE>
                <AMOUNT>-1000.00</AMOUNT>
                <ACTUALQTY> 10.0 KGS</ACTUALQTY>
                <BILLEDQTY> 10.0 KGS</BILLEDQTY>
                <BATCHALLOCATIONS.LIST>
                    <GODOWNNAME>Main Location</GODOWNNAME>
                    <AMOUNT>-1000.00</AMOUNT>
                    <ACTUALQTY> 10.0 KGS</ACTUALQTY>
                    <BILLEDQTY> 10.0 KGS</BILLEDQTY>
                </BATCHALLOCATIONS.LIST>
                <ACCOUNTINGALLOCATIONS.LIST>
                    <LEDGERNAME>Purchase Account</LEDGERNAME>
                    <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                    <AMOUNT>-1000.00</AMOUNT>
                </ACCOUNTINGALLOCATIONS.LIST>
            </ALLINVENTORYENTRIES.LIST>
        </VOUCHER>
    </TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY>
</ENVELOPE>"""

try:
    resp = requests.post('http://localhost:9000', data=xml, timeout=10)
    print("STATUS:", resp.status_code)
    print("RESPONSE:", resp.text[:400])
except Exception as e:
    print("Error:", e)
