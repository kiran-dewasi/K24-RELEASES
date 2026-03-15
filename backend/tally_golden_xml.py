"""
Tally Golden XML Builder
========================
This module generates XML that matches EXACTLY the golden XML structure
found in tests/golden_xml/all_vouchers_dump.xml

All voucher types follow the same proven format that works with Tally.
Reference: tests/golden_xml/all_vouchers_dump.xml

Author: K24.ai
Version: 1.0.0
"""

import uuid
import datetime
from typing import Dict, List, Any, Optional
from xml.sax.saxutils import escape
from dataclasses import dataclass, field


@dataclass
class InventoryItem:
    """Stock item in a voucher"""
    name: str
    quantity: float
    rate: float
    unit: str = "Kgs"
    godown: str = "Main Location"
    purchase_ledger: str = "Purchase Account"
    
    @property
    def amount(self) -> float:
        return self.quantity * self.rate


@dataclass
class LedgerEntry:
    """Ledger entry in a voucher"""
    ledger_name: str
    amount: float
    is_party: bool = False
    is_debit: bool = True
    bill_name: Optional[str] = None
    bill_type: str = "New Ref"


@dataclass
class VoucherData:
    """Complete voucher data"""
    company: str
    voucher_type: str  # Purchase, Sales, Receipt, Payment, Journal
    date: str  # YYYYMMDD format
    party_name: str
    reference: Optional[str] = None
    narration: Optional[str] = None
    voucher_number: Optional[str] = None
    
    # GST Fields
    party_gstin: Optional[str] = None
    state_name: str = "Maharashtra"
    place_of_supply: str = "Maharashtra"
    gst_registration_type: str = "Regular"
    
    # Items
    inventory_items: List[InventoryItem] = field(default_factory=list)
    ledger_entries: List[LedgerEntry] = field(default_factory=list)

    # Override sales ledger name (default: "Sales Account")
    sales_ledger_name: Optional[str] = None



class GoldenXMLBuilder:
    """
    Builds Tally XML that matches the golden XML structure exactly.
    This is the ONLY approved way to generate XML for Tally operations.
    """
    
    @staticmethod
    def generate_guid() -> str:
        """Generate a Tally-compatible GUID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def format_date(date_str: str) -> str:
        """Ensure date is in YYYYMMDD format"""
        if len(date_str) == 8:
            return date_str
        # Try to parse and reformat
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y%m%d")
        except:
            return datetime.datetime.now().strftime("%Y%m%d")
    
    @staticmethod
    def build_envelope(company: str = "", report_name: str = "All Masters") -> str:
        """Build the standard envelope header.
        SVCURRENTCOMPANY is intentionally omitted — Tally uses whichever company is open.
        """
        return f"""<ENVELOPE>
 <HEADER>
  <TALLYREQUEST>Import Data</TALLYREQUEST>
 </HEADER>
 <BODY>
  <IMPORTDATA>
   <REQUESTDESC>
    <REPORTNAME>{report_name}</REPORTNAME>
   </REQUESTDESC>
   <REQUESTDATA>
"""
    
    @staticmethod
    def close_envelope() -> str:
        """Close the envelope"""
        return """   </REQUESTDATA>
  </IMPORTDATA>
 </BODY>
</ENVELOPE>"""

    @classmethod
    def build_stock_item_xml(cls, name: str, unit: str = "Kgs",
                              under_group: str = "Primary",
                              gst_rate: float = 0.0) -> str:
        """
        Build XML to create a Stock Item in Tally.
        Called automatically before creating Invoice Voucher View vouchers
        to ensure the stock item exists in Tally.
        """
        guid = cls.generate_guid()
        xml = cls.build_envelope()
        xml += f"""    <TALLYMESSAGE xmlns:UDF="TallyUDF">
     <STOCKITEM NAME="{escape(name)}" ACTION="Create">
      <NAME>{escape(name)}</NAME>
      <PARENT>{escape(under_group)}</PARENT>
      <CATEGORY>&#4; Not Applicable</CATEGORY>
      <BASEUNITS>{escape(unit)}</BASEUNITS>
      <GSTAPPLICABLE>&#4; Applicable</GSTAPPLICABLE>
      <GSTTYPEOFSUPPLY>Goods</GSTTYPEOFSUPPLY>
      <GUID>{guid}</GUID>
      <ISDELETED>No</ISDELETED>
      <ISSIMPLEUNIT>Yes</ISSIMPLEUNIT>
     </STOCKITEM>
    </TALLYMESSAGE>
"""
        xml += cls.close_envelope()
        return xml

    @classmethod
    def create_stock_item_in_tally(cls, name: str, tally_url: str,
                                    unit: str = "Kgs",
                                    under_group: str = "Primary") -> bool:
        """
        Auto-create a stock item in Tally if it doesn't exist.
        Returns True if created or already exists, False on failure.
        """
        import requests as _requests
        import logging as _logging
        _log = _logging.getLogger("GoldenXMLBuilder")

        try:
            xml = cls.build_stock_item_xml(name, unit, under_group)
            resp = _requests.post(
                tally_url, data=xml,
                headers={'Content-Type': 'text/xml; charset=utf-8'},
                timeout=8
            )
            txt = resp.text
            if "<CREATED>1</CREATED>" in txt or "<ALTERED>1</ALTERED>" in txt:
                _log.info(f"✅ Stock item '{name}' created in Tally")
                return True
            if "<EXCEPTIONS>1</EXCEPTIONS>" in txt:
                # Item might already exist — not a hard failure
                _log.warning(f"Stock item '{name}' creation got EXCEPTION (may already exist): {txt[:200]}")
                return True   # We proceed anyway — voucher might still work
            _log.warning(f"Stock item '{name}' creation — unknown response: {txt[:200]}")
            return True  # Proceed optimistically
        except Exception as e:
            _log.warning(f"Could not create stock item '{name}' in Tally: {e}")
            return False


        return """   </REQUESTDATA>
  </IMPORTDATA>
 </BODY>
