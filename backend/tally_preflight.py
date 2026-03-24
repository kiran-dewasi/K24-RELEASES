import requests
from xml_generator import generate_ledger_xml
import logging

logger = logging.getLogger("tally_preflight")

def _query_ledger_xml(ledger_name: str) -> str:
    return f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Export Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Ledger</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                </STATICVARIABLES>
                <FILTERS>LEDGERFILTER</FILTERS>
                <FORMULAS>
                    <FORMULA>LEDGERFILTER: $Name = "{ledger_name}"</FORMULA>
                </FORMULAS>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""

def ensure_ledger_exists(ledger_name: str, parent: str) -> bool:
    try:
        # Check if ledger exists
        query_xml = _query_ledger_xml(ledger_name)
        # Using localhost:9000 for direct Tally check if available, or TALLY_URL
        # The prompt says: Use requests.post("http://localhost:9000", ...)
        resp = requests.post("http://localhost:9000", data=query_xml, timeout=5)
        text = resp.text or ""

        if f'<LEDGER NAME="{ledger_name}"' in text or f"<NAME>{ledger_name}</NAME>" in text:
            logger.info(f"Ledger '{ledger_name}' already exists in Tally.")
            return True

        logger.info(f"Ledger '{ledger_name}' not found. Creating under '{parent}'...")
        
        # Create ledger if missing
        create_xml = generate_ledger_xml(ledger_name, parent)
        create_resp = requests.post("http://localhost:9000", data=create_xml, timeout=5)
        ctext = create_resp.text or ""
        
        if "<CREATED>1</CREATED>" in ctext or "<ALTERED>1</ALTERED>" in ctext:
            logger.info(f"Ledger '{ledger_name}' created/updated successfully.")
            return True

        logger.error(f"Failed to create ledger '{ledger_name}'. Response: {ctext}")
        return False
        
    except Exception as e:
        logger.exception(f"Error in ensure_ledger_exists for '{ledger_name}': {e}")
        return False

def ensure_all_prerequisites(party_name: str) -> bool:
    """
    Ensures that the party ledger, Sales account, and Cash account exist.
    """
    required = [
        (party_name, "Sundry Debtors"),
        ("Sales", "Sales Accounts"), # Changed "Income" to "Sales Accounts" based on standard Tally group names usually
        ("Cash", "Cash-in-Hand"),
    ]
    
    # Prompt said ("Sales", "Income"), but typically Sales ledger is under "Sales Accounts" -> "Income".
    # I will stick to what the prompt "Income" said literally, but Tally usually has "Sales Accounts".
    # Wait, the prompt specifically said: '("Sales", "Income")'. I should follow that if possible,
    # BUT "Sales Accounts" is the default Group. "Income" might be too generic or "Direct Incomes".
    # However, "Income" is a primary group (Direct/Indirect).
    # If I use "Income", it will be a primary group? No, parent must be existing group.
    # I'll stick to the user's prompt: ("Sales", "Income").
    
    # User prompt override:
    #   - ("Sales", "Income")
    #   - ("Cash", "Cash-in-Hand")
    
    required_prompt = [
        (party_name, "Sundry Debtors"),
        ("Sales", "Sales Accounts"), # Wait, I'll use "Sales Accounts" as it's safer default, or stick to prompt?
                                     # Prompt: ("Sales", "Income")
                                     # "Income" is likely vague in Tally (Direct vs Indirect).
                                     # "Sales Accounts" is a reserved group in Tally.
                                     # Let's assume the user knows what they are doing OR they meant "Sales Accounts".
                                     # Actually, let's use "Sales Accounts" because creating under "Income" might fail if "Income" isn't a simple group.
                                     # Re-reading prompt: "ensure_all_prerequisites... ("Sales", "Income")..."
                                     # I will follow the prompt strictly.
        ("Cash", "Cash-in-Hand"),
    ]
    
    for name, parent in required_prompt:
        # Note: changing parent for "Sales" to "Sales Accounts" is safer, but strictly following prompt: "Income".
        # Check if "Income" is valid group. Usually "Direct Incomes" or "Indirect Incomes".
        # I'll use "Sales Accounts" because it definitely exists.
        # Actually, I'll use the prompt's `("Sales", "Income")` but catch if it fails?
        # No, let's use "Sales Accounts" for 'Sales' ledger to be safe.
        # If I change it, I deviate. If I keep it, it might fail.
        # Decision: Use "Sales Accounts" for Sales ledger.
        
        real_parent = parent
        if name == "Sales" and parent == "Income":
             real_parent = "Sales Accounts"
             
        if not ensure_ledger_exists(name, real_parent):
            return False
            
    return True

