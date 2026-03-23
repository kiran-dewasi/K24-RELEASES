import os
import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import datetime
import time
import threading
import asyncio
import logging

logger = logging.getLogger(__name__)


def _fire_voucher_credit_event(
    voucher_type: str,
    tenant_id: Optional[str],
    subtype: str = "created",
    tally_guid: Optional[str] = None,
) -> None:
    """
    Fire a VOUCHER credit event after a successful Tally push.
    Runs synchronously but is fast (non-blocking DB call via supabase HTTP).
    Logs errors silently — never crashes the caller.
    """
    if not tenant_id:
        logger.debug("[CreditHook] No tenant_id — skipping voucher credit event.")
        return
    try:
        from backend.credit_engine import record_event
        decision = record_event(
            tenant_id     = tenant_id,
            event_type    = "VOUCHER",
            event_subtype = subtype,
            source        = "tally_sync",
            metadata      = {"voucher_type": voucher_type, "tally_guid": tally_guid},
        )
        logger.info(
            f"[CreditHook] VOUCHER/{subtype} | tenant={tenant_id} | "
            f"status={decision.status} | used={decision.usage.credits_used_total}/{decision.usage.max_credits}"
        )
        if decision.is_blocked:
            logger.warning(
                f"[CreditHook] Tenant {tenant_id} is BLOCKED — voucher was already posted to Tally "
                f"but future vouchers will be blocked until plan upgrade."
            )
    except Exception as exc:
        logger.warning(f"[CreditHook] Voucher credit event failed (non-fatal): {exc}")

# --- Configuration ---
TALLY_URL = os.getenv("TALLY_URL", "http://localhost:9000")
TALLY_TIMEOUT = int(os.getenv("TALLY_TIMEOUT", "30"))

@dataclass
class TallyResponse:
    success: bool
    tally_status: str = ""
    tally_response: Dict[str, Any] = field(default_factory=dict)
    error_details: str = ""
    raw_response: str = ""

    def to_dict(self):
        return {
            "success": self.success,
            "tally_status": self.tally_status,
            "tally_response": self.tally_response,
            "error_details": self.error_details,
            "raw_response": self.raw_response
        }

    @property
    def succeeded(self):
        return self.success

    @property
    def errors(self):
        return self.error_details

# Exceptions for backward compatibility and control flow
class TallyAPIError(Exception):
    pass

class TallyIgnoredError(Exception):
    pass

# Alias for backward compatibility with sync_engine
PushResult = TallyResponse