</ENVELOPE>"""
    
    # ============================================
    # PURCHASE VOUCHER (Invoice Voucher View)
    # ============================================
    @classmethod
    def build_purchase_voucher(cls, data: VoucherData) -> str:
        """
        Build Purchase voucher XML matching golden structure.
        Reference: tests/golden_xml/all_vouchers_dump.xml lines 15-273
        """
        guid = cls.generate_guid()
        date = cls.format_date(data.date)
        
        # Calculate totals
        item_total = sum(item.amount for item in data.inventory_items)
        tax_total = sum(entry.amount for entry in data.ledger_entries if not entry.is_party)
        voucher_total = item_total + tax_total
        
        xml = cls.build_envelope(data.company, report_name="Vouchers")
        xml += f"""    <TALLYMESSAGE xmlns:UDF="TallyUDF">
     <VOUCHER REMOTEID="{guid}" VCHTYPE="Purchase" ACTION="Create" OBJVIEW="Invoice Voucher View">
      <BASICBUYERADDRESS.LIST TYPE="String">
       <BASICBUYERADDRESS>{escape(data.company)}</BASICBUYERADDRESS>
      </BASICBUYERADDRESS.LIST>
      <OLDAUDITENTRYIDS.LIST TYPE="Number">
       <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>
      </OLDAUDITENTRYIDS.LIST>
      <DATE>{date}</DATE>
      <REFERENCEDATE>{date}</REFERENCEDATE>
      <BILLOFLADINGDATE>{date}</BILLOFLADINGDATE>
      <VCHSTATUSDATE>{date}</VCHSTATUSDATE>
      <GUID>{guid}</GUID>
      <GSTREGISTRATIONTYPE>{escape(data.gst_registration_type)}</GSTREGISTRATIONTYPE>
      <VATDEALERTYPE>Regular</VATDEALERTYPE>
      <STATENAME>{escape(data.state_name)}</STATENAME>
      <COUNTRYOFRESIDENCE>India</COUNTRYOFRESIDENCE>
      <PARTYGSTIN>{escape(data.party_gstin or "")}</PARTYGSTIN>
      <PLACEOFSUPPLY>{escape(data.place_of_supply)}</PLACEOFSUPPLY>
      <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
      <PARTYNAME>{escape(data.party_name)}</PARTYNAME>
      <PARTYLEDGERNAME>{escape(data.party_name)}</PARTYLEDGERNAME>
      <VOUCHERNUMBER>{escape(data.voucher_number or "")}</VOUCHERNUMBER>
      <BASICBUYERNAME>{escape(data.company)}</BASICBUYERNAME>
      <REFERENCE>{escape(data.reference or data.voucher_number or "")}</REFERENCE>
      <PARTYMAILINGNAME>{escape(data.party_name)}</PARTYMAILINGNAME>
      <CONSIGNEEMAILINGNAME>{escape(data.company)}</CONSIGNEEMAILINGNAME>
      <CONSIGNEESTATENAME>{escape(data.state_name)}</CONSIGNEESTATENAME>
      <CONSIGNEECOUNTRYNAME>India</CONSIGNEECOUNTRYNAME>
      <BASICBASEPARTYNAME>{escape(data.party_name)}</BASICBASEPARTYNAME>
      <NUMBERINGSTYLE>Auto Retain</NUMBERINGSTYLE>
      <CSTFORMISSUETYPE>&#4; Not Applicable</CSTFORMISSUETYPE>
      <CSTFORMRECVTYPE>&#4; Not Applicable</CSTFORMRECVTYPE>
      <FBTPAYMENTTYPE>Default</FBTPAYMENTTYPE>
      <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
      <VCHSTATUSTAXADJUSTMENT>Default</VCHSTATUSTAXADJUSTMENT>
      <VCHSTATUSVOUCHERTYPE>Purchase</VCHSTATUSVOUCHERTYPE>
      <VCHGSTCLASS>&#4; Not Applicable</VCHGSTCLASS>
      <VCHENTRYMODE>Item Invoice</VCHENTRYMODE>
      <DIFFACTUALQTY>No</DIFFACTUALQTY>
      <ISMSTFROMSYNC>No</ISMSTFROMSYNC>
      <ISDELETED>No</ISDELETED>
      <ISSECURITYONWHENENTERED>No</ISSECURITYONWHENENTERED>
      <ASORIGINAL>No</ASORIGINAL>
      <AUDITED>No</AUDITED>
      <ISCOMMONPARTY>No</ISCOMMONPARTY>
      <FORJOBCOSTING>No</FORJOBCOSTING>
      <ISOPTIONAL>No</ISOPTIONAL>
      <EFFECTIVEDATE>{date}</EFFECTIVEDATE>
      <USEFOREXCISE>No</USEFOREXCISE>
      <ISFORJOBWORKIN>No</ISFORJOBWORKIN>
      <ALLOWCONSUMPTION>No</ALLOWCONSUMPTION>
      <USEFORINTEREST>No</USEFORINTEREST>
      <USEFORGAINLOSS>No</USEFORGAINLOSS>
      <USEFORGODOWNTRANSFER>No</USEFORGODOWNTRANSFER>
      <USEFORCOMPOUND>No</USEFORCOMPOUND>
      <USEFORSERVICETAX>No</USEFORSERVICETAX>
      <ISREVERSECHARGEAPPLICABLE>No</ISREVERSECHARGEAPPLICABLE>
      <ISSYSTEM>No</ISSYSTEM>
      <ISFETCHEDONLY>No</ISFETCHEDONLY>
      <ISGSTOVERRIDDEN>No</ISGSTOVERRIDDEN>
      <ISCANCELLED>No</ISCANCELLED>
      <ISONHOLD>No</ISONHOLD>
      <ISSUMMARY>No</ISSUMMARY>
      <ISECOMMERCESUPPLY>No</ISECOMMERCESUPPLY>
      <ISBOENOTAPPLICABLE>No</ISBOENOTAPPLICABLE>
      <ISGSTSECSEVENAPPLICABLE>No</ISGSTSECSEVENAPPLICABLE>
      <IGNOREEINVVALIDATION>No</IGNOREEINVVALIDATION>
      <CMPGSTISOTHTERRITORYASSESSEE>No</CMPGSTISOTHTERRITORYASSESSEE>
      <PARTYGSTISOTHTERRITORYASSESSEE>No</PARTYGSTISOTHTERRITORYASSESSEE>
      <IRNJSONEXPORTED>No</IRNJSONEXPORTED>
      <IRNCANCELLED>No</IRNCANCELLED>
      <IGNOREGSTCONFLICTINMIG>No</IGNOREGSTCONFLICTINMIG>
      <ISOPBALTRANSACTION>No</ISOPBALTRANSACTION>
      <IGNOREGSTFORMATVALIDATION>No</IGNOREGSTFORMATVALIDATION>
      <ISELIGIBLEFORITC>Yes</ISELIGIBLEFORITC>
      <IGNOREGSTOPTIONALUNCERTAIN>No</IGNOREGSTOPTIONALUNCERTAIN>
      <UPDATESUMMARYVALUES>No</UPDATESUMMARYVALUES>
      <ISEWAYBILLAPPLICABLE>No</ISEWAYBILLAPPLICABLE>
      <ISDELETEDRETAINED>No</ISDELETEDRETAINED>
      <ISNULL>No</ISNULL>
      <ISEXCISEVOUCHER>No</ISEXCISEVOUCHER>
      <EXCISETAXOVERRIDE>No</EXCISETAXOVERRIDE>
      <USEFORTAXUNITTRANSFER>No</USEFORTAXUNITTRANSFER>
      <ISINVOICE>Yes</ISINVOICE>
      <MFGJOURNAL>No</MFGJOURNAL>
      <HASDISCOUNTS>No</HASDISCOUNTS>
      <ASPAYSLIP>No</ASPAYSLIP>
      <ISCOSTCENTRE>No</ISCOSTCENTRE>
      <ISSTXNONREALIZEDVCH>No</ISSTXNONREALIZEDVCH>
      <ISEXCISEMANUFACTURERON>No</ISEXCISEMANUFACTURERON>
      <ISBLANKCHEQUE>No</ISBLANKCHEQUE>
      <ISVOID>No</ISVOID>
      <ISVATDUTYPAID>Yes</ISVATDUTYPAID>
      <ISDELIVERYSAMEASCONSIGNEE>No</ISDELIVERYSAMEASCONSIGNEE>
      <ISDISPATCHSAMEASCONSIGNOR>No</ISDISPATCHSAMEASCONSIGNOR>
      <CHANGEVCHMODE>No</CHANGEVCHMODE>
      <VOUCHERNUMBERSERIES>Default</VOUCHERNUMBERSERIES>
      <EWAYBILLDETAILS.LIST>      </EWAYBILLDETAILS.LIST>
      <EXCLUDEDTAXATIONS.LIST>      </EXCLUDEDTAXATIONS.LIST>
      <OLDAUDITENTRIES.LIST>      </OLDAUDITENTRIES.LIST>
      <ACCOUNTAUDITENTRIES.LIST>      </ACCOUNTAUDITENTRIES.LIST>
      <AUDITENTRIES.LIST>      </AUDITENTRIES.LIST>
      <DUTYHEADDETAILS.LIST>      </DUTYHEADDETAILS.LIST>
      <GSTADVADJDETAILS.LIST>      </GSTADVADJDETAILS.LIST>
