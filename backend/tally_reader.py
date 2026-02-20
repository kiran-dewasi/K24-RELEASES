import requests
import xml.etree.ElementTree as ET
import logging
import re
from typing import List, Dict, Any, Optional

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TallyReader")

class TallyReader:
    """
    Simplified Tally Reader using 'List of Accounts' Dump strategy.
    Replaces complex TDL query logic with a robust Cache-First approach.
    """

    def __init__(self, tally_url: str = "http://localhost:9000", debug_xml: bool = False):
        self.tally_url = tally_url
        self.debug_xml = debug_xml
        self.ledger_cache: Dict[str, str] = {} # Key: Lowercase Name, Value: Actual Name
        self.item_cache: Dict[str, str] = {}
        self.cache_populated = False

    def _clean_xml(self, xml_string: str) -> str:
        """Removes invalid characters to ensure ElementTree can parse it."""
        # Remove all control characters (0-31) except Tab(9), LF(10), CR(13)
        xml_string = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', xml_string)
        
        # Remove encoded entities for control chars (e.g., &#x0;, &#11;, &#x1B;)
        # Pattern: &#(x[0-9a-fA-F]+|[0-9]+);
        def entity_replacer(match):
            entity = match.group(1)
            try:
                if entity.lower().startswith('x'):
                    code = int(entity[1:], 16)
                else:
                    code = int(entity)
                
                # Check if invalid (Range 0-8, 11-12, 14-31)
                if (0 <= code <= 8) or (code in [11, 12]) or (14 <= code <= 31):
                    return "" # Remove it
                
                return match.group(0) # Keep valid
            except:
                return match.group(0)

        xml_string = re.sub(r'&#(x[0-9a-fA-F]+|[0-9]+);', entity_replacer, xml_string)
        return xml_string

    def fetch_all_masters(self):
        """
        Fetches ALL Ledgers and Stock Items from Tally and caches them.
        Uses the 'List of Accounts' report which is reliable for listing existence.
        """
        # "List of Accounts" returns Ledgers and Groups (and potentially Items if configured, but usually ACCOUNTTYPE controls it)
        # To get Ledgers specifically:
        xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME>
    <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <ACCOUNTTYPE>Ledgers</ACCOUNTTYPE> 
    </STATICVARIABLES>
    </REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>"""
        
        try:
            logger.info("🔄 REFRESHING CACHE: Fetching List of Accounts (Ledgers)...")
            r = requests.post(self.tally_url, data=xml, timeout=15)
            if r.status_code != 200:
                logger.error(f"Tally HTTP Error: {r.status_code}")
                return

            root = ET.fromstring(self._clean_xml(r.text))
            
            # Reset Cache
            self.ledger_cache = {}
            count = 0

            # Parse TALLYMESSAGE -> LEDGER
            # Parse LEDGER elements directly
            for ledger in root.findall(".//LEDGER"):
                name = ledger.get("NAME") or ledger.findtext("NAME")
                
                if name:
                    # Store in cache
                    self.ledger_cache[name.strip().lower()] = name.strip()
                    count += 1
            
            logger.info(f"✅ Cache Updated: Found {count} Ledgers.")
            self.cache_populated = True

        except Exception as e:
            logger.error(f"❌ Failed to fetch masters: {e}")

    def fetch_all_items(self):
        """Fetches Stock Items."""
        xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME>
    <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <ACCOUNTTYPE>Stock Items</ACCOUNTTYPE> 
    </STATICVARIABLES>
    </REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>"""
        try:
            logger.info("🔄 REFRESHING CACHE: Fetching Stock Items...")
            r = requests.post(self.tally_url, data=xml, timeout=15)
            root = ET.fromstring(self._clean_xml(r.text))
            
            self.item_cache = {}
            count = 0

            for item in root.findall(".//STOCKITEM"):
                name = item.get("NAME") or item.findtext("NAME")
                    
                if name:
                    self.item_cache[name.strip().lower()] = name.strip()
                    count += 1
            
            logger.info(f"✅ Cache Updated: Found {count} Items.")

        except Exception as e:
            logger.error(f"❌ Failed to fetch items: {e}")


    def check_ledger_exists(self, ledger_name: str) -> Optional[str]:
        """
        Exact (Case-Insensitive) Lookup in Cache.
        Returns: Actual Name if found, None otherwise.
        """
        if not self.cache_populated:
            self.fetch_all_masters()
            
        key = ledger_name.strip().lower()
        if key in self.ledger_cache:
            return self.ledger_cache[key]
        
        # If not found, maybe cache is stale? 
        # For now, trust cache. If we want to be safe, we could re-fetch if not found, 
        # but that defeats the purpose of cache during bulk ops.
        # Let's assume one refresh per session is okay, or explicit refresh.
        return None

    def get_ledger_state(self, ledger_name: str) -> Optional[str]:
        """
        Fetch State Name for a specific ledger.
        """
        xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME>
    <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <ACCOUNTTYPE>Ledgers</ACCOUNTTYPE> 
    </STATICVARIABLES>
    <TDL>
        <OBJECT NAME="Ledger">
            <NAME>{escape(ledger_name)}</NAME> 
            <FETCH>Name,StateName</FETCH>
        </OBJECT>
    </TDL>
    </REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>"""
        try:
            # We must filter by specific Object name, but TDL pattern above finds all.
            # Using valid Tally Collection filter is better.
            
            # Revised TDL for specific ledger
            xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>List of Accounts</REPORTNAME>
                <STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES>
                <TDL>
                    <COLLECTION NAME="SpecificLedger">
                        <TYPE>Ledger</TYPE>
                        <EVALUATE>LedgerState: $StateName</EVALUATE>
                        <FILTERS>TargetFilter</FILTERS>
                    </COLLECTION>
                    <SYSTEM TYPE="Formulae" NAME="TargetFilter">$Name = "{escape(ledger_name)}"</SYSTEM>
                </TDL>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
            
            # Alternative: Search collection of one.
            # Tally is finicky. Let's use get_ledgers but simplified? 
            # Or just use fetch_and_parse on a collection with filter.
            
            r = requests.post(self.tally_url, data=xml, headers={'Content-Type': 'text/xml'}, timeout=5)
            root = ET.fromstring(self._clean_xml(r.text))
            
            # The EVALUATE field might appear as <LEDGERSTATE> or similar custom tag?
            # Actually with COLLECTION, fields appear as methods.
            # Let's try simpler: Object context.
            
            # Simpler XML that works reliably for single object properties:
            xml_simple = f"""<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES><TDL><COLLECTION NAME="SL"><TYPE>Ledger</TYPE><FETCH>Name,StateName</FETCH><FILTER>IsMyLedger</FILTER></COLLECTION><SYSTEM TYPE="Formulae" NAME="IsMyLedger">$Name="{escape(ledger_name)}"</SYSTEM></TDL></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"""
            
            r = requests.post(self.tally_url, data=xml_simple, timeout=5)
            root = ET.fromstring(self._clean_xml(r.text))
            
            for l in root.findall(".//LEDGER"):
                return l.findtext("STATENAME")
                
            return None
            
        except Exception as e:
            logger.error(f"Error fetching Ledger State: {e}")
            return None        

    def get_ledger_guid(self, ledger_name: str) -> Optional[str]:
        """Fetch GUID for a ledger."""
        xml = f"""<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES><TDL><COLLECTION NAME="SL"><TYPE>Ledger</TYPE><FETCH>Name,GUID</FETCH><FILTER>IsMyLedger</FILTER></COLLECTION><SYSTEM TYPE="Formulae" NAME="IsMyLedger">$Name="{escape(ledger_name)}"</SYSTEM></TDL></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"""
        try:
            r = requests.post(self.tally_url, data=xml, timeout=5)
            # Basic clean
            txt = r.text.replace("&#4;", "")
            root = ET.fromstring(txt)
            for l in root.findall(".//LEDGER"):
                return l.findtext("GUID")
        except: return None



    def get_voucher_details(self, voucher_number: str) -> Optional[Dict[str, Any]]:
        """Fetch full voucher details by number for verification."""
        xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Voucher Register</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <SVFROMDATE>20200401</SVFROMDATE> 
                    <SVTODATE>20290331</SVTODATE>
                </STATICVARIABLES>
                <TDL>
                    <COLLECTION NAME="SpecificVoucher">
                        <TYPE>Voucher</TYPE>
                        <FETCH>Date,VoucherNumber,PartyLedgerName,Amount,LedgerEntries.List,AllLedgerEntries.List</FETCH>
                        <FILTER>TargetVoucher</FILTER>
                    </COLLECTION>
                    <SYSTEM TYPE="Formulae" NAME="TargetVoucher">$VoucherNumber="{voucher_number}"</SYSTEM>
                </TDL>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
        try:
            r = requests.post(self.tally_url, data=xml, timeout=5)
            # Re-use get_transactions parse logic if possible, or simple parse
            root = ET.fromstring(self._clean_xml(r.text))
            v_node = root.find(".//VOUCHER")
            if not v_node: return None
            
            # Simple Total Amount Check
            # Sum of all ledger entries?
            ledgers = []
            entries = v_node.findall("ALLLEDGERENTRIES.LIST") or v_node.findall("LEDGERENTRIES.LIST")
            for led in entries:
                l_name = led.findtext("LEDGERNAME")
                l_amt = float(led.findtext("AMOUNT") or 0)
                ledgers.append({"name": l_name, "amount": l_amt})
                
            return {
                "number": v_node.findtext("VOUCHERNUMBER"),
                "date": v_node.findtext("DATE"),
                "ledgers": ledgers
            }
        except Exception as e:
            logger.error(f"Verification Fetch Failed: {e}")
            return None

    def check_item_exists(self, item_name: str) -> Optional[str]:
        if not self.item_cache:
            self.fetch_all_items()
            
        key = item_name.strip().lower()
        return self.item_cache.get(key)
        
    def get_godowns(self) -> List[str]:
        """Fetches list of Godowns."""
        xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME>
    <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <ACCOUNTTYPE>Godowns</ACCOUNTTYPE> 
    </STATICVARIABLES>
    </REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>"""
        try:
            r = requests.post(self.tally_url, data=xml, timeout=10)
            root = ET.fromstring(self._clean_xml(r.text))
            godowns = []
            # Tally returns Godowns as GODOWN or names
            for g in root.findall(".//GODOWN"):
                name = g.get("NAME") or g.findtext("NAME")
                if name: godowns.append(name)
            return godowns
        except Exception as e:
            logger.error(f"Error fetching Godowns: {e}")
            return []

    def _fetch_and_parse(self, xml_payload: str, row_tag: str, fields: List[str]) -> List[Dict[str, Any]]:
        """
        Generic Helper to Fetch TDL-XML and Parse specific fields.
        Handles both element text and element attributes (like NAME).
        """
        try:
            r = requests.post(self.tally_url, data=xml_payload, headers={'Content-Type': 'text/xml'}, timeout=10)
            if r.status_code != 200:
                logger.error(f"Tally Error {r.status_code}")
                return []
            
            root = ET.fromstring(self._clean_xml(r.text))
            results = []
            
            for row in root.findall(f".//{row_tag}"):
                item = {}
                for f in fields:
                    # Try 1: Get from element text (e.g., <NAME>value</NAME>)
                    val = row.findtext(f.upper())
                    
                    # Try 2: Get from element attribute (e.g., <LEDGER NAME="value">)
                    if not val:
                        val = row.get(f.upper()) or row.get(f)
                    
                    item[f] = val if val else ""
                results.append(item)
                
            return results
            
        except Exception as e:
            logger.error(f"Reporting Error: {e}")
            return []

    def get_stock_summary(self) -> List[Dict[str, Any]]:
        """
        Fetches Stock Items with Closing Quantity and Value.
        Uses Tally's Stock Summary report for accurate closing values.
        
        Returns: [{'name': 'Item A', 'closing_balance': 10, 'value': 500.00, 'rate': 50.00}]
        """
        # Strategy 1: Use Stock Summary report (gives accurate closing qty and value)
        stock_summary_xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Stock Summary</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
        
        try:
            import requests
            r = requests.post(self.tally_url, data=stock_summary_xml, timeout=15)
            if r.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(self._clean_xml(r.text))
                
                items = []
                current_name = None
                
                # Stock Summary report uses DSP* elements
                # Structure: DSPACCNAME/DSPDISPNAME (name) followed by DSPSTKINFO/DSPSTKCL (close data)
                for elem in root.iter():
                    # Get item name from DSPDISPNAME
                    if elem.tag == "DSPDISPNAME" and elem.text:
                        current_name = elem.text.strip()
                    
                    # Get closing data from DSPSTKCL block
                    if elem.tag == "DSPSTKCL" and current_name:
                        cl_qty_str = elem.findtext("DSPCLQTY") or ""
                        cl_rate_str = elem.findtext("DSPCLRATE") or ""
                        cl_amt_str = elem.findtext("DSPCLAMTA") or ""
                        
                        # Parse closing quantity (e.g., "3815.00 kg")
                        cl_bal = 0.0
                        if cl_qty_str:
                            try:
                                cl_bal = abs(float(cl_qty_str.replace(",", "").split()[0]))
                            except (ValueError, IndexError):
                                pass
                        
                        # Parse closing rate
                        cl_rate = 0.0
                        if cl_rate_str:
                            try:
                                cl_rate = abs(float(cl_rate_str.replace(",", "")))
                            except (ValueError, TypeError):
                                pass
                        
                        # Parse closing amount (negative in Tally = debit/asset value)
                        cl_val = 0.0
                        if cl_amt_str:
                            try:
                                cl_val = abs(float(cl_amt_str.replace(",", "")))
                            except (ValueError, TypeError):
                                pass
                        
                        # Only add items with positive quantities
                        if cl_bal > 0:
                            items.append({
                                "name": current_name,
                                "parent": "",
                                "units": "",
                                "opening_balance": 0,
                                "closing_balance": cl_bal,
                                "value": cl_val,
                                "rate": cl_rate,
                                "standard_cost": "",
                                "standard_price": ""
                            })
                        
                        current_name = None  # Reset for next item
                
                if items:
                    total_val = sum(i.get('value', 0) for i in items)
                    logger.info(f"📦 Stock Summary: Found {len(items)} items with total value: ₹{total_val:.2f}")
                    return items
                    
        except Exception as e:
            logger.warning(f"Stock Summary report failed: {e}")
        
        # Strategy 2: Fallback to List of Accounts with Stock Items
        logger.info("📊 Trying List of Accounts for Stock Items...")
        try:
            list_xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>List of Accounts</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <ACCOUNTTYPE>Stock Items</ACCOUNTTYPE>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
            
            import requests
            r = requests.post(self.tally_url, data=list_xml, timeout=15)
            if r.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(self._clean_xml(r.text))
                
                items = []
                for stock in root.findall(".//STOCKITEM"):
                    name = stock.get("NAME") or stock.findtext("NAME") or ""
                    if not name:
                        continue
                        
                    # Get closing balance and value attributes
                    cl_bal_str = stock.findtext("CLOSINGBALANCE") or ""
                    cl_val_str = stock.findtext("CLOSINGVALUE") or ""
                    rate_str = stock.findtext("CLOSINGRATE") or stock.findtext("STANDARDPRICE") or ""
                    
                    # Parse quantities
                    cl_bal = 0.0
                    if cl_bal_str:
                        try:
                            cl_bal = abs(float(cl_bal_str.replace(",", "").split()[0]))
                        except (ValueError, IndexError):
                            pass
                    
                    cl_val = 0.0
                    if cl_val_str:
                        try:
                            cl_val = abs(float(cl_val_str.replace(",", "").split()[0]))
                        except (ValueError, IndexError):
                            pass
                    
                    rate = 0.0
                    if rate_str:
                        try:
                            rate = abs(float(rate_str.replace(",", "").split("/")[0]))
                        except (ValueError, IndexError):
                            pass
                    
                    # If we have quantity but no value, estimate from rate
                    if cl_bal > 0 and cl_val == 0 and rate > 0:
                        cl_val = cl_bal * rate
                    
                    items.append({
                        "name": name,
                        "parent": stock.findtext("PARENT") or "",
                        "units": stock.findtext("BASEUNITS") or "nos",
                        "opening_balance": 0,
                        "closing_balance": cl_bal,
                        "value": cl_val,
                        "rate": rate,
                        "standard_cost": stock.findtext("STANDARDCOST") or "",
                        "standard_price": stock.findtext("STANDARDPRICE") or ""
                    })
                
                if items:
                    logger.info(f"📦 List of Accounts: Found {len(items)} stock items")
                    return items
                    
        except Exception as e:
            logger.warning(f"List of Accounts failed: {e}")
        
        # Strategy 3: Calculate from voucher transactions (most reliable fallback)
        logger.info("📊 Calculating stock from Purchase/Sales transactions...")
        try:
            from datetime import datetime
            
            # Get transactions for current FY
            now = datetime.now()
            if now.month < 4:
                start_date = datetime(now.year - 1, 4, 1)
            else:
                start_date = datetime(now.year, 4, 1)
            
            txns = self.get_transactions(
                start_date.strftime("%Y%m%d"),
                now.strftime("%Y%m%d")
            )
            
            # Build stock map from transactions
            stock_map = {}  # item_name -> {"qty_in": 0, "qty_out": 0, "value_in": 0}
            
            for txn in txns:
                v_type = (txn.get("type") or "").lower()
                items_list = txn.get("items", [])
                
                for item in items_list:
                    item_name = item.get("name", "")
                    if not item_name:
                        continue
                    
                    qty = abs(float(item.get("quantity", 0) or 0))
                    rate = abs(float(item.get("rate", 0) or 0))
                    amt = abs(float(item.get("amount", 0) or 0))
                    
                    if item_name not in stock_map:
                        stock_map[item_name] = {"qty_in": 0, "qty_out": 0, "value_in": 0, "last_rate": 0}
                    
                    if "purchase" in v_type:
                        stock_map[item_name]["qty_in"] += qty
                        stock_map[item_name]["value_in"] += amt
                        stock_map[item_name]["last_rate"] = rate if rate > 0 else stock_map[item_name]["last_rate"]
                    elif "sales" in v_type:
                        stock_map[item_name]["qty_out"] += qty
            
            # Convert to standard format
            items = []
            for name, data in stock_map.items():
                closing_qty = data["qty_in"] - data["qty_out"]
                avg_rate = data["value_in"] / data["qty_in"] if data["qty_in"] > 0 else data["last_rate"]
                closing_val = closing_qty * avg_rate
                
                items.append({
                    "name": name,
                    "parent": "",
                    "units": "nos",
                    "opening_balance": 0,
                    "closing_balance": max(closing_qty, 0),
                    "value": max(closing_val, 0),
                    "rate": avg_rate,
                    "standard_cost": "",
                    "standard_price": ""
                })
            
            if items:
                total_val = sum(i.get("value", 0) for i in items)
                logger.info(f"📦 Calculated from Transactions: {len(items)} items, Total Value: ₹{total_val:.2f}")
                return items
                
        except Exception as e:
            logger.error(f"Transaction-based stock calculation failed: {e}")
        
        # Final fallback: Return items from cache with zero values
        logger.warning("⚠️ Could not calculate stock values, returning items from cache")
        if not self.item_cache:
            self.fetch_all_items()
        
        return [
            {
                "name": name,
                "parent": "",
                "units": "nos",
                "opening_balance": 0,
                "closing_balance": 0,
                "value": 0,
                "rate": 0,
                "standard_cost": "",
                "standard_price": ""
            }
            for name in self.item_cache.values()
        ]

    def get_receivables(self) -> List[Dict[str, Any]]:
        """
        Fetches Sundry Debtors with Outstanding Balance from Tally.
        Returns: [{'party_name': 'Party A', 'amount': 5000.00}]
        """
        # Strategy: Query each Sundry Debtor's Ledger Vouchers to get closing balance
        # First, get list of all Sundry Debtors
        ledger_list_xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>List of Accounts</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <ACCOUNTTYPE>Ledgers</ACCOUNTTYPE>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
        
        results = []
        
        try:
            import requests
            r = requests.post(self.tally_url, data=ledger_list_xml, timeout=15)
            if r.status_code != 200:
                return []
            
            import re
            
            # Parse ledger names and parents from response
            # <LEDGER NAME="ABC" ... PARENT="Sundry Debtors">
            ledgers = re.findall(
                r'<LEDGER[^>]*NAME="([^"]+)"[^>]*>.*?<PARENT>([^<]+)</PARENT>',
                r.text, re.DOTALL
            )
            
            # Also try alternative format
            if not ledgers:
                ledgers = re.findall(
                    r'<LEDGER[^>]*>.*?<NAME>([^<]+)</NAME>.*?<PARENT>([^<]+)</PARENT>',
                    r.text, re.DOTALL
                )
            
            sundry_debtors = [name for name, parent in ledgers if parent.lower() == 'sundry debtors']
            logger.info(f"Found {len(sundry_debtors)} Sundry Debtors")
            
            # Query each debtor for their balance using Ledger Vouchers report
            for debtor_name in sundry_debtors:
                ledger_xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Ledger Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <LEDGERNAME>{debtor_name}</LEDGERNAME>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
                
                try:
                    lr = requests.post(self.tally_url, data=ledger_xml, timeout=10)
                    if lr.status_code == 200:
                        # Find closing balance at end (last DSPVCHCLAMT / DSPCLAMT)
                        # Try multiple patterns for closing balance
                        closing_patterns = [
                            r'<DSPCLBAL>([^<]+)</DSPCLBAL>',  # Closing Balance row
                            r'<DSPVCHCLBAL>([^<]+)</DSPVCHCLBAL>',
                        ]
                        
                        # Get all transaction amounts and sum them
                        dr_amounts = re.findall(r'<DSPVCHDRAMT>([^<]+)</DSPVCHDRAMT>', lr.text)
                        cr_amounts = re.findall(r'<DSPVCHCRAMT>([^<]+)</DSPVCHCRAMT>', lr.text)
                        
                        total_dr = 0.0
                        total_cr = 0.0
                        
                        for amt in dr_amounts:
                            try:
                                total_dr += abs(float(amt.replace(',', '').strip()))
                            except:
                                pass
                        
                        for amt in cr_amounts:
                            try:
                                total_cr += abs(float(amt.replace(',', '').strip()))
                            except:
                                pass
                        
                        # For Sundry Debtors: Cr means they owe us (receivable)
                        balance = total_cr - total_dr  # Positive = receivable
                        
                        if balance != 0:
                            results.append({
                                "party_name": debtor_name,
                                "amount": abs(balance)  # Show absolute value
                            })
                            logger.debug(f"  {debtor_name}: Rs.{balance:,.2f}")
                except Exception as e:
                    logger.debug(f"Failed to query {debtor_name}: {e}")
            
        except Exception as e:
            logger.error(f"Error fetching receivables: {e}")
        
        results.sort(key=lambda x: x["amount"], reverse=True)
        return results

    def get_payables(self) -> List[Dict[str, Any]]:
        """
        Fetches Sundry Creditors with Outstanding Balance from Tally.
        Returns: [{'party': 'Party A', 'amount': 5000.00}]
        """
        # Strategy: Query each Sundry Creditor's Ledger Vouchers to get closing balance
        ledger_list_xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>List of Accounts</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <ACCOUNTTYPE>Ledgers</ACCOUNTTYPE>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
        
        results = []
        
        try:
            import requests
            import re
            
            r = requests.post(self.tally_url, data=ledger_list_xml, timeout=15)
            if r.status_code != 200:
                return []
            
            # Parse ledger names and parents from response
            ledgers = re.findall(
                r'<LEDGER[^>]*NAME="([^"]+)"[^>]*>.*?<PARENT>([^<]+)</PARENT>',
                r.text, re.DOTALL
            )
            
            if not ledgers:
                ledgers = re.findall(
                    r'<LEDGER[^>]*>.*?<NAME>([^<]+)</NAME>.*?<PARENT>([^<]+)</PARENT>',
                    r.text, re.DOTALL
                )
            
            sundry_creditors = [name for name, parent in ledgers if parent.lower() == 'sundry creditors']
            logger.info(f"Found {len(sundry_creditors)} Sundry Creditors")
            
            # Query each creditor for their balance
            for creditor_name in sundry_creditors:
                ledger_xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Ledger Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <LEDGERNAME>{creditor_name}</LEDGERNAME>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
                
                try:
                    lr = requests.post(self.tally_url, data=ledger_xml, timeout=10)
                    if lr.status_code == 200:
                        dr_amounts = re.findall(r'<DSPVCHDRAMT>([^<]+)</DSPVCHDRAMT>', lr.text)
                        cr_amounts = re.findall(r'<DSPVCHCRAMT>([^<]+)</DSPVCHCRAMT>', lr.text)
                        
                        total_dr = 0.0
                        total_cr = 0.0
                        
                        for amt in dr_amounts:
                            try:
                                total_dr += abs(float(amt.replace(',', '').strip()))
                            except:
                                pass
                        
                        for amt in cr_amounts:
                            try:
                                total_cr += abs(float(amt.replace(',', '').strip()))
                            except:
                                pass
                        
                        # For Sundry Creditors: Cr means we owe them (payable)
                        balance = total_cr - total_dr  # Positive = payable
                        
                        if balance != 0:
                            results.append({
                                "party": creditor_name,
                                "amount": abs(balance)
                            })
                            logger.debug(f"  {creditor_name}: Rs.{balance:,.2f}")
                except Exception as e:
                    logger.debug(f"Failed to query {creditor_name}: {e}")
            
        except Exception as e:
            logger.error(f"Error fetching payables: {e}")
        
        results.sort(key=lambda x: x["amount"], reverse=True)
        return results

    def get_cash_bank_balance(self) -> float:
        """
        Fetches closing balances for Cash-in-Hand and Bank Accounts.
        
        Strategy:
        1. Try to get ledger balances from Tally (preferred)
        2. If that fails, calculate from transactions (Receipt - Payment)
        """
        total_bal = 0.0
        
        # ===== STRATEGY 1: Query Tally for Cash/Bank Ledger Balances =====
        # Try fetching ALL ledgers and filtering for Cash/Bank related
        try:
            all_ledgers_xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>List of Accounts</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <ACCOUNTTYPE>Ledgers</ACCOUNTTYPE>
                </STATICVARIABLES>
                <TDL>
                    <OBJECT NAME="Ledger">
                        <FETCH>Name,Parent,ClosingBalance</FETCH>
                    </OBJECT>
                </TDL>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
            
            all_ledgers = self._fetch_and_parse(all_ledgers_xml, "LEDGER", ["Name", "Parent", "ClosingBalance"])
            
            # Filter for Cash/Bank related ledgers
            cash_bank_groups = ["cash-in-hand", "bank accounts", "bank account", "cash"]
            
            for r in all_ledgers:
                parent = (r.get("Parent") or "").lower()
                name = (r.get("Name") or "").lower()
                
                # Check if this ledger is under Cash-in-Hand or Bank Accounts
                is_cash_bank = any(cb in parent for cb in cash_bank_groups) or name == "cash"
                
                if is_cash_bank:
                    try:
                        bal_str = r.get("ClosingBalance", "0")
                        # Handle potential formatted strings like "5,00,000.00 Dr"
                        bal_clean = bal_str.replace(",", "").split()[0] if bal_str else "0"
                        bal = float(bal_clean)
                        total_bal += abs(bal)
                        logger.info(f"💰 Ledger: {r.get('Name')} ({r.get('Parent')}) = ₹{abs(bal):.2f}")
                    except (ValueError, TypeError, IndexError) as e:
                        logger.debug(f"Could not parse balance for {r.get('Name')}: {e}")
            
            if total_bal > 0:
                logger.info(f"✅ Cash & Bank from Ledgers: ₹{total_bal:.2f}")
                return total_bal
                
        except Exception as e:
            logger.warning(f"Strategy 1 (Ledger Query) failed: {e}")
        
        # ===== STRATEGY 2: Calculate from Transactions =====
        # Sum all Receipts (Cash In) and subtract Payments (Cash Out)
        logger.info("📊 Calculating Cash Balance from Transactions (Receipts - Payments)...")
        
        try:
            from datetime import datetime, timedelta
            
            # Get transactions for a reasonable period (last 2 years)
            end_date = datetime.now()
            # Start from April 1 of current or previous FY
            if end_date.month < 4:
                start_date = datetime(end_date.year - 1, 4, 1)
            else:
                start_date = datetime(end_date.year, 4, 1)
            
            txns = self.get_transactions(
                start_date.strftime("%Y%m%d"), 
                end_date.strftime("%Y%m%d")
            )
            
            total_receipts = 0.0
            total_payments = 0.0
            
            for txn in txns:
                v_type = (txn.get("type") or "").lower()
                ledgers = txn.get("ledgers", [])
                
                # Check if this transaction involves Cash or Bank
                involves_cash_bank = False
                for led in ledgers:
                    led_name = (led.get("name") or "").lower()
                    if "cash" in led_name or "bank" in led_name:
                        involves_cash_bank = True
                        break
                
                if not involves_cash_bank:
                    continue
                
                try:
                    amt = float(txn.get("amount", 0))
                except (ValueError, TypeError):
                    amt = 0.0
                
                # Receipt = Cash coming in
                if "receipt" in v_type:
                    total_receipts += amt
                    logger.debug(f"  + Receipt: ₹{amt:.2f}")
                # Payment = Cash going out  
                elif "payment" in v_type:
                    total_payments += amt
                    logger.debug(f"  - Payment: ₹{amt:.2f}")
                # Sales with Cash payment = Cash coming in (Cash is debited = negative in Tally XML)
                elif "sales" in v_type:
                    for led in ledgers:
                        if "cash" in (led.get("name") or "").lower():
                            led_amt = led.get("amount", 0)
                            if led_amt < 0:  # Debit in Tally XML = negative
                                total_receipts += abs(led_amt)
                                logger.debug(f"  + Sales (Cash): ₹{abs(led_amt):.2f}")
                            break
                # Purchase with Cash payment = Cash going out (Cash is credited = positive in Tally XML)
                elif "purchase" in v_type:
                    for led in ledgers:
                        if "cash" in (led.get("name") or "").lower():
                            led_amt = led.get("amount", 0)
                            if led_amt > 0:  # Credit in Tally XML = positive
                                total_payments += abs(led_amt)
                                logger.debug(f"  - Purchase (Cash): ₹{abs(led_amt):.2f}")
                            break
            
            # Net Cash Balance = Receipts - Payments
            total_bal = total_receipts - total_payments
            
            logger.info(f"📈 Receipts: ₹{total_receipts:.2f} | Payments: ₹{total_payments:.2f}")
            logger.info(f"✅ Net Cash & Bank Balance: ₹{total_bal:.2f}")
            
            return max(total_bal, 0)  # Return 0 if negative (unlikely in normal operations)
            
        except Exception as e:
            logger.error(f"Strategy 2 (Transaction Calculation) failed: {e}")
        
        logger.warning("⚠️ Could not calculate Cash & Bank Balance")
        return 0.0

    def get_daybook_stats(self, from_date: str, to_date: str) -> Dict[str, Any]:
        """
        Get Sales totals and count from Daybook.
        from_date, to_date: YYYYMMDD
        """
        txns = self.get_transactions(from_date, to_date)
        total_sales = 0.0
        count = 0
        
        for txn in txns:
            v_type = txn.get("type", "").lower()
            if "sales" in v_type or "sale" in v_type:
                try:
                    amt = float(txn.get("amount", 0))
                    total_sales += amt
                    count += 1
                except: pass
                
        return {
            "total_sales": total_sales,
            "txn_count": count
        }

    def get_transactions(self, start_date: str, end_date: str, party_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch Vouchers from Tally using 'Voucher Register' report.
        Upgraded to fetch COMPLETE data structure (Line Items, Tax, Ledgers).
        Args:
            start_date: YYYYMMDD
            end_date: YYYYMMDD
        """
        # Fetch FULL Voucher XML (No strict fetch limit) to get Inventory & Ledgers
        xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Voucher Register</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <SVFROMDATE>{{start_date}}</SVFROMDATE>
                    <SVTODATE>{{end_date}}</SVTODATE>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
        
        xml = xml.replace("{{start_date}}", start_date).replace("{{end_date}}", end_date)
        
        try:
            r = requests.post(self.tally_url, data=xml, headers={'Content-Type': 'text/xml'}, timeout=30)
            if r.status_code != 200:
                logger.error(f"Tally Error {r.status_code}")
                return []
            
            root = ET.fromstring(self._clean_xml(r.text))
            results = []
            
            for v_node in root.findall(".//VOUCHER"):
                # Basic Fields
                v_date = v_node.findtext("DATE")
                v_num = v_node.findtext("VOUCHERNUMBER")
                v_type = v_node.findtext("VOUCHERTYPENAME")
                v_party = v_node.findtext("PARTYLEDGERNAME")
                v_narration = v_node.findtext("NARRATION")
                v_guid = v_node.findtext("GUID")
                
                # Dynamic Party Name from Ledger Entries if PARTYLEDGERNAME is generic/missing
                # (Common in Receipts/Payments where Party is first ledger)
                
                # --- Line Items (Inventory) ---
                items = []
                # Check for standard Inventory Entries or In/Out variations
                inv_entries = (v_node.findall("INVENTORYENTRIES.LIST") or []) + \
                              (v_node.findall("INVENTORYENTRIESIN.LIST") or []) + \
                              (v_node.findall("INVENTORYENTRIESOUT.LIST") or [])
                              
                for inv in inv_entries:
                    item_name = inv.findtext("STOCKITEMNAME")
                    qty_str = inv.findtext("ACTUALQTY") or inv.findtext("BILLEDQTY") # e.g. " 10.00 kgs"
                    rate_str = inv.findtext("RATE") # e.g. "120.00/kgs"
                    amt_str = inv.findtext("AMOUNT") 
                    
                    if item_name:
                         # Cleanup Qty/Rate string
                         # Qty: Remove units
                         qty_val = 0.0
                         if qty_str:
                             try:
                                 # Split " 10.00 kgs" -> "10.00"
                                 qty_val = float(qty_str.split()[0])
                             except: pass
                             
                         # Rate: Remove units
                         rate_val = 0.0
                         if rate_str:
                             try:
                                 rate_val = float(rate_str.split('/')[0])
                             except: pass
                             
                         amt_val = 0.0
                         if amt_str:
                             try:
                                 amt_val = float(amt_str)
                             except: pass

                         items.append({
                             "name": item_name,
                             "quantity": qty_val,
                             "rate": rate_val,
                             "amount": abs(amt_val)
                         })

                # --- Ledger Entries (Tax & Accounts) ---
                ledgers = []
                total_dr = 0.0
                total_cr = 0.0
                
                # Traverse All Ledger Entries
                # Could use ALLLEDGERENTRIES.LIST or LEDGERENTRIES.LIST
                ledger_entries = v_node.findall("ALLLEDGERENTRIES.LIST") or v_node.findall("LEDGERENTRIES.LIST")
                
                for led in ledger_entries:
                    l_name = led.findtext("LEDGERNAME")
                    l_amt_str = led.findtext("AMOUNT")
                    l_amt = 0.0
                    if l_amt_str:
                        try:
                            l_amt = float(l_amt_str)
                        except: pass
                    
                    # Accumulate absolute amounts — we use max(dr, cr) to get the voucher total.
                    # In a balanced voucher both sides are equal, so this always gives the correct amount.
                    # The debit/credit column display is handled in the frontend based on voucher_type.
                    if l_amt < 0:
                        total_dr += abs(l_amt)
                    else:
                        total_cr += l_amt

                    # Identify if Tax Ledger
                    is_tax = any(x in (l_name or "").upper() for x in ["GST", "TAX", "CESS", "DUTY"])
                    
                    ledgers.append({
                        "name": l_name,
                        "amount": l_amt,
                        "is_tax": is_tax
                    })

                # Deduce Total Amount
                # Use the higher of Dr vs Cr sums (Balanced vouchers should be equal)
                # This covers Inventory vouchers (items sum included in Ledgers) and Accounting vouchers
                total_amount = max(total_dr, total_cr)
                
                # Fallback if 0 (sometimes Tally doesn't export amounts in ledgers but in header?)
                if total_amount == 0 and items:
                     total_amount = sum(i["amount"] for i in items)
                
                # Party Filter
                if party_filter:
                    # Check Party Name OR First Ledger
                    match = False
                    if v_party and party_filter.lower() in v_party.lower(): match = True
                    elif ledgers and party_filter.lower() in ledgers[0]["name"].lower(): match = True
                    
                    if not match: continue

                results.append({
                    "date": v_date,           # YYYYMMDD
                    "number": v_num,
                    "type": v_type,
                    "party": v_party or (ledgers[0]["name"] if ledgers else "Unknown"),
                    "amount": f"{abs(total_amount):.2f}",
                    "narration": v_narration,
                    "guid": v_guid,
                    "items": items,
                    "ledgers": ledgers,
                    "tax_breakdown": [l for l in ledgers if l["is_tax"]]
                })
            
            return results

        except Exception as e:
            logger.error(f"Error fetching extended transactions: {e}")
            return []

    def get_tax_summary(self, start_date: str, end_date: str) -> Dict[str, float]:
        """
        Calculate GST Tax summary (Input vs Output) for a given period.
        """
        txns = self.get_transactions(start_date, end_date)
        
        summary = {
            "cgst_collected": 0.0, "cgst_paid": 0.0,
            "sgst_collected": 0.0, "sgst_paid": 0.0,
            "igst_collected": 0.0, "igst_paid": 0.0,
            "total_liability": 0.0
        }
        
        for txn in txns:
            v_type = txn.get("type", "").lower()
            
            # Sales -> Output Tax (Collected)
            # Purchase -> Input Tax (Paid)
            is_sales = "sales" in v_type
            is_purchase = "purchase" in v_type
            
            tax_ledgers = txn.get("tax_breakdown", [])
            for tax in tax_ledgers:
                name = tax["name"].lower()
                amount = tax["amount"] # Signed
                
                # Determine tax type
                t_type = "other"
                if "cgst" in name: t_type = "cgst"
                elif "sgst" in name: t_type = "sgst"
                elif "igst" in name: t_type = "igst"
                
                if t_type == "other": continue
                
                if is_sales:
                     summary[f"{t_type}_collected"] += abs(amount)
                elif is_purchase:
                     summary[f"{t_type}_paid"] += abs(amount)
                     
        summary["total_liability"] = (summary["cgst_collected"] + summary["sgst_collected"] + summary["igst_collected"]) - \
                                     (summary["cgst_paid"] + summary["sgst_paid"] + summary["igst_paid"])
                                     
        return summary

    def get_party_metrics(self, start_date: str, end_date: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get Top Customers (Sales) and Top Suppliers (Purchase)
        """
        txns = self.get_transactions(start_date, end_date)
        
        sales_map = {}
        purchase_map = {}
        
        for txn in txns:
            v_type = txn.get("type", "").lower()
            party = txn.get("party", "Unknown")
            try:
                amt = float(txn.get("amount", 0))
            except: amt = 0.0
            
            if "sales" in v_type:
                sales_map[party] = sales_map.get(party, 0.0) + amt
            elif "purchase" in v_type:
                purchase_map[party] = purchase_map.get(party, 0.0) + amt
                
        # Sort and Format
        top_sales = [{"name": k, "value": v} for k, v in sales_map.items()]
        top_sales.sort(key=lambda x: x["value"], reverse=True)
        
        top_purchase = [{"name": k, "value": v} for k, v in purchase_map.items()]
        top_purchase.sort(key=lambda x: x["value"], reverse=True)
        
        return {
            "top_customers": top_sales[:5],
            "top_suppliers": top_purchase[:5]
        }
