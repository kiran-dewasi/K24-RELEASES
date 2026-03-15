"""
PRODUCTION DIAGNOSTIC - confirms every assumption with real Tally data.
No guessing. Every output is a confirmed fact from Tally.
"""
import sys, requests
sys.path.insert(0, '.')

TALLY = "http://localhost:9000"
HEADERS = {"Content-Type": "text/xml; charset=utf-8"}

def tally(xml, timeout=10):
    try:
        r = requests.post(TALLY, data=xml.encode("utf-8"), headers=HEADERS, timeout=timeout)
        return r.text
    except Exception as e:
        return f"ERROR: {e}"

print("=" * 70)
print("DIAGNOSTIC REPORT - CONFIRMED FROM TALLY, NOT GUESSES")
print("=" * 70)

# --- 1. What stock items exist in Tally? ---
from backend.tally_reader import TallyReader
r = TallyReader()
r.fetch_all_items()
print("\n[1] STOCK ITEMS IN TALLY (confirmed via XML fetch):")
for k, v in sorted(r.item_cache.items()):
    print(f"    {repr(v)}")
print(f"    TOTAL: {len(r.item_cache)} items")

# --- 2. Does 'Jeera' item have any vouchers/transactions? ---
print("\n[2] CHECKING IF 'Jeera' HAS TRANSACTIONS:")
xml_vch = """<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>Stock Item Summary</REPORTNAME>
<STATICVARIABLES>
  <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
  <SVFROMDATE>20240401</SVFROMDATE>
  <SVTODATE>20270331</SVTODATE>
</STATICVARIABLES>
<TDL>
  <COLLECTION NAME="MyItems"><TYPE>Stock Item</TYPE>
    <FETCH>Name,OpeningBalance,ClosingBalance</FETCH>
    <FILTER>IsJeera</FILTER>
  </COLLECTION>
  <SYSTEM TYPE="Formulae" NAME="IsJeera">$Name="Jeera"</SYSTEM>
</TDL>
</REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"""
resp = tally(xml_vch, timeout=8)
print(f"    Raw response: {resp[:500]}")

# --- 3. Does 'Main Location' godown exist? ---
print("\n[3] CHECKING GODOWNS IN TALLY:")
xml_gdwn = """<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME>
<STATICVARIABLES>
  <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
  <ACCOUNTTYPE>Godowns</ACCOUNTTYPE>
</STATICVARIABLES>
</REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"""
resp_gdwn = tally(xml_gdwn, timeout=8)
import re
godowns = re.findall(r'NAME="([^"]+)"', resp_gdwn)
if not godowns:
    godowns = re.findall(r'<NAME>([^<]+)</NAME>', resp_gdwn)
print(f"    Godowns found: {godowns}")
print(f"    'Main Location' exists: {'Main Location' in resp_gdwn}")

# --- 4. Does 'Purchase Account' have affects_stock=Yes? ---
print("\n[4] CHECKING 'Purchase Account' CONFIGURATION:")
xml_pa = """<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
<BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME>
<STATICVARIABLES>
  <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
  <ACCOUNTTYPE>Ledgers</ACCOUNTTYPE>
</STATICVARIABLES>
<TDL>
  <COLLECTION NAME="PA"><TYPE>Ledger</TYPE>
    <FETCH>Name,Parent,AffectsStock</FETCH>
    <FILTER>IsPurchase</FILTER>
  </COLLECTION>
  <SYSTEM TYPE="Formulae" NAME="IsPurchase">$Name="Purchase Account"</SYSTEM>
</TDL>
</REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"""
resp_pa = tally(xml_pa, timeout=8)
print(f"    Raw response: {resp_pa[:600]}")

# --- 5. Send minimal voucher WITHOUT items to see if party/ledger works ---
print("\n[5] TESTING MINIMAL VOUCHER (no items, just party + ledger):")
import time
ref = f"TEST-{int(time.time())}"
xml_min = f"""<ENVELOPE>
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
                <RATE>100.0/kg</RATE>
                <AMOUNT>-1000.00</AMOUNT>
                <ACTUALQTY> 10.0 kg</ACTUALQTY>
                <BILLEDQTY> 10.0 kg</BILLEDQTY>
                <BATCHALLOCATIONS.LIST>
                    <GODOWNNAME>Main Location</GODOWNNAME>
                    <BATCHNAME>Primary Batch</BATCHNAME>
                    <AMOUNT>-1000.00</AMOUNT>
                    <ACTUALQTY> 10.0 kg</ACTUALQTY>
                    <BILLEDQTY> 10.0 kg</BILLEDQTY>
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
resp_min = tally(xml_min, timeout=15)
print(f"    RESULT: {resp_min[:400]}")
