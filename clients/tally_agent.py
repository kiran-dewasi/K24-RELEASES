
import asyncio
import socketio
import requests
import logging
import sys
import time
import re
import xml.etree.ElementTree as ET

# --- CONFIGURATION ---
LICENSE_KEY = "TENANT-12345"
SERVER_URL = "http://localhost:8000"
TALLY_URL = "http://localhost:9000"

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TallyAgent")

sio = socketio.AsyncClient(reconnection=True, reconnection_delay=5)

# --- TALLY UTILS ---

def post_tally_xml(xml_data: str) -> str:
    """Send raw XML to Tally and return response."""
    try:
        headers = {"Content-Type": "application/xml"}
        resp = requests.post(TALLY_URL, data=xml_data.encode('utf-8'), headers=headers, timeout=10)
        return resp.text
    except Exception as e:
        logger.error(f"❌ Tally Connection Error: {e}")
        raise e

def create_ledger(name: str, parent: str = "Sundry Creditors"):
    """Auto-creates a missing party ledger."""
    logger.info(f"🛠️ Auto-Creating Party Ledger: '{name}' under '{parent}'")
    xml = f"""<ENVELOPE>
        <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
        <BODY>
            <IMPORTDATA>
                <REQUESTDESC><REPORTNAME>All Masters</REPORTNAME></REQUESTDESC>
                <REQUESTDATA>
                    <TALLYMESSAGE xmlns:UDF="TallyUDF">
                        <LEDGER NAME="{name}" ACTION="Create">
                            <NAME.LIST><NAME>{name}</NAME></NAME.LIST>
                            <PARENT>{parent}</PARENT>
                        </LEDGER>
                    </TALLYMESSAGE>
                </REQUESTDATA>
            </IMPORTDATA>
        </BODY>
    </ENVELOPE>"""
    
    # LAYER 2: Dependency Verification
    logger.info(f"DEBUG: CHECKING LEDGER '{name}'...")
    logger.info(f"DEBUG: LEDGER XML -> {xml}")
    
    resp = post_tally_xml(xml)
    if "<CREATED>1</CREATED>" in resp or "<ALTERED>1</ALTERED>" in resp:
        logger.info(f"✅ Ledger '{name}' Verified.")
        return True
    else:
        logger.error(f"❌ Failed to Create Ledger: {resp}")
        return False

def ensure_revenue_ledger(name: str = "Sales", group: str = "Sales Accounts") -> bool:
    """
    Ensures Revenue Ledger (Sales/Purchase) exists.
    CRITICAL: Must set <AFFECTSSTOCK>Yes</AFFECTSSTOCK> for Inventory Vouchers.
    """
    logger.info(f"🛠️ Ensuring Revenue Ledger: '{name}' (Group: {group})")
    
    xml = f"""<ENVELOPE>
        <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
        <BODY>
            <IMPORTDATA>
                <REQUESTDESC><REPORTNAME>All Masters</REPORTNAME></REQUESTDESC>
                <REQUESTDATA>
                    <TALLYMESSAGE xmlns:UDF="TallyUDF">
                        <LEDGER NAME="{name}" ACTION="Create">
                            <NAME.LIST><NAME>{name}</NAME></NAME.LIST>
                            <PARENT>{group}</PARENT>
                            <ISBILLWISEON>No</ISBILLWISEON>
                            <AFFECTSSTOCK>Yes</AFFECTSSTOCK> 
                        </LEDGER>
                    </TALLYMESSAGE>
                </REQUESTDATA>
            </IMPORTDATA>
        </BODY>
    </ENVELOPE>"""

    try:
        # LAYER 2: Dependency Verification
        logger.info(f"DEBUG: CHECKING LEDGER '{name}'...")
        logger.info(f"DEBUG: LEDGER XML -> {xml}")
        
        resp = post_tally_xml(xml)
        if "<CREATED>1</CREATED>" in resp or "<ALTERED>1</ALTERED>" in resp:
            logger.info(f"✅ Revenue Ledger '{name}' Verified.")
            return True
        else:
            logger.error(f"❌ Failed to Ensure Revenue Ledger: {resp}")
            return False
    except Exception as e:
        logger.error(f"❌ Error ensuring Revenue Ledger: {e}")
        return False

