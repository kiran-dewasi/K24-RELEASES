
import logging
import requests
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VERIFY_PUSH")

TALLY_URL = "http://localhost:9000"
COMPANY_NAME = "SHREEJI SALES CORPORATION"

def check_tally_connection():
    """Verify Tally is reachable"""
    logger.info(f"Using Tally URL: {TALLY_URL}")
    try:
        # Simple test payload
        payload = "<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Companies</REPORTNAME></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"
        resp = requests.post(TALLY_URL, data=payload, timeout=5)
        
        if resp.status_code == 200:
            logger.info("✅ Tally is Reachable!")
            logger.info(f"   Response Preview: {resp.text[:100]}...")
            return True
        else:
            logger.error(f"❌ Tally returned status {resp.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Connection Failed: {e}")
        return False

def create_test_ledger():
    """Attempt to create a test ledger to verify PUSH capability"""
    ledger_name = f"K24 Test Ledger {datetime.now().strftime('%H%M%S')}"
    logger.info(f"🚀 Attempting to create ledger: '{ledger_name}'")
    
    xml = f"""<ENVELOPE>
        <HEADER>
            <TALLYREQUEST>Import Data</TALLYREQUEST>
        </HEADER>
        <BODY>
            <IMPORTDATA>
                <REQUESTDESC>
                    <REPORTNAME>All Masters</REPORTNAME>
                    <STATICVARIABLES>
                        <SVCURRENTCOMPANY>{COMPANY_NAME}</SVCURRENTCOMPANY>
                    </STATICVARIABLES>
                </REQUESTDESC>
                <REQUESTDATA>
                    <TALLYMESSAGE xmlns:UDF="TallyUDF">
                        <LEDGER NAME="{ledger_name}" ACTION="Create">
                            <NAME.LIST>
                                <NAME>{ledger_name}</NAME>
                            </NAME.LIST>
                            <PARENT>Suspense A/c</PARENT>
                            <OPENINGBALANCE>100</OPENINGBALANCE>
                            <ISBILLWISEON>No</ISBILLWISEON>
                        </LEDGER>
                    </TALLYMESSAGE>
                </REQUESTDATA>
            </IMPORTDATA>
        </BODY>
    </ENVELOPE>"""
    
    try:
        headers = {'Content-Type': 'application/xml'}
        resp = requests.post(TALLY_URL, data=xml, headers=headers, timeout=10)
        
        logger.info(f"   Status Code: {resp.status_code}")
        
        # Analyze Response
        resp_text = resp.text
        
        if "<CREATED>1</CREATED>" in resp_text:
            logger.info(f"✅ SUCCESS: Ledger '{ledger_name}' created!")
            return True
        elif "<ALTERED>1</ALTERED>" in resp_text:
            logger.info(f"✅ SUCCESS: Ledger '{ledger_name}' updated (already existed).")
            return True
        elif "<ERRORS>0</ERRORS>" in resp_text:
             logger.info(f"✅ SUCCESS: No errors reported (Created/Altered).")
             return True
        else:
            # Extract Error
            logger.error("❌ FAILURE: Tally rejected the request.")
            logger.error(f"   Response: {resp_text}")
            
            # Simple error parsing
            try:
                root = ET.fromstring(resp_text)
                line_error = root.findtext(".//LINEERROR")
                if line_error:
                    logger.error(f"   Reason: {line_error}")
            except:
                pass
            return False

    except Exception as e:
        logger.error(f"❌ Push Exception: {e}")
        return False

if __name__ == "__main__":
    if check_tally_connection():
        create_test_ledger()
    else:
        logger.warning("⚠️ Skipping push test as Tally is offline.")