"""
        
        # Add inventory items
        for item in data.inventory_items:
            xml += cls._build_inventory_entry(item, is_purchase=True)
            
        # Add additional ledger entries (Taxes, etc.)
        for entry in data.ledger_entries:
            if not entry.is_party:
                xml += cls._build_ledger_entry(entry)
        
        # Add party ledger entry (Credit for Purchase)
        xml += f"""      <LEDGERENTRIES.LIST>
       <OLDAUDITENTRYIDS.LIST TYPE="Number">
        <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>
       </OLDAUDITENTRYIDS.LIST>
       <LEDGERNAME>{escape(data.party_name)}</LEDGERNAME>
       <GSTCLASS>&#4; Not Applicable</GSTCLASS>
       <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
       <LEDGERFROMITEM>No</LEDGERFROMITEM>
       <REMOVEZEROENTRIES>No</REMOVEZEROENTRIES>
       <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
       <GSTOVERRIDDEN>No</GSTOVERRIDDEN>
       <ISGSTASSESSABLEVALUEOVERRIDDEN>No</ISGSTASSESSABLEVALUEOVERRIDDEN>
       <STRDISGSTAPPLICABLE>No</STRDISGSTAPPLICABLE>
       <STRDGSTISPARTYLEDGER>No</STRDGSTISPARTYLEDGER>
       <STRDGSTISDUTYLEDGER>No</STRDGSTISDUTYLEDGER>
       <CONTENTNEGISPOS>No</CONTENTNEGISPOS>
       <ISLASTDEEMEDPOSITIVE>No</ISLASTDEEMEDPOSITIVE>
       <ISCAPVATTAXALTERED>No</ISCAPVATTAXALTERED>
       <ISCAPVATNOTCLAIMED>No</ISCAPVATNOTCLAIMED>
       <AMOUNT>{voucher_total:.2f}</AMOUNT>
       <BILLALLOCATIONS.LIST>
        <NAME>{escape(data.reference or data.voucher_number or str(int(datetime.datetime.now().timestamp())))}</NAME>
        <BILLTYPE>New Ref</BILLTYPE>
        <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>
        <AMOUNT>{voucher_total:.2f}</AMOUNT>
       </BILLALLOCATIONS.LIST>
      </LEDGERENTRIES.LIST>
"""
        
        # Close voucher and envelope
        xml += """     </VOUCHER>
    </TALLYMESSAGE>