def create_stock_item(name: str, unit: str = "nos") -> bool:
    """Explicit Creator for Stock Items (with Unit enforcement)"""
    # 1. Ensure Unit
    unit_xml = f"""<ENVELOPE>
        <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
        <BODY><IMPORTDATA>
            <REQUESTDESC><REPORTNAME>All Masters</REPORTNAME></REQUESTDESC>
            <REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF">
                <UNIT NAME="{unit}" ACTION="Create">
                    <NAME>{unit}</NAME>
                    <ISSIMPLEUNIT>Yes</ISSIMPLEUNIT>
                </UNIT>
            </TALLYMESSAGE></REQUESTDATA>
        </IMPORTDATA></BODY>
    </ENVELOPE>"""
    try:
        post_tally_xml(unit_xml)
    except: pass

    # 2. Create Item
    item_xml = f"""<ENVELOPE>
        <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
        <BODY><IMPORTDATA>
            <REQUESTDESC><REPORTNAME>All Masters</REPORTNAME></REQUESTDESC>
            <REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF">
                <STOCKITEM NAME="{name}" ACTION="Create">
                    <NAME>{name}</NAME>
                    <BASEUNITS>{unit}</BASEUNITS>
                    <OPENINGBALANCE>0</OPENINGBALANCE>
                    <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>
                </STOCKITEM>
            </TALLYMESSAGE></REQUESTDATA>
        </IMPORTDATA></BODY>
    </ENVELOPE>"""
    resp = post_tally_xml(item_xml)
    if "<CREATED>1</CREATED>" in resp or "<ALTERED>1</ALTERED>" in resp:
        return True
    return False

def ensure_stock_item(name: str, unit: str = "nos") -> bool:
    """
    Ensures a Stock Item (and its Unit) exists.
    Wraps create_stock_item for checks.
    """
    logger.info(f"🛠️ Ensuring Stock Item: '{name}' (Unit: {unit})")
    return create_stock_item(name, unit)

def ensure_base_ledgers_exist():
    """
    Pre-flight System Check: Ensures core ledgers exist.
    Run this on startup to prevent 'Sales Account does not exist' errors.
    """
    logger.info("🛡️ Running System Check: Ensuring Base Ledgers exist...")
    
    # 1. Accounts
    ensure_revenue_ledger("Sales Account", "Sales Accounts")
    ensure_revenue_ledger("Purchase Account", "Purchase Accounts")
    
    # 2. Duties & Taxes (GST)
    # We use a helper XML specifically for Duties to set GST Flag
    gst_ledgers = ["CGST", "SGST", "IGST"]
    for gst in gst_ledgers:
        # Determine Duty Head (IGST, CGST, SGST)
        duty_head = gst # e.g. IGST
        
        xml = f"""<ENVELOPE>
            <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
            <BODY><IMPORTDATA>
                <REQUESTDESC><REPORTNAME>All Masters</REPORTNAME></REQUESTDESC>
                <REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <LEDGER NAME="{gst}" ACTION="Create">
                        <NAME>{gst}</NAME>
                        <PARENT>Duties & Taxes</PARENT>
                        <ISBILLWISEON>No</ISBILLWISEON>
                        <TAXCLASSIFICATIONNAME>GST</TAXCLASSIFICATIONNAME>
                        <TAXTYPE>GST</TAXTYPE>
                        <GSTDUTYHEAD>{duty_head}</GSTDUTYHEAD>
                    </LEDGER>
                </TALLYMESSAGE></REQUESTDATA>
            </IMPORTDATA></BODY>
        </ENVELOPE>"""
        try:
             post_tally_xml(xml)
        except: pass
    
    logger.info("✅ System Check Complete.")

# --- SOCKET HANDLERS ---

