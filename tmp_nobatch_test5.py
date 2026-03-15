import requests
xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>
    <REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF">
        <VOUCHER VCHTYPE="Purchase" ACTION="Create" OBJVIEW="Accounting Voucher View">
            <DATE>20250315</DATE>
            <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
            <PARTYLEDGERNAME>VINAYAK ENETRPRISES</PARTYLEDGERNAME>
            <PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>
            <ISINVOICE>No</ISINVOICE>
            <LEDGERENTRIES.LIST>
                <LEDGERNAME>VINAYAK ENETRPRISES</LEDGERNAME>
                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                <AMOUNT>-1000.00</AMOUNT>
            </LEDGERENTRIES.LIST>
            <LEDGERENTRIES.LIST>
                <LEDGERNAME>Purchase Account</LEDGERNAME>
                <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                <AMOUNT>-1000.00</AMOUNT>
            </LEDGERENTRIES.LIST>
        </VOUCHER>
    </TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY>
</ENVELOPE>"""

try:
    resp = requests.post('http://localhost:9000', data=xml, timeout=10)
    print("STATUS:", resp.status_code)
    print("RESPONSE:", resp.text)
except Exception as e:
    print("Error:", e)