"""
        xml += cls.close_envelope()
        
        return xml
    
    @classmethod
    def _build_inventory_entry(cls, item: InventoryItem, is_purchase: bool = True) -> str:
        """Build ALLINVENTORYENTRIES.LIST matching golden XML"""
        amount = -item.amount if is_purchase else item.amount
        deemed_positive = "Yes" if is_purchase else "No"
        
        return f"""      <ALLINVENTORYENTRIES.LIST>
       <STOCKITEMNAME>{escape(item.name)}</STOCKITEMNAME>
       <ISDEEMEDPOSITIVE>{deemed_positive}</ISDEEMEDPOSITIVE>
       <ISGSTASSESSABLEVALUEOVERRIDDEN>No</ISGSTASSESSABLEVALUEOVERRIDDEN>
       <STRDISGSTAPPLICABLE>No</STRDISGSTAPPLICABLE>
       <CONTENTNEGISPOS>No</CONTENTNEGISPOS>
       <ISLASTDEEMEDPOSITIVE>{deemed_positive}</ISLASTDEEMEDPOSITIVE>
       <ISAUTONEGATE>No</ISAUTONEGATE>
       <ISCUSTOMSCLEARANCE>No</ISCUSTOMSCLEARANCE>
       <ISTRACKCOMPONENT>No</ISTRACKCOMPONENT>
       <ISTRACKPRODUCTION>No</ISTRACKPRODUCTION>
       <ISPRIMARYITEM>No</ISPRIMARYITEM>
       <ISSCRAP>No</ISSCRAP>
       <RATE>{item.rate:.2f}/{item.unit}</RATE>
       <AMOUNT>{amount:.2f}</AMOUNT>
       <ACTUALQTY> {item.quantity:.2f} {item.unit}</ACTUALQTY>
       <BILLEDQTY> {item.quantity:.2f} {item.unit}</BILLEDQTY>
       <BATCHALLOCATIONS.LIST>
        <GODOWNNAME>{escape(item.godown)}</GODOWNNAME>
        <BATCHNAME>Primary Batch</BATCHNAME>
        <DESTINATIONGODOWNNAME>{escape(item.godown)}</DESTINATIONGODOWNNAME>
        <INDENTNO>&#4; Not Applicable</INDENTNO>
        <ORDERNO>&#4; Not Applicable</ORDERNO>
        <TRACKINGNUMBER>&#4; Not Applicable</TRACKINGNUMBER>
        <DYNAMICCSTISCLEARED>No</DYNAMICCSTISCLEARED>
        <AMOUNT>{amount:.2f}</AMOUNT>
        <ACTUALQTY> {item.quantity:.2f} {item.unit}</ACTUALQTY>
        <BILLEDQTY> {item.quantity:.2f} {item.unit}</BILLEDQTY>
        <ADDITIONALDETAILS.LIST>        </ADDITIONALDETAILS.LIST>
        <VOUCHERCOMPONENTLIST.LIST>        </VOUCHERCOMPONENTLIST.LIST>
       </BATCHALLOCATIONS.LIST>
       <ACCOUNTINGALLOCATIONS.LIST>
        <OLDAUDITENTRYIDS.LIST TYPE="Number">
         <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>
        </OLDAUDITENTRYIDS.LIST>
        <LEDGERNAME>{escape(item.purchase_ledger)}</LEDGERNAME>
        <GSTCLASS>&#4; Not Applicable</GSTCLASS>
        <ISDEEMEDPOSITIVE>{deemed_positive}</ISDEEMEDPOSITIVE>
        <LEDGERFROMITEM>No</LEDGERFROMITEM>
        <REMOVEZEROENTRIES>No</REMOVEZEROENTRIES>
        <ISPARTYLEDGER>No</ISPARTYLEDGER>
        <GSTOVERRIDDEN>No</GSTOVERRIDDEN>
        <ISGSTASSESSABLEVALUEOVERRIDDEN>No</ISGSTASSESSABLEVALUEOVERRIDDEN>
        <STRDISGSTAPPLICABLE>No</STRDISGSTAPPLICABLE>
        <STRDGSTISPARTYLEDGER>No</STRDGSTISPARTYLEDGER>
        <STRDGSTISDUTYLEDGER>No</STRDGSTISDUTYLEDGER>
        <CONTENTNEGISPOS>No</CONTENTNEGISPOS>
        <ISLASTDEEMEDPOSITIVE>{deemed_positive}</ISLASTDEEMEDPOSITIVE>
        <ISCAPVATTAXALTERED>No</ISCAPVATTAXALTERED>
        <ISCAPVATNOTCLAIMED>No</ISCAPVATNOTCLAIMED>
        <AMOUNT>{amount:.2f}</AMOUNT>
       </ACCOUNTINGALLOCATIONS.LIST>
      </ALLINVENTORYENTRIES.LIST>
"""

    @classmethod
    def _build_ledger_entry(cls, entry: LedgerEntry) -> str:
        """Build LEDGERENTRIES.LIST for taxes/expenses"""
        deemed_positive = "Yes" if entry.is_debit else "No"
        # For Purchase Taxes (Input GST), usually Debit (Positive)
        # For Purchase Party, Credit (Negative)
        
        return f"""      <LEDGERENTRIES.LIST>
       <OLDAUDITENTRYIDS.LIST TYPE="Number">
        <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>
       </OLDAUDITENTRYIDS.LIST>
       <LEDGERNAME>{escape(entry.ledger_name)}</LEDGERNAME>
       <GSTCLASS>&#4; Not Applicable</GSTCLASS>
       <ISDEEMEDPOSITIVE>{deemed_positive}</ISDEEMEDPOSITIVE>
       <LEDGERFROMITEM>No</LEDGERFROMITEM>
       <REMOVEZEROENTRIES>No</REMOVEZEROENTRIES>
       <ISPARTYLEDGER>No</ISPARTYLEDGER>
       <ISLASTDEEMEDPOSITIVE>{deemed_positive}</ISLASTDEEMEDPOSITIVE>
       <AMOUNT>{-entry.amount if not entry.is_debit else entry.amount:.2f}</AMOUNT>
      </LEDGERENTRIES.LIST>