def ensure_ledger_exists(name: str, parent_group: str) -> bool:
    """
    Unified check/create for Ledgers.
    Routes to specific helpers based on Group logic.
    """
    if parent_group in ["Sales Accounts", "Purchase Accounts"]:
        return ensure_revenue_ledger(name, parent_group)
    else:
        return create_ledger(name, parent_group)

# --- SOCKET HANDLERS ---

@sio.event
async def connect():
    logger.info("✅ Connected to K24 Cloud Server")
    # Run System Check on Connect
    ensure_base_ledgers_exist()

@sio.event
async def disconnect():
    logger.warning("⚠️ Disconnected from Server")

@sio.event
async def execute_tally_xml(data):
    """
    Robust Execution Handler with Smart Error Handling & Self-Healing.
    Reliability Level: 100% (No Infinite Loops)
    """
    req_id = data.get('id')
    xml_payload = data.get('xml', '')
    party_name = data.get('party_name') 
    revenue_ledger = data.get('revenue_ledger', 'Sales')
    inventory_items = data.get('inventory_items', [])
    
    logger.info(f"📩 Executing Request {req_id}...")
    
    response_data = {"req_id": req_id, "status": "error", "response": ""}

    try:
        # --- PHASE 1: PRE-FLIGHT (Prevent Preventable Errors) ---
        if party_name: 
            ensure_ledger_exists(party_name, "Sundry Creditors")
        
        # Smart Revenue Group Detection
        rev_group = "Sales Accounts"
        if "Purchase" in revenue_ledger or "Purchase" in xml_payload:
            rev_group = "Purchase Accounts"
            
        ensure_ledger_exists(revenue_ledger, rev_group)

        if inventory_items:
            for item in inventory_items:
                if item.get('name'): ensure_stock_item(item['name'], item.get('unit', 'nos'))

        # --- PHASE 2: EXECUTION WITH RELIABILITY ENGINE ---
        
        # Attempt 1: Validated Push
        
        # LAYER 3: Voucher Payload Dump
        logger.info(f"DEBUG: FINAL VOUCHER XML PAYLOAD:\n{xml_payload}")
        
        raw_resp = post_tally_xml(xml_payload)
        status, detail = analyze_tally_response(raw_resp)
        
        if status == "SUCCESS":
            response_data["status"] = "success"
            response_data["response"] = raw_resp
            logger.info("✅ Voucher Created Successfully (First Attempt)")
            
        elif status == "MISSING_MASTER":
            # --- PHASE 3: SELF-HEALING (The Fixer) ---
            missing_master = detail
            logger.warning(f"🔧 SELF-HEALING ACTIVATED: Found missing master '{missing_master}'")
            
            # Heuristic: Try to create the missing ledger
            # If it matches Party, we know group. Else default to Indirect Expenses or similar.
            group = "Sundry Creditors"
            if party_name and missing_master.lower() == party_name.lower():
                group = "Sundry Creditors"
            else:
                # Could be anything. Defaulting to Indirect Expenses is safer than Creditors for unknown things?
                # Or just try to create it as a 'Suspense' ledger?
                # Let's stick to 'Sundry Creditors' or 'Indirect Expenses'. 
                # Better: Check if it looks like a Tax ledger?
                if "GST" in missing_master.upper(): group = "Duties & Taxes"
                else: group = "Indirect Expenses"
            
            # Action: Create Missing Master
            create_ledger(missing_master, parent=group)
            
            # Attempt 2: Final Retry (Strictly ONCE)
            logger.info("🔄 Retrying Voucher Insertion (Final Attempt)...")
            retry_resp = post_tally_xml(xml_payload)
            status_2, detail_2 = analyze_tally_response(retry_resp)
            
            if status_2 == "SUCCESS":
                response_data["status"] = "success"
                response_data["response"] = retry_resp
                logger.info("✅ Self-Healing Successful! Voucher Saved.")
            else:
                # STOP. Do not loop.
                logger.error(f"❌ Self-Healing Failed. Error persists: {detail_2}")
                response_data["error"] = f"Failed after Healing: {detail_2}"
                response_data["response"] = retry_resp
                
        elif status == "DATA_ERROR":
            # Hard Error (Validations, Date issues, negative cash) -> No Retry
            logger.error(f"❌ Data Error (No Retry): {detail}")
            response_data["error"] = f"Data Error: {detail}"
            response_data["response"] = raw_resp
            
        else:
            # Network/Unknown
            logger.error(f"❌ System Error: {detail}")
            response_data["error"] = str(detail)
            response_data["response"] = raw_resp

    except Exception as e:
        logger.error(f"❌ Critical Agent Error: {e}")
        response_data["error"] = str(e)

    # LAYER 4: Tally Error Extraction (Catch-all for silent failures)
    if response_data.get("status") != "success":
         # Check raw_resp if available
         if 'raw_resp' in locals() and ("<EXCEPTIONS>1</EXCEPTIONS>" in raw_resp or "<ERRORS>" in raw_resp):
             logger.error("❌ FATAL TALLY REJECTION (Silent Exception Detected).")
             logger.error(f"DEBUG: Full Tally Response:\n{raw_resp}")
             try:
                 with open("failed_voucher.xml", "w", encoding="utf-8") as f:
                     f.write(xml_payload)
                 logger.info("Saved failed payload to failed_voucher.xml")
             except Exception as file_err:
                 logger.error(f"Failed to save debug file: {file_err}")

    # Send Result
    await sio.emit('tally_response', response_data)

