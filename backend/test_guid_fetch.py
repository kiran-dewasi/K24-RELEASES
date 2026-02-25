import requests
import re
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

cname = 'SHREEJI SALES CORPORATION'
# GUID of Sales #55 (Jan 28 2026, VINAYAK) from our local DB
guid = 'd3b3ef8c-95f5-4294-923d-ab7b57a5de98-000000b5'

xml_body = f"""<ENVELOPE>
  <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
  <BODY><EXPORTDATA><REQUESTDESC>
    <REPORTNAME>VchByGUID</REPORTNAME>
    <STATICVARIABLES>
      <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
      <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
    </STATICVARIABLES>
    <TDL><TDLMESSAGE>
      <COLLECTION NAME="VchByGUID">
        <TYPE>Voucher</TYPE>
        <FILTER>ByGUID</FILTER>
        <FETCH>Date,VoucherNumber,VoucherTypeName,PartyLedgerName,Narration,GUID,AllLedgerEntries,AllInventoryEntries,InventoryEntries,InventoryEntriesIn,InventoryEntriesOut</FETCH>
      </COLLECTION>
      <SYSTEM TYPE="Formulae" NAME="ByGUID">$GUID = "{guid}"</SYSTEM>
    </TDLMESSAGE></TDL>
  </REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"""

print(f"Fetching voucher by GUID: {guid}")
try:
    r = requests.post('http://localhost:9000', data=xml_body.encode('utf-8'), timeout=15)
    print(f"Status: {r.status_code}")
    raw = r.text
    print(f"\nFirst 2000 chars:\n{raw[:2000]}")

    # Try to parse
    cleaned = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;)', '&amp;', raw)
    try:
        root = ET.fromstring(cleaned)
        all_v = root.findall('.//VOUCHER')
        print(f"\n==> Found {len(all_v)} VOUCHER nodes")
        for v in all_v:
            vnum  = v.findtext('VOUCHERNUMBER') or 'NO-NUM'
            vtype = v.findtext('VOUCHERTYPENAME') or v.get('VCHTYPE', 'NO-TYPE')
            vdate = v.findtext('DATE') or 'NO-DATE'
            vparty = v.findtext('PARTYLEDGERNAME') or 'NO-PARTY'
            vguid  = v.findtext('GUID') or 'NO-GUID'
            inv_tags = ['ALLINVENTORYENTRIES.LIST', 'INVENTORYENTRIES.LIST',
                        'INVENTORYENTRIESIN.LIST', 'INVENTORYENTRIESOUT.LIST']
            inv_count = sum(len(v.findall(t)) for t in inv_tags)
            led_tags = ['ALLLEDGERENTRIES.LIST', 'LEDGERENTRIES.LIST']
            led_count = sum(len(v.findall(t)) for t in led_tags)
            print(f"  VCH #{vnum} | {vtype} | {vdate} | {vparty}")
            print(f"      GUID={vguid}")
            print(f"      Inventory entries: {inv_count}, Ledger entries: {led_count}")
            # Show inventory items
            for tag in inv_tags:
                for inv in v.findall(tag):
                    item = inv.findtext('STOCKITEMNAME') or '?'
                    qty  = inv.findtext('ACTUALQTY') or inv.findtext('BILLEDQTY') or '?'
                    rate = inv.findtext('RATE') or '?'
                    amt  = inv.findtext('AMOUNT') or '?'
                    print(f"      ITEM: {item} | qty={qty} | rate={rate} | amt={amt}")
            # Show ledger entries
            for tag in led_tags:
                for led in v.findall(tag):
                    lname = led.findtext('LEDGERNAME') or '?'
                    lamt  = led.findtext('AMOUNT') or '?'
                    print(f"      LED: {lname} | {lamt}")
    except ET.ParseError as pe:
        print(f"XML parse error: {pe}")
        print("Raw response saved. Check manually.")
except Exception as e:
    print(f"Connection error: {e}")