"""
    
    # ============================================
    # SALES VOUCHER (Invoice Voucher View)
    # ============================================
    @classmethod
    def build_sales_voucher(cls, data: VoucherData) -> str:
        """Build Sales voucher XML matching golden structure"""
        guid = cls.generate_guid()
        date = cls.format_date(data.date)

        # Calculate totals
        item_total = sum(item.amount for item in data.inventory_items)
        tax_total = sum(e.amount for e in data.ledger_entries if not e.is_party)
        voucher_total = item_total + tax_total

        # Find the correct Sales ledger name — use passed override or default
        sales_ledger = data.sales_ledger_name or "Sales Account"

        xml = cls.build_envelope(data.company, report_name="Vouchers")
        xml += f"""    <TALLYMESSAGE xmlns:UDF="TallyUDF">
     <VOUCHER REMOTEID="{guid}" VCHTYPE="Sales" ACTION="Create" OBJVIEW="Invoice Voucher View">
      <BASICBUYERADDRESS.LIST TYPE="String">
       <BASICBUYERADDRESS>{escape(data.party_name)}</BASICBUYERADDRESS>
      </BASICBUYERADDRESS.LIST>
      <OLDAUDITENTRYIDS.LIST TYPE="Number">
       <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>
      </OLDAUDITENTRYIDS.LIST>
      <DATE>{date}</DATE>
      <REFERENCEDATE>{date}</REFERENCEDATE>
      <BILLOFLADINGDATE>{date}</BILLOFLADINGDATE>
      <VCHSTATUSDATE>{date}</VCHSTATUSDATE>
      <GUID>{guid}</GUID>
      <GSTREGISTRATIONTYPE>{escape(data.gst_registration_type)}</GSTREGISTRATIONTYPE>
      <VATDEALERTYPE>Regular</VATDEALERTYPE>
      <STATENAME>{escape(data.state_name)}</STATENAME>
      <COUNTRYOFRESIDENCE>India</COUNTRYOFRESIDENCE>
      <PARTYGSTIN>{escape(data.party_gstin or "")}</PARTYGSTIN>
      <PLACEOFSUPPLY>{escape(data.place_of_supply)}</PLACEOFSUPPLY>
      <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
      <PARTYNAME>{escape(data.party_name)}</PARTYNAME>
      <PARTYLEDGERNAME>{escape(data.party_name)}</PARTYLEDGERNAME>
      <VOUCHERNUMBER>{escape(data.voucher_number or "")}</VOUCHERNUMBER>
      <BASICBUYERNAME>{escape(data.party_name)}</BASICBUYERNAME>
      <REFERENCE>{escape(data.reference or data.voucher_number or "")}</REFERENCE>
      <PARTYMAILINGNAME>{escape(data.party_name)}</PARTYMAILINGNAME>
      <CONSIGNEEMAILINGNAME>{escape(data.party_name)}</CONSIGNEEMAILINGNAME>
      <CONSIGNEESTATENAME>{escape(data.state_name)}</CONSIGNEESTATENAME>
      <CONSIGNEECOUNTRYNAME>India</CONSIGNEECOUNTRYNAME>
      <BASICBASEPARTYNAME>{escape(data.party_name)}</BASICBASEPARTYNAME>
      <NUMBERINGSTYLE>Auto Retain</NUMBERINGSTYLE>
      <CSTFORMISSUETYPE>&#4; Not Applicable</CSTFORMISSUETYPE>
      <CSTFORMRECVTYPE>&#4; Not Applicable</CSTFORMRECVTYPE>
      <FBTPAYMENTTYPE>Default</FBTPAYMENTTYPE>
      <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
      <VCHSTATUSTAXADJUSTMENT>Default</VCHSTATUSTAXADJUSTMENT>
      <VCHSTATUSVOUCHERTYPE>Sales</VCHSTATUSVOUCHERTYPE>
      <VCHGSTCLASS>&#4; Not Applicable</VCHGSTCLASS>
      <VCHENTRYMODE>Item Invoice</VCHENTRYMODE>
      <DIFFACTUALQTY>No</DIFFACTUALQTY>
      <ISMSTFROMSYNC>No</ISMSTFROMSYNC>
      <ISDELETED>No</ISDELETED>
      <ISSECURITYONWHENENTERED>No</ISSECURITYONWHENENTERED>
      <ASORIGINAL>No</ASORIGINAL>
      <AUDITED>No</AUDITED>
      <ISCOMMONPARTY>No</ISCOMMONPARTY>
      <FORJOBCOSTING>No</FORJOBCOSTING>
      <ISOPTIONAL>No</ISOPTIONAL>
      <EFFECTIVEDATE>{date}</EFFECTIVEDATE>
      <USEFOREXCISE>No</USEFOREXCISE>
      <ISFORJOBWORKIN>No</ISFORJOBWORKIN>
      <ALLOWCONSUMPTION>No</ALLOWCONSUMPTION>
      <USEFORINTEREST>No</USEFORINTEREST>
      <USEFORGAINLOSS>No</USEFORGAINLOSS>
      <USEFORGODOWNTRANSFER>No</USEFORGODOWNTRANSFER>
      <USEFORCOMPOUND>No</USEFORCOMPOUND>
      <USEFORSERVICETAX>No</USEFORSERVICETAX>
      <ISREVERSECHARGEAPPLICABLE>No</ISREVERSECHARGEAPPLICABLE>
      <ISSYSTEM>No</ISSYSTEM>
      <ISFETCHEDONLY>No</ISFETCHEDONLY>
      <ISGSTOVERRIDDEN>No</ISGSTOVERRIDDEN>
      <ISCANCELLED>No</ISCANCELLED>
      <ISONHOLD>No</ISONHOLD>
      <ISSUMMARY>No</ISSUMMARY>
      <ISECOMMERCESUPPLY>No</ISECOMMERCESUPPLY>
      <ISBOENOTAPPLICABLE>No</ISBOENOTAPPLICABLE>
      <ISGSTSECSEVENAPPLICABLE>No</ISGSTSECSEVENAPPLICABLE>
      <IGNOREEINVVALIDATION>No</IGNOREEINVVALIDATION>
      <CMPGSTISOTHTERRITORYASSESSEE>No</CMPGSTISOTHTERRITORYASSESSEE>
      <PARTYGSTISOTHTERRITORYASSESSEE>No</PARTYGSTISOTHTERRITORYASSESSEE>
      <IRNJSONEXPORTED>No</IRNJSONEXPORTED>
      <IRNCANCELLED>No</IRNCANCELLED>
      <IGNOREGSTCONFLICTINMIG>No</IGNOREGSTCONFLICTINMIG>
      <ISOPBALTRANSACTION>No</ISOPBALTRANSACTION>
      <IGNOREGSTFORMATVALIDATION>No</IGNOREGSTFORMATVALIDATION>
      <ISELIGIBLEFORITC>Yes</ISELIGIBLEFORITC>
      <IGNOREGSTOPTIONALUNCERTAIN>No</IGNOREGSTOPTIONALUNCERTAIN>
      <UPDATESUMMARYVALUES>No</UPDATESUMMARYVALUES>
      <ISEWAYBILLAPPLICABLE>No</ISEWAYBILLAPPLICABLE>
      <ISDELETEDRETAINED>No</ISDELETEDRETAINED>
      <ISNULL>No</ISNULL>
      <ISEXCISEVOUCHER>No</ISEXCISEVOUCHER>
      <EXCISETAXOVERRIDE>No</EXCISETAXOVERRIDE>
      <USEFORTAXUNITTRANSFER>No</USEFORTAXUNITTRANSFER>
      <ISINVOICE>Yes</ISINVOICE>
      <MFGJOURNAL>No</MFGJOURNAL>
      <HASDISCOUNTS>No</HASDISCOUNTS>
      <ASPAYSLIP>No</ASPAYSLIP>
      <ISCOSTCENTRE>No</ISCOSTCENTRE>
      <ISSTXNONREALIZEDVCH>No</ISSTXNONREALIZEDVCH>
      <ISEXCISEMANUFACTURERON>No</ISEXCISEMANUFACTURERON>
      <ISBLANKCHEQUE>No</ISBLANKCHEQUE>
      <ISVOID>No</ISVOID>
      <ISVATDUTYPAID>Yes</ISVATDUTYPAID>
      <ISDELIVERYSAMEASCONSIGNEE>No</ISDELIVERYSAMEASCONSIGNEE>
      <ISDISPATCHSAMEASCONSIGNOR>No</ISDISPATCHSAMEASCONSIGNOR>
      <CHANGEVCHMODE>No</CHANGEVCHMODE>
      <VOUCHERNUMBERSERIES>Default</VOUCHERNUMBERSERIES>
      <EWAYBILLDETAILS.LIST>      </EWAYBILLDETAILS.LIST>
      <EXCLUDEDTAXATIONS.LIST>      </EXCLUDEDTAXATIONS.LIST>
      <OLDAUDITENTRIES.LIST>      </OLDAUDITENTRIES.LIST>
      <ACCOUNTAUDITENTRIES.LIST>      </ACCOUNTAUDITENTRIES.LIST>
      <AUDITENTRIES.LIST>      </AUDITENTRIES.LIST>
      <DUTYHEADDETAILS.LIST>      </DUTYHEADDETAILS.LIST>
      <GSTADVADJDETAILS.LIST>      </GSTADVADJDETAILS.LIST>
