import requests
import xml.etree.ElementTree as ET
import pandas as pd
from typing import Optional, Dict, Any, List
from xml.sax.saxutils import escape
import logging
import os
import time
from datetime import datetime
from backend.tally_response_parser import parse_tally_response

# Retry logic for resilient connections
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    # Fallback decorator that does nothing
    def retry(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def stop_after_attempt(n): return None
    def wait_exponential(**kwargs): return None
    def retry_if_exception_type(exc): return None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tally_connector")

TALLY_API_URL = os.getenv("TALLY_URL", "http://localhost:9000")
DEFAULT_COMPANY = os.getenv("TALLY_COMPANY", "")  # Empty = auto-detect from Tally

# Try loading from config file
try:
    import json
    if os.path.exists("k24_config.json"):
        with open("k24_config.json", "r") as f:
            config = json.load(f)
            TALLY_API_URL = config.get("tally_url", TALLY_API_URL)
            DEFAULT_COMPANY = config.get("company_name", DEFAULT_COMPANY)
except Exception as e:
    logger.warning(f"Failed to load config file: {e}")

def _strip_namespace(tag):
    return tag.split('}', 1)[-1] if '}' in tag else tag

def flatten_element(element):
    data = {}
    # Capture attributes first (crucial for Tally NAME attribute)
    if element.attrib:
        for k, v in element.attrib.items():
            data[k.upper()] = (v or '').strip()

    for child in element:
        tag = _strip_namespace(child.tag).upper().replace(' ', '_')
        if list(child):  # has children, flatten recursively
            data.update({f"{tag}_{k}": v for k, v in flatten_element(child).items()})
        else:
            data[tag] = (child.text or '').strip()
    return data

def normalize_columns(df):
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df

def push_to_tally(xml_data):
    """
    Legacy wrapper for backward compatibility.
    Uses TallyConnector to push XML and returns raw response text on success, None on failure.
    """
    connector = TallyConnector()
    result = connector.push_xml(xml_data)
    if result["success"]:
        # Return a success indicator or the raw response if available?
        # Original returned response.text.
        # We can reconstruct a simple success XML or just return "OK"
        return "<RESPONSE>Success</RESPONSE>"
    else:
        logger.error(f"Push failed: {result['errors']}")
        return None

class TallyConnector:
    """
    Connector for TallyPrime XML-HTTP interface.
    Supports reading ledgers/vouchers and pushing updates directly to Tally.
    """
    def __init__(self, url: str = TALLY_API_URL, timeout: int = 300, company_name: Optional[str] = None):
        self.url = url
        self.timeout = timeout
        self.company_name = company_name or DEFAULT_COMPANY or self._fetch_active_company(url, timeout)
        self.session = self._create_session()

    def _fetch_active_company(self, url: str, timeout: int) -> str:
        """Auto-detect the currently open company from Tally. Called once at init."""
        xml = (
            "<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>"
            "<BODY><EXPORTDATA><REQUESTDESC>"
            "<REPORTNAME>List of Companies</REPORTNAME>"
            "<STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES>"
            "</REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"
        )
        try:
            resp = requests.post(url, data=xml,
                                 headers={'Content-Type': 'text/xml'}, timeout=5)
            import re as _re
            import xml.etree.ElementTree as _ET
            cleaned = _re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', resp.text)
            root = _ET.fromstring(cleaned)
            for node in root.findall('.//COMPANY'):
                name = node.findtext('NAME') or node.get('NAME', '')
                if name and name.strip():
                    logger.info(f"[TallyConnector] Auto-detected company: '{name.strip()}'")
                    return name.strip()
            for node in root.findall('.//NAME'):
                if node.text and node.text.strip():
                    logger.info(f"[TallyConnector] Auto-detected company (fallback): '{node.text.strip()}'")
                    return node.text.strip()
        except Exception as e:
            logger.warning(f"[TallyConnector] Could not auto-detect company name: {e}")
        return ""

    def _create_session(self):
        """Create session with custom timeout and retry strategy"""
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = requests.Session()
        
        # Retry strategy for transient failures
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # Wait 1, 2, 4 seconds between retries
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=1,  # Single connection to avoid Tally overload
            pool_maxsize=1
        )
        
        session.mount("http://", adapter)
        return session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True
    ) if TENACITY_AVAILABLE else lambda f: f
    def send_request_with_retry(self, xml: str) -> str:
        """
        Sends raw XML to Tally with automatic retry on failure.
        Uses exponential backoff for resilient connections.
        """
        return self.send_request(xml)

    def send_request(self, xml: str) -> str:
        """
        Sends raw XML to Tally and returns raw text response.
        Raises RuntimeError on HTTP connection issues.
        """
        headers = {
            "Content-Type": "application/xml; charset=utf-8",
            "Content-Length": str(len(xml.encode('utf-8')))
        }
        try:
            # Ensure XML is encoded properly
            resp = self.session.post(
                self.url, 
                data=xml.encode("utf-8"), 
                headers=headers, 
                timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            logger.error(f"Tally HTTP Request failed: {e}")
            raise RuntimeError(f"TallyConnector HTTP error: {e}")

    def push_xml(self, xml: str) -> Dict[str, Any]:
        """
        Sends XML to Tally and returns a robustly parsed response dictionary.
        Use this for all WRITE operations (Create/Alter/Delete).
        """
        try:
            raw_response = self.send_request(xml)
            return parse_tally_response(raw_response)
        except RuntimeError as e:
            return {
                "success": False,
                "status": "Connection Error",
                "errors": [str(e)],
                "created": 0, "altered": 0, "deleted": 0, "data": None
            }
        except Exception as e:
            return {
                "success": False,
                "status": "Unexpected Error",
                "errors": [str(e)],
                "created": 0, "altered": 0, "deleted": 0, "data": None
            }

    def fetch_ledgers(self, company_name: Optional[str] = None, from_date: Optional[str] = None, to_date: Optional[str] = None) -> pd.DataFrame:
        cname = company_name or self.company_name
        
        date_range_xml = ""
        if from_date and to_date:
            date_range_xml = f"""
            <SVFROMDATE>{escape(from_date)}</SVFROMDATE>
            <SVTODATE>{escape(to_date)}</SVTODATE>
            """

        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
            <BODY>
                <EXPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>List of Accounts</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                            <ACCOUNTTYPE>Ledgers</ACCOUNTTYPE>
                            {date_range_xml}
                        </STATICVARIABLES>
                        <TDL>
                            <SYSTEM TYPE="Formulae" NAME="MyClosingBal">$$ClosingBalance</SYSTEM>
                            <SYSTEM TYPE="Formulae" NAME="MyOpeningBal">$$OpeningBalance</SYSTEM>
                            <OBJECT NAME="Ledger">
                                <FETCH>Name,MyClosingBal,MyOpeningBal,Parent</FETCH>
                            </OBJECT>
                        </TDL>
                    </REQUESTDESC>
                </EXPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        try:
            xml_response = self.send_request(xml)
            return self._parse_ledger_xml(xml_response)
        except Exception as e:
            logger.error(f"Failed to fetch ledgers: {e}")
            return pd.DataFrame()

    def lookup_ledger(self, query: str) -> list[str]:
        """
        Finds ledgers matching the query.
        Returns a list of names.
        """
        df = self.fetch_ledgers()
        if df.empty:
            return []
        
        # Normalize
        df = normalize_columns(df)
        name_col = next((c for c in df.columns if 'name' in c), None)
        if not name_col:
            return []
            
        all_names = df[name_col].astype(str).tolist()
        
        # 1. Exact Match (Case Insensitive)
        exact = [n for n in all_names if n.lower() == query.lower()]
        if exact:
            return exact
            
        # 2. Starts With
        starts = [n for n in all_names if n.lower().startswith(query.lower())]
        if starts:
            return starts
            
        # 3. Contains
        contains = [n for n in all_names if query.lower() in n.lower()]
        return contains

    def fetch_ledgers_full(self, company_name: Optional[str] = None) -> pd.DataFrame:
        cname = company_name or self.company_name
        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
            <BODY>
                <EXPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>Ledger</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                </EXPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        xml_response = self.send_request(xml)
        return self._parse_ledger_xml(xml_response)

    def fetch_stock_items(self, company_name=None, from_date=None, to_date=None):
        """
        Fetch stock items from Tally Stock Summary report.
        Parses DSPDISPNAME/DSPCL* tags (actual Tally XML response format).
        No SVCURRENTCOMPANY - Tally uses active company automatically.
        """
        import re as _re
        xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY><EXPORTDATA><REQUESTDESC>
        <REPORTNAME>Stock Summary</REPORTNAME>
        <STATICVARIABLES>
            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
    </REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"""

        xml_response = self.send_request(xml)
        if not xml_response:
            logger.warning("Stock Summary: empty response from Tally")
            return pd.DataFrame()

        try:
            clean = self._sanitize_xml(xml_response)
            root = ET.fromstring(clean)

            records = []
            names = root.findall(".//DSPDISPNAME")
            infos = root.findall(".//DSPSTKINFO")

            for name_el, info_el in zip(names, infos):
                name = (name_el.text or "").strip()
                if not name:
                    continue

                qty_el  = info_el.find(".//DSPCLQTY")
                rate_el = info_el.find(".//DSPCLRATE")
                amt_el  = info_el.find(".//DSPCLAMTA")

                qty_str  = (qty_el.text  or "0").strip() if qty_el  is not None else "0"
                rate_str = (rate_el.text or "0").strip() if rate_el is not None else "0"
                amt_str  = (amt_el.text  or "0").strip() if amt_el  is not None else "0"

                qty_match    = _re.match(r"([\d.,]+)\s*(\w+)?", qty_str)
                closing_qty  = float(qty_match.group(1).replace(",", "")) if qty_match else 0.0
                unit         = (qty_match.group(2) or "Nos").upper() if qty_match else "Nos"
                closing_rate = float(rate_str.replace(",", "")) if rate_str else 0.0
                closing_val  = abs(float(amt_str.replace(",", "")) if amt_str else 0.0)

                records.append({
                    "name":          name,
                    "unit":          unit,
                    "closing_qty":   closing_qty,
                    "rate":          closing_rate,
                    "closing_value": closing_val,
                    "guid":          f"TALLY-STOCK-{name}"
                })

            logger.info(f"Stock Summary: parsed {len(records)} items")
            return pd.DataFrame(records) if records else pd.DataFrame()

        except Exception as e:
            logger.error(f"fetch_stock_items parse error: {e}. Raw: {xml_response[:200]}")
            return pd.DataFrame()

    def fetch_outstanding_bills(self, company_name: Optional[str] = None) -> pd.DataFrame:
        cname = company_name or self.company_name
        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
            <BODY>
                <EXPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>Bills Outstanding</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                </EXPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        xml_response = self.send_request(xml)
        return self._parse_generic_xml(xml_response, "BILL")

    # ========== NEW METHODS FOR 360° PROFILE SYNC ==========
    
    def fetch_bills_receivable_payable(self, bill_type: str = "Both", company_name: Optional[str] = None) -> List[Dict]:
        """
        Fetch outstanding bills with due dates for receivables/payables tracking.
        
        Args:
            bill_type: "Receivable", "Payable", or "Both"
            company_name: Optional company name override
            
        Returns:
            List of dicts with: party_name, bill_ref, bill_date, due_date, amount, pending_amount, is_overdue
        """
        cname = company_name or self.company_name
        
        # Use Tally's Bill Receivable/Payable report
        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
            <BODY>
                <EXPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>Bills Outstanding</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                </EXPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        
        try:
            xml_response = self.send_request(xml)
            xml_response = self._sanitize_xml(xml_response)
            root = ET.fromstring(xml_response)
            
            bills = []
            today = datetime.now().date()
            
            # Parse all BILLALLOCATIONS
            for bill in root.iter("BILLALLOCATIONS.LIST"):
                bill_name = bill.findtext("NAME") or bill.findtext("BILLNAME") or ""
                bill_date_str = bill.findtext("BILLDATE") or ""
                bill_due_date_str = bill.findtext("BILLDUEDATE") or bill.findtext("DUEDATE") or ""
                amount_str = bill.findtext("AMOUNT") or "0"
                
                # Parse amount
                try:
                    amount = float(amount_str.replace(",", ""))
                except:
                    amount = 0.0
                    
                # Parse dates
                bill_date = None
                due_date = None
                
                if bill_date_str:
                    try:
                        bill_date = datetime.strptime(bill_date_str[:8], "%Y%m%d").date()
                    except:
                        pass
                        
                if bill_due_date_str:
                    try:
                        due_date = datetime.strptime(bill_due_date_str[:8], "%Y%m%d").date()
                    except:
                        pass
                
                # Determine if receivable (positive) or payable (negative in Tally)
                is_receivable = amount > 0
                
                # Filter by type
                if bill_type == "Receivable" and not is_receivable:
                    continue
                if bill_type == "Payable" and is_receivable:
                    continue
                
                # Calculate overdue status
                is_overdue = False
                if due_date and due_date < today:
                    is_overdue = True
                
                bills.append({
                    "bill_ref": bill_name,
                    "bill_date": bill_date.isoformat() if bill_date else None,
                    "due_date": due_date.isoformat() if due_date else None,
                    "amount": abs(amount),
                    "pending_amount": abs(amount),  # Same as amount for outstanding
                    "is_receivable": is_receivable,
                    "is_overdue": is_overdue,
                    "days_overdue": (today - due_date).days if is_overdue and due_date else 0
                })
            
            # Try alternate parsing if no results
            if not bills:
                for dsp in root.iter("DSPBILLDETAILS"):
                    party_name = dsp.findtext("DSPACCNAME") or ""
                    bill_date_str = dsp.findtext("DSPBILLDATE") or ""
                    due_date_str = dsp.findtext("DSPDUEDATE") or ""
                    amount_str = dsp.findtext("DSPBILLAMOUNT") or "0"
                    pending_str = dsp.findtext("DSPPENDINGAMT") or dsp.findtext("DSPBILLAMOUNT") or "0"
                    
                    try:
                        amount = abs(float(amount_str.replace(",", "")))
                        pending = abs(float(pending_str.replace(",", "")))
                    except:
                        amount = 0.0
                        pending = 0.0
                    
                    bill_date = None
                    due_date = None
                    
                    if bill_date_str:
                        try:
                            bill_date = datetime.strptime(bill_date_str[:8], "%Y%m%d").date()
                        except:
                            pass
                            
                    if due_date_str:
                        try:
                            due_date = datetime.strptime(due_date_str[:8], "%Y%m%d").date()
                        except:
                            pass
                    
                    is_overdue = False
                    if due_date and due_date < today:
                        is_overdue = True
                    
                    bills.append({
                        "party_name": party_name,
                        "bill_date": bill_date.isoformat() if bill_date else None,
                        "due_date": due_date.isoformat() if due_date else None,
                        "amount": amount,
                        "pending_amount": pending,
                        "is_overdue": is_overdue,
                        "days_overdue": (today - due_date).days if is_overdue and due_date else 0
                    })
            
            logger.info(f"📋 Fetched {len(bills)} outstanding bills")
            return bills
            
        except Exception as e:
            logger.error(f"Failed to fetch bills: {e}")
            return []

    def fetch_ledger_complete(self, ledger_name: str, company_name: Optional[str] = None) -> Dict:
        """
        Fetch complete ledger details including contact info, opening balance, GSTIN, etc.
        
        Returns:
            Dict with all ledger fields for 360° customer profile
        """
        cname = company_name or self.company_name
        
        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
            <BODY>
                <EXPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>Ledger</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                            <LEDGERNAME>{escape(ledger_name)}</LEDGERNAME>
                            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                </EXPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        
        try:
            xml_response = self.send_request(xml)
            xml_response = self._sanitize_xml(xml_response)
            root = ET.fromstring(xml_response)
            
            ledger = root.find(".//LEDGER")
            if not ledger:
                logger.warning(f"Ledger '{ledger_name}' not found in Tally")
                return {}
            
            # Extract all available fields
            result = {
                "name": ledger.findtext("NAME") or ledger_name,
                "parent": ledger.findtext("PARENT") or "",
                "gstin": ledger.findtext("PARTYGSTIN") or ledger.findtext("GSTREGISTRATIONNUMBER") or "",
                "pan": ledger.findtext("INCOMETAXNUMBER") or "",
                "opening_balance": 0.0,
                "closing_balance": 0.0,
                "address": "",
                "city": "",
                "state": "",
                "pincode": "",
                "country": "India",
                "phone": "",
                "email": "",
                "contact_person": "",
                "credit_limit": 0.0,
                "credit_days": 0,
                "gst_registration_type": ""
            }
            
            # Parse opening balance
            try:
                ob_str = ledger.findtext("OPENINGBALANCE") or "0"
                result["opening_balance"] = float(ob_str.replace(",", ""))
            except:
                pass
            
            # Parse closing balance
            try:
                cb_str = ledger.findtext("CLOSINGBALANCE") or "0"
                result["closing_balance"] = float(cb_str.replace(",", ""))
            except:
                pass
            
            # Parse address (usually in ADDRESS.LIST)
            address_parts = []
            for addr in ledger.findall(".//ADDRESS.LIST/ADDRESS"):
                if addr.text:
                    address_parts.append(addr.text.strip())
            result["address"] = ", ".join(address_parts)
            
            # Also try MAILINGNAME/ADDRESS
            if not result["address"]:
                result["address"] = ledger.findtext("MAILINGNAME") or ""
            
            # State
            result["state"] = ledger.findtext("LEDSTATENAME") or ledger.findtext("STATENAME") or ""
            
            # Pincode
            result["pincode"] = ledger.findtext("PINCODE") or ""
            
            # Phone - check multiple possible fields
            result["phone"] = ledger.findtext("LEDGERPHONE") or ledger.findtext("PHONENUMBER") or ""
            
            # Email
            result["email"] = ledger.findtext("EMAIL") or ledger.findtext("LEDGEREMAIL") or ""
            
            # Contact person
            result["contact_person"] = ledger.findtext("LEDGERCONTACT") or ledger.findtext("CONTACTPERSON") or ""
            
            # Credit management
            try:
                result["credit_limit"] = float(ledger.findtext("CREDITLIMIT") or "0")
            except:
                pass
            
            try:
                result["credit_days"] = int(ledger.findtext("CREDITPERIOD") or ledger.findtext("CREDITDAYS") or "0")
            except:
                pass
            
            # GST details
            result["gst_registration_type"] = ledger.findtext("GSTREGISTRATIONTYPE") or ""
            
            logger.info(f"📋 Fetched complete ledger: {result['name']} (GSTIN: {result['gstin']})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch ledger details: {e}")
            return {}

    def fetch_voucher_with_line_items(
        self,
        voucher_number: str,
        voucher_type: str = None,
        guid: str = None,
        voucher_date: str = None,      # YYYYMMDD – narrows Day Book to 1 day for speed + precision
        company_name: Optional[str] = None,
    ) -> Dict:
        """
        Fetch a single voucher with ALL line items (inventory + ledger entries).

        Strategy:
        1. Ask Tally's Day Book for a 1-day window (the voucher's date).
           Day Book returns complete VOUCHER XML with all entries natively.
        2. Iterate ALL returned <VOUCHER> nodes and pick the one matching:
           – GUID (exact, highest priority)
           – VoucherNumber + VoucherType (fallback)
        3. If the day-window returns nothing, widen to ±30 days around that date.

        NOTE: No custom TDL FORM/PART/LINE is used – those caused Tally to
              throw "Part:DB Body No PARTS or LINES or BUTTONS" and return 0 results.
        """
        cname = company_name or self.company_name

        # ── Build date window ────────────────────────────────────────────────
        # Prefer the exact voucher date for a 1-day window.
        # Tally date format: YYYYMMDD
        from datetime import datetime as _dt, timedelta as _td

        if voucher_date and len(voucher_date) == 8:
            try:
                _parsed = _dt.strptime(voucher_date, "%Y%m%d")
                from_date = voucher_date
                to_date = voucher_date
            except ValueError:
                _parsed = None
                from_date = None
                to_date = None
        else:
            from_date = None
            to_date = None

        # If no specific date, use a rolling 2-year window so we don't miss anything
        if not from_date:
            _now = _dt.now()
            from_date = (_now - _td(days=730)).strftime("%Y%m%d")
            to_date = _now.strftime("%Y%m%d")

        def _build_daybook_xml(fd: str, td: str) -> str:
            return f"""<ENVELOPE>
  <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Day Book</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
          <SVFROMDATE>{fd}</SVFROMDATE>
          <SVTODATE>{td}</SVTODATE>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

        def _find_voucher_in_xml(xml_text: str) -> Optional[ET.Element]:
            """Parse xml_text and return the matching VOUCHER element or None."""
            try:
                sanitized = self._sanitize_xml(xml_text)
                root = ET.fromstring(sanitized)
            except Exception as parse_err:
                logger.warning(f"XML parse error in Day Book response: {parse_err}")
                return None

            all_nodes = root.findall(".//VOUCHER")
            logger.info(
                f"🔍 Day Book [{from_date}→{to_date}] for "
                f"#{voucher_number} ({voucher_type}): {len(all_nodes)} voucher(s)"
            )

            # Priority 1: GUID match
            if guid:
                for v in all_nodes:
                    if (v.findtext("GUID") or "").strip() == guid.strip():
                        return v

            # Priority 2: VoucherNumber + VoucherType
            req_type = (voucher_type or "").strip().lower()
            for v in all_nodes:
                v_num  = (v.findtext("VOUCHERNUMBER") or "").strip()
                v_type = (
                    v.findtext("VOUCHERTYPENAME")
                    or v.get("VCHTYPE", "")
                ).strip().lower()

                num_ok  = (v_num == voucher_number.strip())
                type_ok = (not req_type) or (req_type in v_type) or (v_type in req_type)

                if num_ok and type_ok:
                    return v

            # Last resort: only result
            if len(all_nodes) == 1:
                return all_nodes[0]

            return None

        try:
            # ── Attempt 1: narrow window ─────────────────────────────────────
            xml_response = self.send_request(_build_daybook_xml(from_date, to_date))
            voucher_node = _find_voucher_in_xml(xml_response)

            # ── Attempt 2: widen to ±30 days if narrow gave nothing ──────────
            if voucher_node is None and voucher_date:
                try:
                    _parsed = _dt.strptime(voucher_date, "%Y%m%d")
                    wide_from = (_parsed - _td(days=30)).strftime("%Y%m%d")
                    wide_to   = (_parsed + _td(days=30)).strftime("%Y%m%d")
                    logger.info(f"Widening Day Book window to {wide_from}→{wide_to}")
                    xml_response = self.send_request(_build_daybook_xml(wide_from, wide_to))
                    voucher_node = _find_voucher_in_xml(xml_response)
                except Exception:
                    pass

            if voucher_node is None:
                logger.warning(
                    f"Voucher #{voucher_number} (type={voucher_type}) not found "
                    f"in Day Book [{from_date}→{to_date}]"
                )
                return {}

            # ── Parse the matched voucher ────────────────────────────────────
            result = {
                "voucher_number": voucher_node.findtext("VOUCHERNUMBER") or voucher_number,
                "date": voucher_node.findtext("DATE") or "",
                "voucher_type": (
                    voucher_node.findtext("VOUCHERTYPENAME")
                    or voucher_node.get("VCHTYPE", "")
                    or voucher_type
                    or ""
                ),
                "party_name": voucher_node.findtext("PARTYLEDGERNAME") or "",
                "narration": voucher_node.findtext("NARRATION") or "",
                "guid": voucher_node.findtext("GUID") or guid or "",
                "items": [],
                "ledgers": [],
                "tax_breakdown": [],
                "total_amount": 0.0,
            }

            # Inventory entries
            for inv_tag in [
                "ALLINVENTORYENTRIES.LIST",
                "INVENTORYENTRIES.LIST",
                "INVENTORYENTRIESIN.LIST",
                "INVENTORYENTRIESOUT.LIST",
            ]:
                for inv in voucher_node.findall(inv_tag):
                    item_name = inv.findtext("STOCKITEMNAME") or ""
                    qty_str = inv.findtext("ACTUALQTY") or inv.findtext("BILLEDQTY") or "0"
                    rate_str = inv.findtext("RATE") or "0"
                    amt_str = inv.findtext("AMOUNT") or "0"

                    try:
                        qty = abs(float(qty_str.split()[0].replace(",", "")))
                    except Exception:
                        qty = 0.0

                    try:
                        rate = abs(float(rate_str.split("/")[0].replace(",", "")))
                    except Exception:
                        rate = 0.0

                    try:
                        amount = abs(float(amt_str.replace(",", "")))
                    except Exception:
                        amount = 0.0

                    if item_name:
                        result["items"].append({
                            "name": item_name,
                            "quantity": qty,
                            "rate": rate,
                            "amount": amount,
                            "godown": inv.findtext("GODOWNNAME") or "Main Location",
                            "batch": inv.findtext("BATCHNAME") or "",
                        })

            # Ledger entries
            total_dr = 0.0
            total_cr = 0.0

            for led_tag in ["ALLLEDGERENTRIES.LIST", "LEDGERENTRIES.LIST"]:
                for led in voucher_node.findall(led_tag):
                    led_name = led.findtext("LEDGERNAME") or ""
                    led_amt_str = led.findtext("AMOUNT") or "0"

                    try:
                        led_amt = float(led_amt_str.replace(",", ""))
                    except Exception:
                        led_amt = 0.0

                    if led_amt < 0:
                        total_cr += abs(led_amt)
                    else:
                        total_dr += led_amt

                    is_tax = any(
                        x in led_name.upper()
                        for x in ["GST", "TAX", "CESS", "DUTY", "CGST", "SGST", "IGST"]
                    )
                    entry = {"name": led_name, "amount": led_amt, "is_tax": is_tax}
                    result["ledgers"].append(entry)
                    if is_tax:
                        result["tax_breakdown"].append(entry)

            result["total_amount"] = max(total_dr, total_cr)
            logger.info(
                f"✅ Matched voucher #{result['voucher_number']} "
                f"type={result['voucher_type']} amount={result['total_amount']:.2f} "
                f"items={len(result['items'])} ledgers={len(result['ledgers'])}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to fetch voucher detail: {e}")
            return {}

    def fetch_stock_items_complete(self, company_name: Optional[str] = None) -> List[Dict]:
        """
        Fetch all stock items with complete details: HSN, GST rate, alternate units, etc.
        
        Returns:
            List of dicts with comprehensive stock item data
        """
        cname = company_name or self.company_name
        
        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
            <BODY>
                <EXPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>List of Accounts</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                            <ACCOUNTTYPE>Stock Items</ACCOUNTTYPE>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                </EXPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        
        try:
            xml_response = self.send_request(xml)
            xml_response = self._sanitize_xml(xml_response)
            root = ET.fromstring(xml_response)
            
            items = []
            
            for stock in root.iter("STOCKITEM"):
                name = stock.get("NAME") or stock.findtext("NAME") or ""
                if not name:
                    continue
                
                item = {
                    "name": name,
                    "alias": stock.findtext("ALIAS") or "",
                    "parent": stock.findtext("PARENT") or "",
                    "stock_group": stock.findtext("PARENT") or "",
                    "units": stock.findtext("BASEUNITS") or "Nos",
                    "alternate_unit": stock.findtext("ADDITIONALUNITS") or "",
                    "conversion_factor": 0.0,
                    "hsn_code": stock.findtext("GSTCLASSIFICATIONNAME") or stock.findtext("HSNCODE") or "",
                    "gst_rate": 0.0,
                    "taxability": stock.findtext("TAXABILITY") or "Taxable",
                    "opening_stock": 0.0,
                    "closing_balance": 0.0,
                    "cost_price": 0.0,
                    "selling_price": 0.0,
                    "mrp": 0.0,
                    "is_godown_tracking": stock.findtext("ISMAINTAININGBALANCES") == "Yes"
                }
                
                # Parse GST rate
                try:
                    gst_str = stock.findtext("GSTRATE") or stock.findtext("GSTTYPEOFSUPPLY") or "0"
                    item["gst_rate"] = float(gst_str.replace("%", ""))
                except:
                    pass
                
                # Parse closing balance
                try:
                    cb_str = stock.findtext("CLOSINGBALANCE") or "0"
                    item["closing_balance"] = abs(float(cb_str.split()[0].replace(",", "")))
                except:
                    pass
                
                # Parse opening stock
                try:
                    os_str = stock.findtext("OPENINGBALANCE") or "0"
                    item["opening_stock"] = abs(float(os_str.split()[0].replace(",", "")))
                except:
                    pass
                
                # Parse prices
                try:
                    item["cost_price"] = float(stock.findtext("STANDARDCOST") or "0")
                except:
                    pass
                
                try:
                    item["selling_price"] = float(stock.findtext("STANDARDPRICE") or "0")
                except:
                    pass
                
                try:
                    item["mrp"] = float(stock.findtext("MRP") or "0")
                except:
                    pass
                
                items.append(item)
            
            logger.info(f"📦 Fetched {len(items)} complete stock items")
            return items
            
        except Exception as e:
            logger.error(f"Failed to fetch stock items: {e}")
            return []

    def fetch_stock_movements(self, item_name: str = None, from_date: str = None, to_date: str = None, company_name: Optional[str] = None) -> List[Dict]:
        """
        Fetch stock movements (transactions) for an item or all items.
        
        Returns:
            List of dicts with movement details: date, type, quantity, rate, amount, voucher_ref
        """
        cname = company_name or self.company_name
        
        # Default to current FY
        if not from_date:
            now = datetime.now()
            if now.month < 4:
                from_date = f"{now.year - 1}0401"
            else:
                from_date = f"{now.year}0401"
        
        if not to_date:
            to_date = datetime.now().strftime("%Y%m%d")
        
        item_filter = f"<STOCKITEMNAME>{escape(item_name)}</STOCKITEMNAME>" if item_name else ""
        
        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
            <BODY>
                <EXPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>Stock Item Vouchers</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                            <SVFROMDATE>{from_date}</SVFROMDATE>
                            <SVTODATE>{to_date}</SVTODATE>
                            {item_filter}
                            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                </EXPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        
        try:
            xml_response = self.send_request(xml)
            xml_response = self._sanitize_xml(xml_response)
            root = ET.fromstring(xml_response)
            
            movements = []
            
            for voucher in root.iter("VOUCHER"):
                v_date = voucher.findtext("DATE") or ""
                v_type = voucher.findtext("VOUCHERTYPENAME") or voucher.get("VCHTYPE", "")
                v_number = voucher.findtext("VOUCHERNUMBER") or ""
                v_guid = voucher.findtext("GUID") or ""
                
                # Parse date
                movement_date = None
                if v_date:
                    try:
                        movement_date = datetime.strptime(v_date[:8], "%Y%m%d")
                    except:
                        pass
                
                # Determine movement type
                movement_type = "OUT"  # Default
                if "purchase" in v_type.lower():
                    movement_type = "IN"
                elif "sales" in v_type.lower():
                    movement_type = "OUT"
                elif "receipt" in v_type.lower() or "adjustment" in v_type.lower():
                    movement_type = "ADJUSTMENT"
                
                # Parse inventory entries
                for inv_tag in ["ALLINVENTORYENTRIES.LIST", "INVENTORYENTRIES.LIST",
                               "INVENTORYENTRIESIN.LIST", "INVENTORYENTRIESOUT.LIST"]:
                    for inv in voucher.findall(inv_tag):
                        stock_item = inv.findtext("STOCKITEMNAME") or ""
                        
                        # Skip if filtering by item and doesn't match
                        if item_name and stock_item.lower() != item_name.lower():
                            continue
                        
                        qty_str = inv.findtext("ACTUALQTY") or inv.findtext("BILLEDQTY") or "0"
                        rate_str = inv.findtext("RATE") or "0"
                        amt_str = inv.findtext("AMOUNT") or "0"
                        godown = inv.findtext("GODOWNNAME") or "Main Location"
                        
                        try:
                            qty = abs(float(qty_str.split()[0].replace(",", "")))
                        except:
                            qty = 0.0
                        
                        try:
                            rate = abs(float(rate_str.split("/")[0].replace(",", "")))
                        except:
                            rate = 0.0
                        
                        try:
                            amount = abs(float(amt_str.replace(",", "")))
                        except:
                            amount = 0.0
                        
                        movements.append({
                            "item_name": stock_item,
                            "movement_date": movement_date.isoformat() if movement_date else None,
                            "movement_type": movement_type,
                            "quantity": qty,
                            "rate": rate,
                            "amount": amount,
                            "godown": godown,
                            "voucher_type": v_type,
                            "voucher_number": v_number,
                            "voucher_guid": v_guid
                        })
            
            logger.info(f"📦 Fetched {len(movements)} stock movements" + (f" for {item_name}" if item_name else ""))
            return movements
            
        except Exception as e:
            logger.error(f"Failed to fetch stock movements: {e}")
            return []

    def fetch_cost_centers(self, company_name: Optional[str] = None) -> List[Dict]:
        """
        Fetch all cost centers from Tally.
        
        Returns:
            List of cost center dicts
        """
        cname = company_name or self.company_name
        
        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
            <BODY>
                <EXPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>List of Accounts</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                            <ACCOUNTTYPE>Cost Centres</ACCOUNTTYPE>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                </EXPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        
        try:
            xml_response = self.send_request(xml)
            xml_response = self._sanitize_xml(xml_response)
            root = ET.fromstring(xml_response)
            
            cost_centers = []
            
            for cc in root.iter("COSTCENTRE"):
                name = cc.get("NAME") or cc.findtext("NAME") or ""
                if name:
                    cost_centers.append({
                        "name": name,
                        "parent": cc.findtext("PARENT") or "",
                        "category": cc.findtext("CATEGORYNAME") or ""
                    })
            
            logger.info(f"📊 Fetched {len(cost_centers)} cost centers")
            return cost_centers
            
        except Exception as e:
            logger.error(f"Failed to fetch cost centers: {e}")
            return []

    def fetch_godown_stock(self, company_name: Optional[str] = None) -> List[Dict]:
        """
        Fetch stock levels by godown (warehouse).
        
        Returns:
            List of dicts with: godown_name, item_name, quantity, value
        """
        cname = company_name or self.company_name
        
        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
            <BODY>
                <EXPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>Godown Summary</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                </EXPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        
        try:
            xml_response = self.send_request(xml)
            xml_response = self._sanitize_xml(xml_response)
            root = ET.fromstring(xml_response)
            
            godown_stock = []
            current_godown = None
            
            for elem in root.iter():
                if elem.tag == "GODOWNNAME" or elem.tag == "DSPACCNAME":
                    if elem.text:
                        current_godown = elem.text.strip()
                
                # Try to find stock entries under each godown
                if elem.tag in ["BATCHALLOCATIONS.LIST", "STOCKINGODOWN.LIST"]:
                    item_name = elem.findtext("STOCKITEMNAME") or elem.findtext("NAME") or ""
                    qty_str = elem.findtext("CLOSINGBALANCE") or elem.findtext("BILLEDQTY") or "0"
                    val_str = elem.findtext("CLOSINGVALUE") or elem.findtext("AMOUNT") or "0"
                    
                    try:
                        qty = abs(float(qty_str.split()[0].replace(",", "")))
                    except:
                        qty = 0.0
                    
                    try:
                        val = abs(float(val_str.replace(",", "")))
                    except:
                        val = 0.0
                    
                    if item_name and qty > 0:
                        godown_stock.append({
                            "godown_name": current_godown or "Main Location",
                            "item_name": item_name,
                            "quantity": qty,
                            "value": val
                        })
            
            logger.info(f"📦 Fetched {len(godown_stock)} godown stock entries")
            return godown_stock
            
        except Exception as e:
            logger.error(f"Failed to fetch godown stock: {e}")
            return []
    
    # ========== END NEW METHODS ==========


    def fetch_vouchers(self, company_name: Optional[str] = None, voucher_type: Optional[str] = None, from_date: Optional[str] = None, to_date: Optional[str] = None) -> pd.DataFrame:
        cname = company_name or self.company_name
        voucher_type_xml = f"<VOUCHERTYPENAME>{escape(voucher_type)}</VOUCHERTYPENAME>" if voucher_type else ""
        
        date_range_xml = ""
        if from_date and to_date:
            # Ensure YYYYMMDD format
            date_range_xml = f"""
            <SVFROMDATE>{escape(from_date)}</SVFROMDATE>
            <SVTODATE>{escape(to_date)}</SVTODATE>
            """
            
        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
            <BODY>
                <EXPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>Voucher Register</REPORTNAME>
                        <STATICVARIABLES>
                            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                            {voucher_type_xml}
                            {date_range_xml}
                        </STATICVARIABLES>
                    </REQUESTDESC>
                </EXPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        xml_response = self.send_request(xml)
        logger.info(f"Tally fetch_vouchers response size: {len(xml_response)} bytes")
        if len(xml_response) < 500:
            logger.info(f"Response preview: {xml_response}")
        
        df = self._parse_voucher_xml(xml_response)
        logger.info(f"Parsed {len(df)} vouchers from response")
        return df

    def fetch_ledger_vouchers(self, ledger_name: str, company_name: Optional[str] = None) -> pd.DataFrame:
        cname = company_name or self.company_name
        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
            <BODY>
                <EXPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>Ledger Vouchers</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                            <LEDGERNAME>{escape(ledger_name)}</LEDGERNAME>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                </EXPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        xml_response = self.send_request(xml)
        return self._parse_voucher_xml(xml_response)

    def push_voucher(self, company_name: Optional[str], voucher_xml: str) -> Dict[str, Any]:
        """
        DEPRECATED: Use tally_live_update.create_voucher_safely instead.
        """
        logger.warning("Using deprecated method push_voucher. Please migrate to tally_live_update.")
        cname = company_name or self.company_name
        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
            <BODY>
                <IMPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>Vouchers</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                    <REQUESTDATA>
                        <TALLYMESSAGE>
                            {voucher_xml}
                        </TALLYMESSAGE>
                    </REQUESTDATA>
                </IMPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        xml_response = self.send_request(xml)
        return {"status": self._parse_response_status(xml_response), "raw": xml_response}

    def create_ledger_if_missing(self, ledger_name: str, parent_group: str = "Sundry Debtors") -> Dict[str, Any]:
        """
        Creates a ledger in Tally if it doesn't already exist.
        
        Args:
            ledger_name: Name of the ledger to create
            parent_group: Parent group (e.g., "Sundry Debtors", "Sundry Creditors", "Cash-in-hand")
            
        Returns:
            Dict with success status
        """
        cname = self.company_name or DEFAULT_COMPANY
        
        # First, check if ledger exists
        try:
            existing_ledgers = self.lookup_ledger(ledger_name)
            if existing_ledgers and ledger_name in existing_ledgers:
                logger.info(f"Ledger '{ledger_name}' already exists in Tally")
                return {"success": True, "message": "Ledger already exists"}
        except:
            pass  # If lookup fails, proceed to create
        
        # Create the ledger
        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
            <BODY>
                <IMPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>All Masters</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                    <REQUESTDATA>
                        <TALLYMESSAGE xmlns:UDF="TallyUDF">
                            <LEDGER NAME="{escape(ledger_name)}" ACTION="Create">
                                <NAME.LIST TYPE="String">
                                    <NAME>{escape(ledger_name)}</NAME>
                                </NAME.LIST>
                                <PARENT>{escape(parent_group)}</PARENT>
                                <ISBILLWISEON>Yes</ISBILLWISEON>
                                <ISCOSTCENTRESON>No</ISCOSTCENTRESON>
                            </LEDGER>
                        </TALLYMESSAGE>
                    </REQUESTDATA>
                </IMPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        
        logger.info(f"Creating ledger '{ledger_name}' under '{parent_group}'")
        result = self.push_xml(xml)
        
        if result.get("success"):
            logger.info(f"Successfully created ledger '{ledger_name}'")
            return {"success": True, "message": f"Created ledger '{ledger_name}'"}
        else:
            logger.error(f"Failed to create ledger '{ledger_name}': {result.get('errors')}")
            return {"success": False, "errors": result.get("errors")}

    def create_voucher(self, voucher_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        DEPRECATED: Use tally_live_update.create_voucher_safely instead.
        """
        logger.warning("Using deprecated method create_voucher. Please migrate to tally_live_update.")
        """
        Creates a voucher in Tally using the XML Import feature.
        Expects voucher_data to contain:
        - voucher_type: str (Sales, Purchase, Receipt, Payment)
        - date: str (YYYYMMDD)
        - party_name: str
        - amount: float
        - narration: str (optional)
        - items: List[Dict] (optional, for inventory vouchers)
          - name: str
          - quantity: float
          - rate: float
          - amount: float
        """
        cname = self.company_name or DEFAULT_COMPANY  # Auto-detected at init
        
        # AUTO-CREATE LEDGERS IF MISSING
        party_name = voucher_data.get("party_name")
        voucher_type = voucher_data.get("voucher_type", "")
        
        if party_name:
            # Determine parent group based on voucher type
            if voucher_type in ["Receipt", "Sales"]:
                parent_group = "Sundry Debtors"
            elif voucher_type in ["Payment", "Purchase"]:
                parent_group = "Sundry Creditors"
            else:
                parent_group = "Sundry Debtors"  # Default
            
            logger.info(f"Ensuring ledger '{party_name}' exists...")
            self.create_ledger_if_missing(party_name, parent_group)
        
        # Also ensure Cash/Bank ledger exists if specified
        deposit_to = voucher_data.get("deposit_to", "Cash")
        if deposit_to:
            if deposit_to.lower() == "cash":
                # Create Cash under Cash-in-Hand
                self.create_ledger_if_missing(deposit_to, "Cash-in-Hand")
            else:
                # For bank accounts, create under "Bank Accounts"
                self.create_ledger_if_missing(deposit_to, "Bank Accounts")
        
        # Basic XML construction (simplified for MVP)
        # In a real app, use a proper XML builder library
        
        items_xml = ""
        if "items" in voucher_data and voucher_data["items"]:
            for item in voucher_data["items"]:
                items_xml += f"""
                <ALLINVENTORYENTRIES.LIST>
                    <STOCKITEMNAME>{escape(item['name'])}</STOCKITEMNAME>
                    <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                    <RATE>{item['rate']}</RATE>
                    <AMOUNT>{-abs(item['amount'])}</AMOUNT> <!-- Credit for Sales -->
                    <ACTUALQTY>{item['quantity']}</ACTUALQTY>
                    <BILLEDQTY>{item['quantity']}</BILLEDQTY>
                </ALLINVENTORYENTRIES.LIST>
                """

        # Ledger entries - Different logic for different voucher types
        vch_type = voucher_data.get("voucher_type", "Sales")
        
        if vch_type == "Receipt":
            # Receipt: Cash/Bank (Dr) | Party (Cr)
            cash_account = voucher_data.get("deposit_to", "Cash")
            ledger_entries_xml = f"""
            <ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{escape(cash_account)}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                <AMOUNT>{abs(voucher_data['amount'])}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{escape(voucher_data['party_name'])}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                <AMOUNT>{-abs(voucher_data['amount'])}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            """
        elif vch_type == "Payment":
            # Payment: Party (Dr) | Cash/Bank (Cr)
            cash_account = voucher_data.get("deposit_to", "Cash")
            ledger_entries_xml = f"""
            <ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{escape(voucher_data['party_name'])}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                <AMOUNT>{abs(voucher_data['amount'])}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{escape(cash_account)}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                <AMOUNT>{-abs(voucher_data['amount'])}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            """
        else:
            # Sales/Purchase - Original logic
            is_sales = vch_type == "Sales"
            party_amount = -abs(voucher_data['amount']) if is_sales else abs(voucher_data['amount'])
            sales_account_name = voucher_data.get("sales_account", "Sales") # Allow custom sales account
            purchase_account_name = voucher_data.get("purchase_account", "Purchase") # Allow custom purchase account
            
            # Determine the contra ledger and its amount
            contra_ledger_name = sales_account_name if is_sales else purchase_account_name
            contra_amount = abs(voucher_data['amount']) if is_sales else -abs(voucher_data['amount'])
            
            ledger_entries_xml = f"""
            <ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{escape(voucher_data['party_name'])}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>{'Yes' if is_sales else 'No'}</ISDEEMEDPOSITIVE>
                <AMOUNT>{party_amount}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{escape(contra_ledger_name)}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>{'No' if is_sales else 'Yes'}</ISDEEMEDPOSITIVE>
                <AMOUNT>{contra_amount}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            """

        # Tally Edu Mode Handling
        # Edu mode only allows dates 1, 2, 31.
        # If enabled, we force the date to the 1st of the month to ensure acceptance.
        is_edu_mode = os.getenv("TALLY_EDU_MODE", "true").lower() == "true"
        from datetime import datetime
        raw_date = voucher_data.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # Ensure date is in YYYYMMDD format
        import re
        # Remove hyphens or slashes if present
        clean_date = re.sub(r'[^0-9]', '', str(raw_date))
        
        if len(clean_date) == 8:
            voucher_date = clean_date
        else:
            # Fallback if date is weird
            logger.warning(f"Invalid date format received: {raw_date}. Defaulting to today.")
            from datetime import datetime
            voucher_date = datetime.now().strftime("%Y%m%d")

        if is_edu_mode:
            # Force DD to 01
            original_date = voucher_date
            voucher_date = voucher_date[:6] + "01"
            if original_date != voucher_date:
                logger.info(f"Edu Mode: Adjusted voucher date from {original_date} to {voucher_date}")

        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
            <BODY>
                <IMPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>Vouchers</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                    <REQUESTDATA>
                        <TALLYMESSAGE xmlns:UDF="TallyUDF">
                            <VOUCHER ACTION="Create">
                                <DATE>{voucher_date}</DATE>
                                <VOUCHERTYPENAME>{escape(voucher_data['voucher_type'])}</VOUCHERTYPENAME>
                                <NARRATION>{escape(voucher_data.get('narration', 'Created via K24'))}</NARRATION>
                                {ledger_entries_xml}
                            </VOUCHER>
                        </TALLYMESSAGE>
                    </REQUESTDATA>
                </IMPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        
        logger.info(f"🚀 PUSHING VOUCHER TO TALLY - START")
        logger.info(f"=" * 80)
        logger.info(f"VOUCHER XML BEING SENT:")
        logger.info(xml)
        logger.info(f"=" * 80)
        
        try:
            xml_response = self.send_request(xml)
            logger.info(f"✅ TALLY RESPONSE RECEIVED:")
            logger.info(f"=" * 80)
            logger.info(xml_response)
            logger.info(f"=" * 80)
            
            parsed_status = self._parse_response_status(xml_response)
            logger.info(f"📊 PARSED STATUS: {parsed_status}")
            
            return {
                "status": parsed_status,
                "raw_response": xml_response,
                "raw_request": xml
            }
        except Exception as e:
            logger.error(f"❌ ERROR COMMUNICATING WITH TALLY: {e}")
            return {"status": "Error", "raw_response": str(e), "raw_request": xml}

    def delete_voucher(self, voucher_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deletes a voucher in Tally.
        Requires identifying info (Date, VoucherType, VoucherNumber or MasterID).
        For simplicity in this MVP, we try to match by Date + VchType + VchNo if available,
        or we might need the GUID if we stored it.
        """
        cname = self.company_name or DEFAULT_COMPANY
        
        # To delete, we need to identify the voucher. 
        # Tally deletion usually requires the exact original ID (GUID/MasterId) or the composite key.
        # Here we assume we have the GUID or we construct the same key.
        
        # If we have a GUID/MasterID, it's best.
        # Otherwise, we try to delete by VchNo + Date + Type
        
        date_val = voucher_data.get('date', '20240401')
        vch_type = voucher_data.get('voucher_type', 'Sales')
        vch_no = voucher_data.get('voucher_number')
        
        # Tally Delete XML
        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
            <BODY>
                <IMPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>Vouchers</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                    <REQUESTDATA>
                        <TALLYMESSAGE xmlns:UDF="TallyUDF">
                            <VOUCHER VCHTYPE="{escape(vch_type)}" ACTION="Delete" OBJVIEW="Invoice Voucher View">
                                <DATE>{date_val}</DATE>
                                <VOUCHERTYPENAME>{escape(vch_type)}</VOUCHERTYPENAME>
                                <VOUCHERNUMBER>{escape(vch_no)}</VOUCHERNUMBER>
                                <!-- If we had GUID/MasterID, we'd put it here -->
                            </VOUCHER>
                        </TALLYMESSAGE>
                    </REQUESTDATA>
                </IMPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        return self.push_xml(xml)

    @staticmethod
    def _parse_ledger_xml(xml_text: str) -> pd.DataFrame:
        try:
            # Sanitize before parsing
            xml_text = TallyConnector._sanitize_xml(xml_text)
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logging.error(f"XML ParseError: {e}; raw: {xml_text[:2000]}")
            return pd.DataFrame()
        rows = []
        for ledger in root.iter("LEDGER"):
            data = flatten_element(ledger)
            rows.append(data)
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    @staticmethod
    def _sanitize_xml(xml_text: str) -> str:
        """
        Robustly sanitize XML from Tally.
        1. Removes invalid XML 1.0 characters (control chars).
        2. Fixes common Tally issues like unescaped ampersands or invalid entities.
        """
        import re
        
        # 1. Remove invalid XML 1.0 characters
        # Valid: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
        # We construct a regex to MATCH INVALID characters and replace them
        # Note: We keep \t, \n, \r
        xml_text = re.sub(r'[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\u10000-\u10FFFF]', '', xml_text)

        # 2. Handle specific Tally garbage like &#x4; which is invalid in XML 1.0
        # This regex finds numeric entities that resolve to invalid chars
        def replace_entity(match):
            try:
                # Get the number
                ent = match.group(1)
                if ent.startswith('x'):
                    val = int(ent[1:], 16)
                else:
                    val = int(ent)
                # Check if valid
                if (val == 0x9 or val == 0xA or val == 0xD or 
                    (0x20 <= val <= 0xD7FF) or 
                    (0xE000 <= val <= 0xFFFD) or 
                    (0x10000 <= val <= 0x10FFFF)):
                    return match.group(0) # Keep valid
                return '' # Remove invalid
            except:
                return match.group(0)

        xml_text = re.sub(r'&#(x?[0-9a-fA-F]+);', replace_entity, xml_text)
        
        return xml_text

    @staticmethod
    def _parse_voucher_xml(xml_text: str) -> pd.DataFrame:
        """
        Parse Tally voucher XML and extract meaningful voucher data.
        Handles nested ALLLEDGERENTRIES.LIST structure properly.
        """
        try:
            # Sanitize before parsing
            xml_text = TallyConnector._sanitize_xml(xml_text)
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logging.error(f"XML ParseError: {e}")
            logging.error(f"First 2000 chars: {xml_text[:2000]}")
            return pd.DataFrame()
        
        rows = []
        
        # Find all TALLYMESSAGE tags (Tally 9+ format)
        for tallymessage in root.iter("TALLYMESSAGE"):
            for voucher in tallymessage.findall("VOUCHER"):
                voucher_data = TallyConnector._extract_voucher_data(voucher)
                if voucher_data:
                    rows.append(voucher_data)
        
        # If no TALLYMESSAGE found, try direct VOUCHER tags (older format)
        if not rows:
            for voucher in root.iter("VOUCHER"):
                voucher_data = TallyConnector._extract_voucher_data(voucher)
                if voucher_data:
                    rows.append(voucher_data)
        
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    
    @staticmethod
    def _extract_voucher_data(voucher_elem) -> dict:
        """
        Extract structured data from a single VOUCHER element.
        Returns a dictionary with voucher details.
        """
        data = {}
        
        # Get voucher type from attributes
        data['voucher_type'] = voucher_elem.attrib.get('VCHTYPE', '')
        
        # Get voucher number
        vch_num = voucher_elem.find('VOUCHERNUMBER')
        data['voucher_number'] = vch_num.text if vch_num is not None and vch_num.text else ''
        
        # Get date and parse it (format: YYYYMMDD)
        date_elem = voucher_elem.find('DATE')
        if date_elem is not None and date_elem.text:
            date_str = date_elem.text
            try:
                # Parse YYYYMMDD format
                from datetime import datetime
                data['date'] = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
            except:
                data['date'] = date_str
        else:
            data['date'] = ''
        
        # Get narration
        narration = voucher_elem.find('NARRATION')
        data['narration'] = narration.text if narration is not None and narration.text else ''
        
        # Extract ledger entries — Tally uses different tag names depending on version/report:
        #   ALLLEDGERENTRIES.LIST  → TallyPrime "all ledger entries" (most common in Day Book)
        #   LEDGERENTRIES.LIST     → Older Tally 9 / Voucher Register exports
        #   LEDGERENTRIESIN.LIST   → Some receipt/payment vouchers
        #   LEDGERENTRIESOUT.LIST  → Some payment vouchers
        # We must check ALL of them to reliably get amounts.
        _LEDGER_TAGS = [
            'ALLLEDGERENTRIES.LIST',
            'LEDGERENTRIES.LIST',
            'LEDGERENTRIESIN.LIST',
            'LEDGERENTRIESOUT.LIST',
        ]

        # Prefer PARTYLEDGERNAME from the voucher element itself (fastest & most reliable)
        party_name = voucher_elem.findtext('PARTYLEDGERNAME', '').strip()
        total_amount = 0.0

        for tag in _LEDGER_TAGS:
            for ledger in voucher_elem.findall(f'.//{tag}'):
                ledger_name_elem = ledger.find('LEDGERNAME')
                amount_elem = ledger.find('AMOUNT')

                if ledger_name_elem is not None and ledger_name_elem.text:
                    ledger_name = ledger_name_elem.text.strip()

                    # Get amount
                    if amount_elem is not None and amount_elem.text:
                        try:
                            amount = float(amount_elem.text.replace(',', ''))
                            if abs(amount) > abs(total_amount):
                                total_amount = abs(amount)
                                # Only overwrite party_name from ledger if we didn't
                                # get it from PARTYLEDGERNAME directly
                                if not party_name:
                                    party_name = ledger_name
                        except ValueError:
                            pass

        data['party_name'] = party_name
        data['amount'] = total_amount
        
        return data

    @staticmethod
    def _parse_generic_xml(xml_text: str, tag_name: str) -> pd.DataFrame:
        try:
            # Sanitize before parsing
            xml_text = TallyConnector._sanitize_xml(xml_text)
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logging.error(f"XML ParseError: {e}")
            return pd.DataFrame()
        rows = []
        for item in root.iter(tag_name):
            data = flatten_element(item)
            rows.append(data)
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    @staticmethod
    def _parse_response_status(xml_text: str) -> str:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logging.error(f"XML ParseError: {e}; raw: {xml_text[:2000]}")
            return "Unknown"
        resp = root.find("RESPONSE")
        return resp.text.strip() if resp is not None else "OK"

    def fetch_group_summary(self, group_name: str = "Sundry Debtors") -> List[Dict[str, Any]]:
        """
        Fetch balance summary for a specific group (e.g., Sundry Debtors).
        Returns list of dicts with 'name' and 'closing_balance'.
        """
        cname = self.company_name or DEFAULT_COMPANY
        xml = f"""
        <ENVELOPE>
            <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
            <BODY>
                <EXPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>Group Summary</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                            <GROUPNAME>{escape(group_name)}</GROUPNAME>
                            <EXPLODEFLAG>Yes</EXPLODEFLAG>
                            <ISITEMWISE>Yes</ISITEMWISE>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                </EXPORTDATA>
            </BODY>
        </ENVELOPE>
        """
        try:
            xml_resp = self.send_request(xml)
            return self._parse_group_summary_xml(xml_resp)
        except Exception as e:
            logger.error(f"Failed to fetch {group_name} summary: {e}")
            return []

    def fetch_closing_balances_from_bills(self, report_name: str = "Bills Receivable") -> List[Dict[str, Any]]:
        """
        Fetch closing balances by aggregating outstanding bills. 
        Reliable for Debtors/Creditors when Group Summary is incomplete.
        """
        cname = self.company_name or DEFAULT_COMPANY
        xml = f"""<ENVELOPE>
            <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
            <BODY>
                <EXPORTDATA>
                    <REQUESTDESC>
                        <REPORTNAME>{escape(report_name)}</REPORTNAME>
                        <STATICVARIABLES>
                            <SVCURRENTCOMPANY>{escape(cname)}</SVCURRENTCOMPANY>
                            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                        </STATICVARIABLES>
                    </REQUESTDESC>
                </EXPORTDATA>
            </BODY>
        </ENVELOPE>"""

        response = self.send_request(xml)
        
        # Parse flat XML
        balances = {}
        try:
             # Basic clean incase of weird chars
            response = self._sanitize_xml(response)
            root = ET.fromstring(response)
            
            current_party = None
            
            # Iterate all children (flat structure)
            for child in root:
                if child.tag == "BILLFIXED":
                    # New Bill Block
                    party_node = child.find("BILLPARTY")
                    if party_node is not None:
                        current_party = party_node.text
                
                elif child.tag == "BILLCL":
                    # Closing Balance for the PREVIOUS BILLFIXED entry
                    if current_party and child.text:
                        try:
                            # Parse amount
                            amt = float(child.text.replace(",", ""))
                            
                            # Tally BILLCL tag already returns positive values for Bills Receivable.
                            # We store debtors as positive (Dr = money owed to us).
                            # No sign inversion needed — abs() ensures consistent sign regardless.
                            amt = abs(amt)
                                
                            balances[current_party] = balances.get(current_party, 0.0) + amt
                        except ValueError:
                            pass
                        
        except Exception as e:
            logger.error(f"Error parsing {report_name}: {e}")
            return []
            
        # Convert to list of dicts to match fetch_group_summary format
        return [{"name": k, "closing_balance": v} for k, v in balances.items()]

    @staticmethod
    def _parse_group_summary_xml(xml_text: str) -> List[Dict[str, Any]]:
        try:
            # Clean and sanitize before creating ElementTree
            xml_text = TallyConnector._sanitize_xml(xml_text)
            root = ET.fromstring(xml_text)
        except:
            return []
            
        rows = []
        # Tally Group Summary XML structure is sequential
        current_name = None
        
        # Iterate all elements for robustness
        for child in root.iter():
            if child.tag == "DSPDISPNAME": # Display Name usually inside DSPACCNAME
                 current_name = child.text.strip() if child.text else None
            
            elif child.tag == "DSPACCINFO" and current_name:
                # Inside DSPACCINFO, find amounts
                
                dr_elem = child.find(".//DSPCLDRAMT/DSPCLDRAMTA") 
                if dr_elem is None: dr_elem = child.find(".//DSPCLDRAMTA")
                
                cr_elem = child.find(".//DSPCLCRAMT/DSPCLCRAMTA")
                if cr_elem is None: cr_elem = child.find(".//DSPCLCRAMTA")
                
                dr_val = 0.0
                if dr_elem is not None and dr_elem.text:
                    try: dr_val = float(dr_elem.text.replace(",",""))
                    except: pass
                    
                cr_val = 0.0
                if cr_elem is not None and cr_elem.text:
                    try: cr_val = float(cr_elem.text.replace(",",""))
                    except: pass
                
                # Net Balance: Debit - Credit
                balance = dr_val - cr_val
                
                rows.append({
                    "name": current_name,
                    "closing_balance": balance,
                    "debit": dr_val,
                    "credit": cr_val
                })
                current_name = None # Reset after matching Info

        return rows

def get_customer_details(ledgers_df: pd.DataFrame, party_name: str) -> dict:
    if ledgers_df.empty:
        logger.warning(f"Ledgers DataFrame is empty, cannot lookup '{party_name}'")
        return {}
    ledgers_df = normalize_columns(ledgers_df)
    name_col = next((c for c in ledgers_df.columns if 'name' in c), None)
    if name_col is None:
        logger.warning(f"No recognized name column found in ledgers. Available columns: {list(ledgers_df.columns)}")
        return {}
    try:
        match = ledgers_df[ledgers_df[name_col].astype(str).str.strip().str.lower() == party_name.strip().lower()]
        if match.empty:
            logger.warning(f"Customer '{party_name}' not found in live ledgers (fallback?)")
            return {}
        row = match.iloc[0].to_dict()
        details = {
            'GSTIN': row.get('gstin', '') or row.get('gstin/uin', ''),
            'PAN': row.get('incometaxnumber', '') or row.get('pan', ''),
            'ADDRESS': row.get('address', '') or row.get('mailingname', ''),
            # Add/adjust fields to suit your Tally ledger XML!
        }
        logger.info(f"Enriched customer details for '{party_name}': {details}")
        return details
    except Exception as ex:
        logger.error(f"Failed to lookup customer '{party_name}': {ex}")
        return {}



# Example usage:
if __name__ == "__main__":
    tc = TallyConnector()
    company = "SHREE JI SALES"  # Replace this with your actual company name!
    logger.info("Fetching ledgers...")
    df_ledgers = tc.fetch_ledgers(company)
    logger.info(df_ledgers.head())