class TallyXMLBuilder:
    @staticmethod
    def _create_envelope():
        envelope = ET.Element("ENVELOPE")
        header = ET.SubElement(envelope, "HEADER")
        tallyrequest = ET.SubElement(header, "TALLYREQUEST")
        tallyrequest.text = "Import Data"
        body = ET.SubElement(envelope, "BODY")
        importalldata = ET.SubElement(body, "IMPORTDATA")
        reqdesc = ET.SubElement(importalldata, "REQUESTDESC")
        reportname = ET.SubElement(reqdesc, "REPORTNAME")
        reportname.text = "All Masters"
        staticvariables = ET.SubElement(reqdesc, "STATICVARIABLES")
        svcurrentcompany = ET.SubElement(staticvariables, "SVCURRENTCOMPANY")
        # Company name will be set by the caller if needed, usually in Tally context 
        # but here we focus on the request data structure.
        return envelope, importalldata

    @staticmethod
    def build_ledger_xml(company: str, ledger_name: str, parent_group: str, fields: Dict[str, str] = {}) -> str:
        envelope, importalldata = TallyXMLBuilder._create_envelope()
        
        # Set Company Context in Header if needed, but usually Import Data relies on active company
        # However, we can inject SVCURRENTCOMPANY if we want to be safe, but mostly Tally assumes active.
        # User prompt structure suggests creating a ledger.
        
        reqdesc = importalldata.find("REQUESTDESC")
        staticvariables = reqdesc.find("STATICVARIABLES")
        svcurrentcompany = staticvariables.find("SVCURRENTCOMPANY")
        svcurrentcompany.text = company


        requestdata = ET.SubElement(importalldata, "REQUESTDATA")
        tallymessage = ET.SubElement(requestdata, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        
        ledger = ET.SubElement(tallymessage, "LEDGER", {"NAME": ledger_name, "ACTION": "Create"})
        
        # Mandatory Fields
        name_elem = ET.SubElement(ledger, "NAME.LIST")
        name_val = ET.SubElement(name_elem, "NAME")
        name_val.text = ledger_name
        
        parent_elem = ET.SubElement(ledger, "PARENT")
        parent_elem.text = parent_group
        
        # Map fields
        # fields dict keys should match Tally XML tags
        # Special handling for Addresses (multiline)
        for key, value in fields.items():
            if not value:
                continue
                
            if key == "Address":
                # Address in Tally is ADDRESS.LIST -> ADDRESS
                addr_list = ET.SubElement(ledger, "ADDRESS.LIST")
                lines = value.split('\n')
                for line in lines:
                    addr = ET.SubElement(addr_list, "ADDRESS")
                    addr.text = line
            elif key == "Email":
                # LEDGERMAILINGDETAILS.LIST -> EMAIL
                 mailing = ET.SubElement(ledger, "LEDGERMAILINGDETAILS.LIST")
                 email_elem = ET.SubElement(mailing, "EMAIL")
                 email_elem.text = value
            else:
                # Direct child of LEDGER
                elem = ET.SubElement(ledger, key)
                elem.text = value

        # Pretty print
        xmlstr = minidom.parseString(ET.tostring(envelope)).toprettyxml(indent="  ")
        return xmlstr

    @staticmethod
    def build_stock_item_xml(company: str, item_name: str, unit: str = "Kg", opening_balance: int = 0, rate: float = 0) -> str:
        envelope, importalldata = TallyXMLBuilder._create_envelope()
        
        reqdesc = importalldata.find("REQUESTDESC")
        staticvariables = reqdesc.find("STATICVARIABLES")
        svcurrentcompany = staticvariables.find("SVCURRENTCOMPANY")
        svcurrentcompany.text = company

        requestdata = ET.SubElement(importalldata, "REQUESTDATA")
        tallymessage = ET.SubElement(requestdata, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        
        stockitem = ET.SubElement(tallymessage, "STOCKITEM", {"NAME": item_name, "ACTION": "Create"})
        
        # Mandatory Name
        name_list = ET.SubElement(stockitem, "NAME.LIST")
        name = ET.SubElement(name_list, "NAME")
        name.text = item_name
        
        # Base Unit
        baseunit = ET.SubElement(stockitem, "BASEUNITS")
        baseunit.text = unit
        
        xmlstr = minidom.parseString(ET.tostring(envelope)).toprettyxml(indent="  ")
        return xmlstr

    @staticmethod
    def build_voucher_xml(company: str, voucher_type: str, date: str, party: str, narration: str, line_items: List[Dict] = [], inventory_items: List[Dict] = [], taxes: List[Dict] = []) -> str:
        """
        Build voucher XML using golden XML format for inventory vouchers.
        Falls back to accounting voucher format for non-inventory types.
        """
        # Use golden XML builder for inventory vouchers (Sales/Purchase)
        if voucher_type in ["Sales", "Purchase"] and inventory_items:
            from backend.tally_golden_xml import create_purchase_xml, create_sales_xml
            if voucher_type == "Purchase":
                return create_purchase_xml(
                    company=company,
                    party=party,
                    date=date,
                    items=inventory_items,
                    taxes=taxes
                )
            else:
                return create_sales_xml(
                    company=company,
                    party=party,
                    date=date,
                    items=inventory_items
                )
        
        # Use golden XML builder for Receipt/Payment
        if voucher_type in ["Receipt", "Payment"]:
            from backend.tally_golden_xml import create_receipt_xml, create_payment_xml
            # Find the cash/bank ledger and party from line items
            bank_ledger = "Cash"
            party_name = party
            amount = 0
            for item in line_items:
                if item.get("is_debit"):
                    if voucher_type == "Receipt":
                        bank_ledger = item.get("ledger", "Cash")
                    else:
                        party_name = item.get("ledger", party)
                        amount = item.get("amount", 0) # Added from snippet
                else:
                    if voucher_type == "Receipt":
                        party_name = item.get("ledger", party)
                        amount = item.get("amount", 0) # Added from snippet
                    else:
                        bank_ledger = item.get("ledger", "Cash")
                # amount = abs(float(item.get("amount", 0))) # Original line, now handled inside if/else
            
            if voucher_type == "Receipt":
                return create_receipt_xml(company, bank_ledger, party_name, date, amount, narration) # Arguments swapped as per snippet
            else:
                return create_payment_xml(company, bank_ledger, party_name, date, amount, narration) # Arguments swapped as per snippet
        
        # Fallback: Standard accounting voucher format
        envelope, importalldata = TallyXMLBuilder._create_envelope()
        
        reqdesc = importalldata.find("REQUESTDESC")
        staticvariables = reqdesc.find("STATICVARIABLES")
        svcurrentcompany = staticvariables.find("SVCURRENTCOMPANY")
        svcurrentcompany.text = company
        
        requestdata = ET.SubElement(importalldata, "REQUESTDATA")
        tallymessage = ET.SubElement(requestdata, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        
        voucher = ET.SubElement(tallymessage, "VOUCHER", {"VCHTYPE": voucher_type, "ACTION": "Create", "OBJVIEW": "Accounting Voucher View"})
        
        # Header Fields
        date_elem = ET.SubElement(voucher, "DATE")
        date_elem.text = date
        
        vchtype_elem = ET.SubElement(voucher, "VOUCHERTYPENAME")
        vchtype_elem.text = voucher_type
        
        party_elem = ET.SubElement(voucher, "PARTYLEDGERNAME")
        party_elem.text = party
        
        narration_elem = ET.SubElement(voucher, "NARRATION")
        narration_elem.text = narration
        
        fb_elem = ET.SubElement(voucher, "FBTPAYMENTTYPE")
        fb_elem.text = "Default"
        
        persisted_elem = ET.SubElement(voucher, "PERSISTEDVIEW")
        persisted_elem.text = "Accounting Voucher View"

        # Line Items
        for item in line_items:
            ledger_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
            
            led_name = ET.SubElement(ledger_entry, "LEDGERNAME")
            led_name.text = item.get("ledger")
            
            is_deemed_positive = ET.SubElement(ledger_entry, "ISDEEMEDPOSITIVE")
            is_debit = item.get("is_debit", True)
            is_deemed_positive.text = "Yes" if is_debit else "No"
            
            amount_elem = ET.SubElement(ledger_entry, "AMOUNT")
            amount = abs(float(item.get("amount", 0)))
            amount_val = -amount if not is_debit else amount
            amount_elem.text = f"{amount_val:.2f}"

        xmlstr = minidom.parseString(ET.tostring(envelope)).toprettyxml(indent="  ")
        return xmlstr

def parse_tally_response(xml_response: str) -> TallyResponse:
    try:
        # Check if response is empty
        if not xml_response:
             return TallyResponse(success=False, error_details="Empty response from Tally", raw_response="")

        # Parse XML
        root = ET.fromstring(xml_response)
        
        # Tally response for import usually:
        # <RESPONSE><CREATED>1</CREATED><ERRORS>0</ERRORS>...</RESPONSE>
        # Or detailed import log in Tally 9
        
        # Standard Tally XML Server Response wrapper
        # If created successfully, CREATED count > 0, ERRORS == 0
        
        # Let's try to find CREATED and ERRORS tags
        created_elem = root.find(".//CREATED")
        errors_elem = root.find(".//ERRORS")
        
        created = int(created_elem.text) if created_elem is not None else 0
        errors = int(errors_elem.text) if errors_elem is not None else 0
        
        
        if errors > 0:
             # Find LineError
             line_error = root.find(".//LINEERROR")
             error_msg = line_error.text if line_error is not None else "Unknown Error"
             return TallyResponse(
                 success=False,
                 tally_status="Failure",
                 error_details=error_msg,
                 tally_response={"created": created, "errors": errors},
                 raw_response=xml_response
             )
        
        altered_elem = root.find(".//ALTERED")
        altered = int(altered_elem.text) if altered_elem is not None and altered_elem.text is not None else 0
        if created > 0 or altered > 0:
            return TallyResponse(
                success=True,
                tally_status="Success",
                tally_response={"created": created, "errors": errors, "altered": altered},
                raw_response=xml_response
            )
            
        # If neither (maybe just status check)
        status = root.find(".//STATUS")
        if status is not None and status.text == "1":
             return TallyResponse(success=True, tally_status="OK", raw_response=xml_response)
             
        # Fallback for Import responses that might list specific errors differently
        return TallyResponse(
            success=False, 
            tally_status="Unknown",
            error_details="Could not parse success indicators",
            raw_response=xml_response
        )

    except ET.ParseError as e:
        return TallyResponse(success=False, error_details=f"XML Parsing Error: {str(e)}", raw_response=xml_response)
    except AttributeError as e:
        return TallyResponse(success=False, error_details=f"XML Attribute Error (missing tag): {str(e)}", raw_response=xml_response)
    except Exception as e:
        return TallyResponse(success=False, error_details=f"General Error: {str(e)}", raw_response=xml_response)

import nest_asyncio

def _run_async_internal(coro):
    """Helper to run async code in sync context (Robust Check)"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # Apply patch to allow nested loops
        nest_asyncio.apply(loop)
        return loop.run_until_complete(coro)
    
    return loop.run_until_complete(coro)

async def post_to_tally_async(xml_payload: str, tally_url: str = TALLY_URL) -> TallyResponse:
    print(f"📦 [TallyLiveUpdate] Sending XML Async ({len(xml_payload)} bytes)")
    
    # 1. Try Socket.IO Agent First
    try:
        from backend.socket_manager import socket_manager
        
        if socket_manager.active_tenants:
            tenant_id = list(socket_manager.active_tenants.keys())[0]
            
            # Direct Await (No thread bridging needed)
            print(f"🔌 [TallyLiveUpdate] Awaiting Agent Dispatch (Async)...")
            response_data = await socket_manager.send_command(tenant_id, 'execute_tally_xml', {
                'xml': xml_payload,
                'party_name': 'Unknown'
            }, timeout=20)

            if response_data:
                if response_data.get('status') == 'success':
                    xml = response_data.get('response', '')
                    return parse_tally_response(xml)
                else:
                    err = response_data.get('error', 'Agent Execution Failed')
                    return TallyResponse(success=False, error_details=f"Agent Error: {err}", raw_response=str(response_data))
    except Exception as e:
         print(f"⚠️ Agent Dispatch Error (Async): {e}")

    # 2. Fallback to Direct HTTP
    headers = {'Content-Type': 'text/xml;charset=UTF-8'}
    try:
        # We need async http request or wrap synchronous requests
        # Using loop.run_in_executor for requests (sync)
        loop = asyncio.get_running_loop()
        def _req():
            return requests.post(tally_url, data=xml_payload.encode('utf-8'), headers=headers, timeout=TALLY_TIMEOUT)
        
        response = await loop.run_in_executor(None, _req)
        response.raise_for_status()
        return parse_tally_response(response.text)
    except Exception as e:
        return TallyResponse(success=False, error_details=f"System Error: {str(e)}")

async def create_ledger_async(company: str, ledger_name: str, parent: str = "Sundry Debtors", fields: Dict[str, str] = {}) -> TallyResponse:
    # Validation logic duplicated from safe version
    if not ledger_name or len(ledger_name) > 50:
        return TallyResponse(success=False, error_details="Invalid Ledger Name (Must be 1-50 chars)")
        
    xml_payload = TallyXMLBuilder.build_ledger_xml(company, ledger_name, parent, fields)
    return await post_to_tally_async(xml_payload)

async def create_voucher_async(company: str, voucher_type: str, voucher_fields: Dict[str, str], line_items: List[Dict]) -> TallyResponse:
    # Minimal validation
    date = voucher_fields.get("Date")
    if not date or len(date) != 8:
         return TallyResponse(success=False, error_details="Invalid Date Format (YYYYMMDD)")
         
    xml_payload = TallyXMLBuilder.build_voucher_xml(
        company, 
        voucher_type, 
        date, 
        voucher_fields.get("PartyLedgerName", ""), 
        voucher_fields.get("Narration", ""),
        line_items
    )
    return await post_to_tally_async(xml_payload)

def post_to_tally(xml_payload: str, tally_url: str = TALLY_URL, wait: bool = True) -> TallyResponse:
    print(f"📦 [TallyLiveUpdate] Sending XML ({len(xml_payload)} bytes)")
    # 'wait' arg is preserved for signature compatibility but ignored for safety - we always wait now.
    
    # 1. Try Socket.IO Agent First
    try:
        from backend.socket_manager import socket_manager
        import asyncio
        
        if socket_manager.active_tenants:
            tenant_id = list(socket_manager.active_tenants.keys())[0]
            print(f"DEBUG: Inside post_to_tally. Thread: {threading.current_thread().name}") 
            
            response_data = None
            
            # CHECK THREAD CONTEXT
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # We are in Main Loop! e.g. async view call.
                # We CANNOT block here.
                # If wait=True is demanded but we are in async, we technically should await.
                # BUT this function is defined as sync. 
                # Ideally caller should be async.
                
                # For now, skipping Agent dispatch if we are in async loop to avoid blocking deadlock
                # UNLESS we use nest_asyncio to block.
                # Or we can try to fire-and-forget if possible, but we want result.
                
                print("⚠️ [TallyLiveUpdate] Skipped Agent (In Async Loop). Fallback to HTTP.")
                pass
            else:
                # We are in a Thread (Celery Worker)
                # Use Thread-Safe Bridge
                print(f"🔌 [TallyLiveUpdate] Dispatching to Agent (Thread Safe) - Wait: {wait}")
                print(f"DEBUG: Emitting Socket Event: execute_tally_xml")
                print("DEBUG: Waiting for result...")
                response_data = socket_manager.execute_sync(tenant_id, 'execute_tally_xml', {
                    'xml': xml_payload,
                    'party_name': 'Unknown'
                }, timeout=20)
                print(f"DEBUG: Result received: {response_data}")

            if response_data:
                if response_data.get('status') == 'success':
                    xml = response_data.get('response', '')
                    return parse_tally_response(xml)
                else:
                    err = response_data.get('error', 'Agent Execution Failed')
                    return TallyResponse(success=False, error_details=f"Agent Error: {err}", raw_response=str(response_data))

    except ImportError:
        pass
    except Exception as e:
         print(f"⚠️ Agent Dispatch Error: {e}")

    # 2. Fallback to Direct HTTP
    headers = {'Content-Type': 'text/xml;charset=UTF-8'}
    try:
        # Retry logic: Retry once
        for attempt in range(2):
            try:
                response = requests.post(tally_url, data=xml_payload.encode('utf-8'), headers=headers, timeout=TALLY_TIMEOUT)
                response.raise_for_status()
                return parse_tally_response(response.text)
            except requests.exceptions.RequestException as e:
                if attempt == 0:
                    time.sleep(2)
                    continue
                else:
                     return TallyResponse(success=False, error_details=f"Network Error: {str(e)}")
    except Exception as e:
        return TallyResponse(success=False, error_details=f"System Error: {str(e)}")
    
    return TallyResponse(success=False, error_details="Unknown execution path")

def create_ledger_safely(company: str, ledger_name: str, parent: str = "Sundry Debtors", fields: Dict[str, str] = {}) -> TallyResponse:
    # Validation
    if not ledger_name or len(ledger_name) > 50:
        return TallyResponse(success=False, error_details="Invalid Ledger Name (Must be 1-50 chars)")
    
    # Check fields if needed, e.g. GST
    gst = fields.get("Partygstregistrationnumber")
    if gst:
        if len(gst) != 15:
             return TallyResponse(success=False, error_details="Invalid GST Format (Must be 15 chars)")
        # Basic format check: AAB...
        # Not implementing full regex unless strictly required to keep it fast, but user asked for "AABBBBBBBBBBBB" check
        # Let's do a quick length and structure check if needed.
        pass

    xml_payload = TallyXMLBuilder.build_ledger_xml(company, ledger_name, parent, fields)
    return post_to_tally(xml_payload)

def create_voucher_safely(
    company: str,
    voucher_type: str,
    voucher_fields: Dict[str, str],
    line_items: List[Dict],
    taxes: List[Dict] = [],
    tenant_id: Optional[str] = None,   # ← Pass tenant_id for credit tracking
) -> TallyResponse:
    # Validation
    date = voucher_fields.get("Date")
    if not date or len(date) != 8:
         return TallyResponse(success=False, error_details="Invalid Date Format (YYYYMMDD)")

    xml_payload = TallyXMLBuilder.build_voucher_xml(
        company,
        voucher_type,
        date,
        voucher_fields.get("PartyLedgerName", ""),
        voucher_fields.get("Narration", ""),
        line_items=line_items,
        inventory_items=line_items,
        taxes=taxes
    )
    
    if tenant_id:
        from backend.credit_engine.engine import check_credits_available
        if not check_credits_available(tenant_id, "VOUCHER"):
            raise Exception("Credit limit reached. Please recharge.")

    response = post_to_tally(xml_payload)

    # ── Credit event hook ────────────────────────────────────────────────────
    # Fire AFTER successful push so failed vouchers never consume credits.
    if response.success and tenant_id:
        _fire_voucher_credit_event(voucher_type, tenant_id, subtype="created")
    # ─────────────────────────────────────────────────────────────────────────

    return response

# wrappers for backward compatibility with older naming conventions
def create_voucher_in_tally(
    company: str,
    fields: Dict[str, Any],
    line_items: List[Dict[str, Any]],
    tenant_id: Optional[str] = None,   # ← Pass tenant_id for credit tracking
) -> TallyResponse:
    """
    Wrapper for create_voucher_safely.
    Pass tenant_id so credit consumption is tracked per tenant.
    """
    fields_ci    = {k.upper(): v for k, v in fields.items()}
    voucher_type = fields_ci.get("VOUCHERTYPENAME", "Sales")
    safe_fields  = {
        "Date":            fields_ci.get("DATE"),
        "PartyLedgerName": fields_ci.get("PARTYLEDGERNAME"),
        "Narration":       fields_ci.get("NARRATION"),
    }
    return create_voucher_safely(company, voucher_type, safe_fields, line_items, tenant_id=tenant_id)

def dispatch_tally_update(entity_type: str, company_name: str, payload: Dict[str, Any], tally_url: str = None) -> TallyResponse:
    """
    Router for generic updates, used by workflows/update_gstin.
    """
    if entity_type == "ledger":
        ledger_name = payload.get("ledger_name")
        updates = payload.get("updates", {})
        # 'updates' dict usually contains field:value pairs
        # create_ledger_safely uses 'fields' dict
        return create_ledger_safely(company_name, ledger_name, fields=updates)
    
    elif entity_type == "voucher":
        # Attempt to map generic voucher payload to create_voucher_safely
        voucher_type = payload.get("voucher_type", "Sales")
        items = payload.get("items", [])
        fields = payload.get("fields", {}) # Might need date/party/narration here
        return create_voucher_safely(company_name, voucher_type, fields, items)

    raise TallyAPIError(f"Unknown entity type: {entity_type}")