"""

        # Add inventory items
        for item in data.inventory_items:
            # Override item's purchase ledger to the requested sales ledger context
            old_pl = item.purchase_ledger
            item.purchase_ledger = sales_ledger
            xml += cls._build_inventory_entry(item, is_purchase=False)
            item.purchase_ledger = old_pl

        # Add additional ledger entries (Taxes, etc.)
        for entry in data.ledger_entries:
            if not entry.is_party:
                xml += cls._build_ledger_entry(entry)

        # Add party ledger entry (Debit for Sales)
        xml += f"""      <LEDGERENTRIES.LIST>
       <OLDAUDITENTRYIDS.LIST TYPE="Number">
        <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>
       </OLDAUDITENTRYIDS.LIST>
       <LEDGERNAME>{escape(data.party_name)}</LEDGERNAME>
       <GSTCLASS>&#4; Not Applicable</GSTCLASS>
       <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
       <LEDGERFROMITEM>No</LEDGERFROMITEM>
       <REMOVEZEROENTRIES>No</REMOVEZEROENTRIES>
       <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
       <GSTOVERRIDDEN>No</GSTOVERRIDDEN>
       <ISGSTASSESSABLEVALUEOVERRIDDEN>No</ISGSTASSESSABLEVALUEOVERRIDDEN>
       <STRDISGSTAPPLICABLE>No</STRDISGSTAPPLICABLE>
       <STRDGSTISPARTYLEDGER>No</STRDGSTISPARTYLEDGER>
       <STRDGSTISDUTYLEDGER>No</STRDGSTISDUTYLEDGER>
       <CONTENTNEGISPOS>No</CONTENTNEGISPOS>
       <ISLASTDEEMEDPOSITIVE>Yes</ISLASTDEEMEDPOSITIVE>
       <ISCAPVATTAXALTERED>No</ISCAPVATTAXALTERED>
       <ISCAPVATNOTCLAIMED>No</ISCAPVATNOTCLAIMED>
       <AMOUNT>-{voucher_total:.2f}</AMOUNT>
       <BILLALLOCATIONS.LIST>
        <NAME>{escape(data.reference or data.voucher_number or "New")}</NAME>
        <BILLTYPE>New Ref</BILLTYPE>
        <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>
        <AMOUNT>-{voucher_total:.2f}</AMOUNT>
       </BILLALLOCATIONS.LIST>
      </LEDGERENTRIES.LIST>
"""

        xml += """     </VOUCHER>
    </TALLYMESSAGE>
"""
        xml += cls.close_envelope()
        return xml

    # ============================================
    # RECEIPT VOUCHER (Accounting Voucher View)
    # ============================================
    @classmethod
    def build_receipt_voucher(cls, company: str, date: str, 
                               from_ledger: str, to_ledger: str,
                               amount: float, narration: str = "",
                               bill_ref: Optional[str] = None) -> str:
        """
        Build Receipt voucher (money coming in).
        from_ledger = Party (who is paying)
        to_ledger = Cash/Bank (where money goes)
        """
        guid = cls.generate_guid()
        date = cls.format_date(date)
        
        xml = cls.build_envelope(company)
        xml += f"""    <TALLYMESSAGE xmlns:UDF="TallyUDF">
     <VOUCHER REMOTEID="{guid}" VCHTYPE="Receipt" ACTION="Create" OBJVIEW="Accounting Voucher View">
      <OLDAUDITENTRYIDS.LIST TYPE="Number">
       <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>
      </OLDAUDITENTRYIDS.LIST>
      <DATE>{date}</DATE>
      <VCHSTATUSDATE>{date}</VCHSTATUSDATE>
      <GUID>{guid}</GUID>
      <VOUCHERTYPENAME>Receipt</VOUCHERTYPENAME>
      <PARTYLEDGERNAME>{escape(to_ledger)}</PARTYLEDGERNAME>
      <NARRATION>{escape(narration)}</NARRATION>
      <NUMBERINGSTYLE>Auto Retain</NUMBERINGSTYLE>
      <CSTFORMISSUETYPE>&#4; Not Applicable</CSTFORMISSUETYPE>
      <CSTFORMRECVTYPE>&#4; Not Applicable</CSTFORMRECVTYPE>
      <FBTPAYMENTTYPE>Default</FBTPAYMENTTYPE>
      <PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>
      <VCHSTATUSTAXADJUSTMENT>Default</VCHSTATUSTAXADJUSTMENT>
      <VCHSTATUSVOUCHERTYPE>Receipt</VCHSTATUSVOUCHERTYPE>
      <VCHGSTCLASS>&#4; Not Applicable</VCHGSTCLASS>
      <DIFFACTUALQTY>No</DIFFACTUALQTY>
      <ISDELETED>No</ISDELETED>
      <EFFECTIVEDATE>{date}</EFFECTIVEDATE>
      <HASCASHFLOW>Yes</HASCASHFLOW>
      <ISINVOICE>No</ISINVOICE>
      <ISVATDUTYPAID>Yes</ISVATDUTYPAID>
      <VOUCHERNUMBERSERIES>Default</VOUCHERNUMBERSERIES>
      <ALLLEDGERENTRIES.LIST>
       <OLDAUDITENTRYIDS.LIST TYPE="Number">
        <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>
       </OLDAUDITENTRYIDS.LIST>
       <LEDGERNAME>{escape(to_ledger)}</LEDGERNAME>
       <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
       <LEDGERFROMITEM>No</LEDGERFROMITEM>
       <REMOVEZEROENTRIES>No</REMOVEZEROENTRIES>
       <ISPARTYLEDGER>No</ISPARTYLEDGER>
       <ISLASTDEEMEDPOSITIVE>Yes</ISLASTDEEMEDPOSITIVE>
       <AMOUNT>-{abs(amount):.2f}</AMOUNT>
      </ALLLEDGERENTRIES.LIST>
      <ALLLEDGERENTRIES.LIST>
       <OLDAUDITENTRYIDS.LIST TYPE="Number">
        <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>
       </OLDAUDITENTRYIDS.LIST>
       <LEDGERNAME>{escape(from_ledger)}</LEDGERNAME>
       <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
       <LEDGERFROMITEM>No</LEDGERFROMITEM>
       <REMOVEZEROENTRIES>No</REMOVEZEROENTRIES>
       <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
       <ISLASTDEEMEDPOSITIVE>No</ISLASTDEEMEDPOSITIVE>
       <AMOUNT>{abs(amount):.2f}</AMOUNT>