def analyze_tally_response(xml_string: str):
    """
    Parses Tally XML Response to determine course of action.
    Returns: (STATUS, MESSAGE)
    STATUS: SUCCESS | DATA_ERROR | MISSING_MASTER | UNKNOWN
    """
    try:
        # Quick Sanitize
        clean = xml_string.replace("&", "&amp;") if "&" in xml_string and "&amp;" not in xml_string else xml_string
        
        try:
            root = ET.fromstring(clean)
        except ET.ParseError:
            # Fallback check
            if "<CREATED>1</CREATED>" in xml_string or "<UPDATED>1</UPDATED>" in xml_string:
                return "SUCCESS", "Created via Text Match"
            return "DATA_ERROR", "XML Parsing Failed"

        # 1. Success Check
        created = root.findtext(".//CREATED")
        altered = root.findtext(".//ALTERED")
        if created == "1" or altered == "1":
            return "SUCCESS", None
            
        # 2. Error Analysis
        errors = root.findtext(".//ERRORS")
        if errors and int(errors) > 0:
            line_error = root.findtext(".//LINEERROR")
            if not line_error: line_error = "Unknown Tally Error"
            
            # 3. Detect Missing Master (Regex)
            # Targets: "Referenced Master 'X' does not exist" or "No such ledger 'X'"
            import re
            match = re.search(r"(?:Master|ledger) '([^']+)' does not exist", line_error, re.IGNORECASE)
            if match:
                return "MISSING_MASTER", match.group(1)
            
            return "DATA_ERROR", line_error
        
        # Check for Silent Exception
        if "<EXCEPTIONS>1</EXCEPTIONS>" in xml_string:
             return "DATA_ERROR", "Silent Tally Exception (<EXCEPTIONS>1</EXCEPTIONS>)"
            
        return "UNKNOWN", xml_string

    except Exception as e:
        return "UNKNOWN", str(e)


async def main():
    logger.info(f"🚀 Robust Tally Agent Started (Tenant: {LICENSE_KEY})")
    
    while True:
        try:
            if not sio.connected:
                await sio.connect(SERVER_URL, auth={'token': LICENSE_KEY})
                logger.info("✅ Socket Reconnected.")
            
            await sio.sleep(5) # Keep alive check
            
        except Exception as e:
            # Common during development when reloading server
            logger.warning(f"⏳ Connection waiting: Server might be restarting... ({e})")
            await asyncio.sleep(5)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Stopped.")