"""
        # Add bill allocation if reference provided
        if bill_ref:
            xml += f"""       <BILLALLOCATIONS.LIST>
        <NAME>{escape(bill_ref)}</NAME>
        <BILLTYPE>Agst Ref</BILLTYPE>
        <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>
        <AMOUNT>{abs(amount):.2f}</AMOUNT>
       </BILLALLOCATIONS.LIST>
"""
        xml += """      </ALLLEDGERENTRIES.LIST>
     </VOUCHER>
    </TALLYMESSAGE>
"""
        xml += cls.close_envelope()
        
        return xml
    
    # ============================================
    # PAYMENT VOUCHER (Accounting Voucher View)
    # ============================================
    @classmethod
    def build_payment_voucher(cls, company: str, date: str,
                               from_ledger: str, to_ledger: str,
                               amount: float, narration: str = "",
                               bill_ref: Optional[str] = None) -> str:
        """
        Build Payment voucher (money going out).
        from_ledger = Cash/Bank (where money comes from)
        to_ledger = Party/Expense (who receives)
        """
        guid = cls.generate_guid()
        date = cls.format_date(date)
        
        xml = cls.build_envelope(company)
        xml += f"""    <TALLYMESSAGE xmlns:UDF="TallyUDF">
     <VOUCHER REMOTEID="{guid}" VCHTYPE="Payment" ACTION="Create" OBJVIEW="Accounting Voucher View">
      <OLDAUDITENTRYIDS.LIST TYPE="Number">
       <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>
      </OLDAUDITENTRYIDS.LIST>
      <DATE>{date}</DATE>
      <VCHSTATUSDATE>{date}</VCHSTATUSDATE>
      <GUID>{guid}</GUID>
      <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
      <PARTYLEDGERNAME>{escape(from_ledger)}</PARTYLEDGERNAME>
      <NARRATION>{escape(narration)}</NARRATION>
      <NUMBERINGSTYLE>Auto Retain</NUMBERINGSTYLE>
      <CSTFORMISSUETYPE>&#4; Not Applicable</CSTFORMISSUETYPE>
      <CSTFORMRECVTYPE>&#4; Not Applicable</CSTFORMRECVTYPE>
      <FBTPAYMENTTYPE>Default</FBTPAYMENTTYPE>
      <PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>
      <VCHSTATUSTAXADJUSTMENT>Default</VCHSTATUSTAXADJUSTMENT>
      <VCHSTATUSVOUCHERTYPE>Payment</VCHSTATUSVOUCHERTYPE>
      <VCHGSTCLASS>&#4; Not Applicable</VCHGSTCLASS>
      <DIFFACTUALQTY>No</DIFFACTUALQTY>
      <ISDELETED>No</ISDELETED>
      <EFFECTIVEDATE>{date}</EFFECTIVEDATE>
      <HASCASHFLOW>Yes</HASCASHFLOW>
      <ISINVOICE>No</ISINVOICE>
      <ISVATDUTYPAID>Yes</ISVATDUTYPAID>
      <VOUCHERNUMBERSERIES>Default</VOUCHERNUMBERSERIES>
      <ALLLEDGERENTRIES.LIST>
       <OLDAUDITENTRYIDS.LIST TYPE="Number">
        <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>
       </OLDAUDITENTRYIDS.LIST>
       <LEDGERNAME>{escape(to_ledger)}</LEDGERNAME>
       <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
       <LEDGERFROMITEM>No</LEDGERFROMITEM>
       <REMOVEZEROENTRIES>No</REMOVEZEROENTRIES>
       <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
       <ISLASTDEEMEDPOSITIVE>Yes</ISLASTDEEMEDPOSITIVE>
       <AMOUNT>-{abs(amount):.2f}</AMOUNT>
"""
        if bill_ref:
            xml += f"""       <BILLALLOCATIONS.LIST>
        <NAME>{escape(bill_ref)}</NAME>
        <BILLTYPE>Agst Ref</BILLTYPE>
        <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>
        <AMOUNT>-{abs(amount):.2f}</AMOUNT>
       </BILLALLOCATIONS.LIST>
"""
        xml += f"""      </ALLLEDGERENTRIES.LIST>
      <ALLLEDGERENTRIES.LIST>
       <OLDAUDITENTRYIDS.LIST TYPE="Number">
        <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>
       </OLDAUDITENTRYIDS.LIST>
       <LEDGERNAME>{escape(from_ledger)}</LEDGERNAME>
       <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
       <LEDGERFROMITEM>No</LEDGERFROMITEM>
       <REMOVEZEROENTRIES>No</REMOVEZEROENTRIES>
       <ISPARTYLEDGER>No</ISPARTYLEDGER>
       <ISLASTDEEMEDPOSITIVE>No</ISLASTDEEMEDPOSITIVE>
       <AMOUNT>{abs(amount):.2f}</AMOUNT>
      </ALLLEDGERENTRIES.LIST>
     </VOUCHER>
    </TALLYMESSAGE>
"""
        xml += cls.close_envelope()
        
        return xml
    
    # ============================================
    # LEDGER MASTER
    # ============================================
    @classmethod
    def build_ledger(cls, company: str, ledger_name: str, 
                      parent_group: str = "Sundry Debtors",
                      gstin: Optional[str] = None,
                      address: Optional[str] = None,
                      state: str = "Maharashtra") -> str:
        """Build Ledger master XML"""
        guid = cls.generate_guid()
        
        xml = cls.build_envelope(company)
        xml += f"""    <TALLYMESSAGE xmlns:UDF="TallyUDF">
     <LEDGER NAME="{escape(ledger_name)}" ACTION="Create">
      <NAME.LIST>
       <NAME>{escape(ledger_name)}</NAME>
      </NAME.LIST>
      <PARENT>{escape(parent_group)}</PARENT>
      <GUID>{guid}</GUID>
"""
        if address:
            xml += f"""      <ADDRESS.LIST TYPE="String">
       <ADDRESS>{escape(address)}</ADDRESS>
      </ADDRESS.LIST>
"""
        if gstin:
            xml += f"""      <PARTYGSTIN>{escape(gstin)}</PARTYGSTIN>
      <GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>
"""
        xml += f"""      <COUNTRYOFRESIDENCE>India</COUNTRYOFRESIDENCE>
      <LEDSTATENAME>{escape(state)}</LEDSTATENAME>
      <ISBILLWISEON>Yes</ISBILLWISEON>
      <AFFECTSSTOCK>No</AFFECTSSTOCK>
      <ISTDSAPPLICABLE>No</ISTDSAPPLICABLE>
      <ISTCSAPPLICABLE>No</ISTCSAPPLICABLE>
      <ISGSTAPPLICABLE>Yes</ISGSTAPPLICABLE>
     </LEDGER>
    </TALLYMESSAGE>
"""
        xml += cls.close_envelope()
        
        return xml
    
    # ============================================
    # STOCK ITEM MASTER
    # ============================================
    @classmethod
    def build_stock_item(cls, company: str, item_name: str,
                          unit: str = "Kgs",
                          group: str = "Primary",
                          opening_qty: float = 0,
                          opening_rate: float = 0) -> str:
        """Build Stock Item master XML"""
        guid = cls.generate_guid()
        
        xml = cls.build_envelope(company)
        xml += f"""    <TALLYMESSAGE xmlns:UDF="TallyUDF">
     <STOCKITEM NAME="{escape(item_name)}" ACTION="Create">
      <NAME.LIST>
       <NAME>{escape(item_name)}</NAME>
      </NAME.LIST>
      <GUID>{guid}</GUID>
      <PARENT>{escape(group) if group != "Primary" else ""}</PARENT>
      <BASEUNITS>{escape(unit)}</BASEUNITS>
      <ADDITIONALUNITS>{escape(unit)}</ADDITIONALUNITS>
      <ISBATCHWISEON>No</ISBATCHWISEON>
      <ISPERISHABLEON>No</ISPERISHABLEON>
      <HASMFGDATE>No</HASMFGDATE>
      <ISGSTUPDATED>Yes</ISGSTUPDATED>
"""
        if opening_qty > 0:
            xml += f"""      <OPENINGBALANCE>{opening_qty:.2f} {unit}</OPENINGBALANCE>
      <OPENINGVALUE>{opening_qty * opening_rate:.2f}</OPENINGVALUE>
      <OPENINGRATE>{opening_rate:.2f}/{unit}</OPENINGRATE>
"""
        xml += """     </STOCKITEM>
    </TALLYMESSAGE>
"""
        xml += cls.close_envelope()
        
        return xml


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

def create_purchase_xml(company: str, party: str, date: str, 
                        items: List[Dict[str, Any]], 
                        invoice_number: str = None,
                        party_gstin: str = None,
                        taxes: List[Dict[str, Any]] = []) -> str:
    """
    Convenience function to create Purchase voucher.
    
    Args:
        company: Company name in Tally
        party: Supplier/Party name
        date: Date in YYYYMMDD or YYYY-MM-DD format
        items: List of dicts with keys: name, quantity, rate, unit (optional)
        invoice_number: Reference/Invoice number
        party_gstin: Party GSTIN (optional)
    
    Returns:
        Complete XML string ready to post to Tally
    """
    inventory_items = []
    for item in items:
        inventory_items.append(InventoryItem(
            name=item.get("name", item.get("item_name", "Unknown Item")),
            quantity=float(item.get("quantity", item.get("qty", 0))),
            rate=float(item.get("rate", item.get("price", 0))),
            unit=item.get("unit", "Kgs")
        ))
    
    data = VoucherData(
        company=company,
        voucher_type="Purchase",
        date=date,
        party_name=party,
        reference=invoice_number,
        voucher_number=invoice_number,
        party_gstin=party_gstin,
        inventory_items=inventory_items
    )
    
    # Add Taxes
    for tax in taxes:
        data.ledger_entries.append(LedgerEntry(
            ledger_name=tax.get("ledger", "CGST"),
            amount=float(tax.get("amount", 0)),
            is_debit=True # Purchases taxes are Debit
        ))
    
    return GoldenXMLBuilder.build_purchase_voucher(data)


def create_sales_xml(company: str, party: str, date: str,
                     items: List[Dict[str, Any]],
                     invoice_number: str = None,
                     party_gstin: str = None) -> str:
    """Convenience function to create Sales voucher."""
    inventory_items = []
    for item in items:
        inv_item = InventoryItem(
            name=item.get("name", item.get("item_name", "Unknown Item")),
            quantity=float(item.get("quantity", item.get("qty", 0))),
            rate=float(item.get("rate", item.get("price", 0))),
            unit=item.get("unit", "Kgs")
        )
        inv_item.purchase_ledger = "Sales Account"  # Override for sales
        inventory_items.append(inv_item)
    
    data = VoucherData(
        company=company,
        voucher_type="Sales",
        date=date,
        party_name=party,
        reference=invoice_number,
        voucher_number=invoice_number,
        party_gstin=party_gstin,
        inventory_items=inventory_items
    )
    
    return GoldenXMLBuilder.build_sales_voucher(data)


def create_receipt_xml(company: str, party: str, bank_ledger: str,
                       date: str, amount: float,
                       bill_ref: str = None, narration: str = "") -> str:
    """Convenience function to create Receipt voucher."""
    return GoldenXMLBuilder.build_receipt_voucher(
        company=company,
        date=date,
        from_ledger=party,
        to_ledger=bank_ledger,
        amount=amount,
        narration=narration,
        bill_ref=bill_ref
    )


def create_payment_xml(company: str, party: str, bank_ledger: str,
                       date: str, amount: float,
                       bill_ref: str = None, narration: str = "") -> str:
    """Convenience function to create Payment voucher."""
    return GoldenXMLBuilder.build_payment_voucher(
        company=company,
        date=date,
        from_ledger=bank_ledger,
        to_ledger=party,
        amount=amount,
        narration=narration,
        bill_ref=bill_ref
    )


def create_ledger_xml(company: str, ledger_name: str,
                      parent_group: str = "Sundry Debtors",
                      gstin: str = None, address: str = None) -> str:
    """Convenience function to create Ledger master."""
    return GoldenXMLBuilder.build_ledger(
        company=company,
        ledger_name=ledger_name,
        parent_group=parent_group,
        gstin=gstin,
        address=address
    )


def create_stock_item_xml(company: str, item_name: str,
                          unit: str = "Kgs", group: str = "Primary") -> str:
    """Convenience function to create Stock Item master."""
    return GoldenXMLBuilder.build_stock_item(
        company=company,
        item_name=item_name,
        unit=unit,
        group=group
    )
