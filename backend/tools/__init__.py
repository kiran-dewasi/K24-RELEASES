"""
Tool definitions for the K24 agent.
These are functions the agent can call to take actions.
"""

from langchain_core.tools import tool
from backend.background_jobs import job_manager
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

# ============================================================================
# CUSTOMER/LEDGER TOOLS
# ============================================================================

from pydantic import BaseModel, Field

class ItemEntry(BaseModel):
    name: str = Field(..., description="Exact Stock Item Name as recognized in Tally (e.g., 'Jeera', 'Rice'). Fix spelling if needed.")
    qty: str = Field(..., description="Quantity (Numeric or with Unit). Example: '3000' or '3000 kg'.")
    unit: str = Field(..., description="Unit of measurement (e.g., kg, mtr). Default to 'kg' if not specified.")
    rate: str = Field(..., description="Rate per unit (e.g., '245/kg', '500/box').")
    amount: float = Field(..., description="Total Line Amount. Calculate as Qty * Rate if not explicitly stated.")


# Module-level tenant override: set by run_agent() before each AI invocation
# so that every tool call in that session uses the correct per-user tenant_id.
_CURRENT_TENANT_ID: str = ""


def _get_tenant() -> str:
    """Resolve tenant_id with priority:
    1. Module-level override set by run_agent() for the current AI session
    2. Supabase-synced local User table
    3. 'default' fallback (logged and warned)
    """
    # 1. Per-session override from run_agent()
    if _CURRENT_TENANT_ID:
        return _CURRENT_TENANT_ID
    # 2. User table (synced from Supabase at login)
    from backend.dependencies import get_tenant_id
    return get_tenant_id()


def _today() -> str:
    """Return today's date as YYYYMMDD."""
    return datetime.now().strftime("%Y%m%d")


def _is_duplicate_voucher(party_name: str, amount: float, voucher_type: str, window_seconds: int = 60) -> bool:
    """
    Idempotency guard: returns True if an identical voucher was created in the last `window_seconds`.
    Prevents the AI from pushing the same transaction twice on retry.
    """
    try:
        from backend.database import SessionLocal, Voucher
        from datetime import timedelta
        db = SessionLocal()
        try:
            cutoff = datetime.now() - timedelta(seconds=window_seconds)
            existing = db.query(Voucher).filter(
                Voucher.party_name == party_name,
                Voucher.voucher_type.ilike(f"%{voucher_type}%"),
                Voucher.amount.between(amount * 0.99, amount * 1.01),
                Voucher.created_at >= cutoff
            ).first()
            return existing is not None
        finally:
            db.close()
    except Exception:
        return False  # On error, allow creation

@tool
def get_top_outstanding() -> str:
    """
    Get top outstanding receivables (customers who owe money).
    Call this IMMEDIATELY if user asks "Show receivables", "Pending payments", etc. with NO name.
    Reads from local DB (instant) — no Tally required.
    """
    try:
        # DB-first: read from shadow DB
        from backend.database import SessionLocal, Ledger
        from sqlalchemy import desc
        tenant_id = _get_tenant()
        db = SessionLocal()
        try:
            top = db.query(Ledger).filter(
                Ledger.tenant_id == tenant_id,
                Ledger.parent.ilike("%debtor%"),
                Ledger.closing_balance > 0
            ).order_by(desc(Ledger.closing_balance)).limit(5).all()

            if top:
                msg = "Here are the top pending receivables:\n"
                for d in top:
                    msg += f"- {d.name}: ₹{d.closing_balance:,.2f}\n"
                msg += "\nDo you want to follow up with any specific customer?"
                return msg
        finally:
            db.close()

        # Fallback: query Tally directly
        import requests, xml.etree.ElementTree as ET
        xml = """<ENVELOPE>
    <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
    <BODY><EXPORTDATA><REQUESTDESC>
        <REPORTNAME>DeepFetcher</REPORTNAME>
        <STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES>
        <TDL>
            <COLLECTION NAME="DebtorsList">
                <TYPE>Ledger</TYPE><CHILDOF>Sundry Debtors</CHILDOF>
                <FETCH>Name,ClosingBalance</FETCH>
                <FILTERS>PositiveOnly</FILTERS>
            </COLLECTION>
            <SYSTEM TYPE="Formulae" NAME="PositiveOnly">$ClosingBalance != 0</SYSTEM>
        </TDL>
    </REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"""
        resp = requests.post("http://localhost:9000", data=xml,
                             headers={'Content-Type': 'text/xml'}, timeout=5)
        root = ET.fromstring(resp.text)
        debtors = []
        for ledger in root.findall(".//LEDGER"):
            name = ledger.get("NAME") or ledger.findtext("NAME")
            bal_str = ledger.findtext("CLOSINGBALANCE")
            if name and bal_str:
                try:
                    bal = float(bal_str)
                    if bal != 0:
                        debtors.append({"name": name, "amount": abs(bal)})
                except Exception:
                    pass
        debtors.sort(key=lambda x: x["amount"], reverse=True)
        top_5 = debtors[:5]
        if not top_5:
            return "No outstanding receivables found."
        msg = "Here are the top pending receivables:\n"
        for d in top_5:
            msg += f"- {d['name']}: ₹{d['amount']:,.2f}\n"
        msg += "\nDo you want to follow up with any specific customer?"
        return msg
    except Exception as e:
        return f"Error fetching receivables: {e}"
@tool
def create_customer(
    name: str,
    gst_number: str,
    address: str = "",
    phone: str = "",
    email: str = ""
) -> str:
    """
    Create a new customer in Tally.
    Use this when user asks to create a customer, party, or client.

    Args:
        name: Customer/party name (required)
            Example: "Sharma & Sons", "ABC Traders"
        gst_number: GST registration number (required for India)
            Example: "18AABTU5055K1Z0"
        address: Customer address (optional)
        phone: Customer phone number (optional)
        email: Customer email (optional)

    Returns:
        Confirmation message with task ID
    """
    try:
        print(f"\U0001f527 Tool called: create_customer")
        tenant_id = _get_tenant()
        ledger_data = {
            'name': name,
            'gst': gst_number,
            'type': 'customer',
            'address': address,
            'phone': phone,
            'email': email,
            'tenant_id': tenant_id
        }

        import asyncio, nest_asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        nest_asyncio.apply(loop)
        result = loop.run_until_complete(
            job_manager.enqueue_create_ledger(ledger_data=ledger_data, user_id=tenant_id)
        )

        if isinstance(result, str):
            task_id = "queued"
        else:
            task_id = result.get('task_id', 'unknown')

        return f"\u2713 Created customer '{name}' (GST: {gst_number}). Task ID: {task_id}."

    except Exception as e:
        return f"\u2717 Error creating customer: {str(e)}"

@tool
def create_vendor(
    name: str,
    gst_number: str,
    address: str = "",
    phone: str = "",
    email: str = ""
) -> str:
    """
    Create a new vendor/supplier in Tally.
    Use this when user asks to create a vendor, supplier, or service provider.

    Args:
        name: Vendor/supplier name
        gst_number: GST registration number
        address: Vendor's address (optional)
        phone: Vendor's phone (optional)
        email: Vendor's email (optional)

    Returns:
        Confirmation message
    """
    try:
        print(f"\U0001f527 Tool called: create_vendor")
        tenant_id = _get_tenant()
        ledger_data = {
            'name': name,
            'gst': gst_number,
            'type': 'vendor',
            'address': address,
            'phone': phone,
            'email': email,
            'tenant_id': tenant_id
        }

        import asyncio, nest_asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        nest_asyncio.apply(loop)
        result = loop.run_until_complete(
            job_manager.enqueue_create_ledger(ledger_data=ledger_data, user_id=tenant_id)
        )

        if isinstance(result, str):
            task_id = "queued"
        else:
            task_id = result.get('task_id', 'unknown')

        return f"\u2713 Created vendor '{name}'. Task ID: {task_id}"

    except Exception as e:
        return f"\u2717 Error creating vendor: {str(e)}"


# ============================================================================
# INVOICE/VOUCHER TOOLS
# ============================================================================
@tool
def create_sales_invoice(
    party_name: str,
    items: List[ItemEntry] = Field(
        default_factory=list,
        description="EXTRACT structured line items from the user's message. Example: 'Buy 10kg sugar at 40' -> [{'name': 'Sugar', 'qty': '10 kg', 'rate': '40/kg', 'amount': 400}]. DO NOT put item details in 'description'."
    ),
    amount: float = 0.0,
    narration: str = "Created via K24 AI"
) -> str:
    """
    Create a sales invoice in Tally.
    Use this when user asks to create an invoice, bill, or sale document.
    Auto-creates missing Parties/Items internally.

    Args:
        party_name: Name of the customer/party (required)
        items: List of line items (Strict Schema)
        amount: Invoice amount (Optional, auto-calculated from items if 0)
        narration: Narration
    """
    try:
        print(f"🔧 Tool called: create_sales_invoice")
        tenant_id = _get_tenant()

        # Auto-Calculate Total Amount if missing
        if amount == 0 and items:
            amount = sum(item.amount for item in items)
            print(f"   Auto-Calculated Amount: {amount}")

        # Idempotency guard — prevent duplicate if AI retries
        if _is_duplicate_voucher(party_name, amount, "Sales"):
            return f"⚠️ A Sales invoice for '{party_name}' of ₹{amount} was already created just now. Skipping duplicate."

        items_dicts = [item.model_dump() for item in items]

        from .invoice_tool import invoice_tool
        from backend.database import SessionLocal
        import asyncio, nest_asyncio

        db = SessionLocal()
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            nest_asyncio.apply(loop)
            result = loop.run_until_complete(invoice_tool.create_sales_invoice(
                tenant_id=tenant_id,
                party_name=party_name,
                amount=amount,
                items=items_dicts,
                source='agent',
                db=db
            ))
            if result['status'] == 'success':
                return f"✅ Invoice created! ID: {result.get('voucher_id')} | Tally ID: {result.get('tally_voucher_id')}"
            else:
                return f"❌ Failed to create invoice: {result.get('error')}"
        finally:
            db.close()

    except Exception as e:
        return f"❌ Error creating invoice: {str(e)}"

@tool
def create_purchase_invoice(
    vendor_name: str,
    items: List[ItemEntry] = Field(
        default_factory=list,
        description="EXTRACT structured line items from the user's message. Example: 'Buy 10kg sugar at 40' -> [{'name': 'Sugar', 'qty': '10 kg', 'rate': '40/kg', 'amount': 400}]. DO NOT put item details in 'description'."
    ),
    amount: float = 0.0, # Optional, calculated from items
    date: str = "",
    description: str = ""
) -> str:
    """
    Create a verified purchase invoice in Tally.
    Use this when user asks to create a purchase bill or purchase document.

    Args:
        vendor_name: Name of the vendor/supplier
        items: List of line items
        amount: Purchase amount (Optional, calculated if 0)
        date: Invoice date (YYYY-MM-DD)
        description: Purchase description
    """
    try:
        print(f"🔧 Tool called: create_purchase_invoice (TallyEngine Upgrade)")
        
        # 1. Convert Items
        items_payload = []
        for item in items:
            # Parse Unit/Qty logic if needed, but TallyEngine expects specific keys
            # ItemEntry has: name, qty (str with unit), rate (str), amount
            # We need to parse "10 kg" -> qty=10, unit="kg"
            
            raw_qty = item.qty.lower()
            import re
            qty_match = re.match(r"([\d\.]+)\s*(\w+)?", raw_qty)
            qty_val = 1.0
            unit_val = "nos"
            
            if qty_match:
                qty_val = float(qty_match.group(1))
                if qty_match.group(2):
                    unit_val = qty_match.group(2)
            
            # Parse Rate "40/kg" -> 40
            raw_rate = item.rate
            rate_match = re.match(r"([\d\.]+)", raw_rate)
            rate_val = float(rate_match.group(1)) if rate_match else 0.0
            
            items_payload.append({
                "name": item.name,
                "quantity": qty_val,
                "unit": unit_val,
                "rate": rate_val,
                "taxable_amount": item.amount
            })

        # 2. Invoke Engine
        from backend.tally_engine import TallyEngine
        engine = TallyEngine()
        
        # Date Handling
        if not date:
            from datetime import datetime
            date = datetime.now().strftime("%Y%m%d")
        else:
            date = date.replace("-", "")

        payload = {
            "voucher_type": "Purchase",
            "date": date,
            "party_name": vendor_name,
            "items": items_payload,
            "description": description
        }
        
        result = engine.process_purchase_request(payload)
        
        if result.get("status") == "success":
            return f"✅ Purchase Invoice Created Successfully! (Msg: {result.get('message')})"
        else:
            return f"❌ Failed to create Purchase Invoice: {result.get('message')}"

    except Exception as e:
        return f"❌ Error creating purchase: {str(e)}"

@tool
def create_receipt(
    party_name: str,
    amount: float,
    payment_method: str = "Cash",
    date: str = "",
    description: str = ""
) -> str:
    """
    Create a receipt in Tally.
    Use this for payment receipts or money received documents.

    Args:
        party_name: Customer/party name
        amount: Receipt amount
        payment_method: How payment was made (Cash, Check, Bank Transfer, etc.)
        date: Receipt date (YYYYMMDD)
        description: Receipt notes
    """
    try:
        print(f"🔧 Tool called: create_receipt")

        # Idempotency guard
        if _is_duplicate_voucher(party_name, amount, "Receipt"):
            return f"⚠️ A Receipt for '{party_name}' of ₹{amount} was already created just now. Skipping duplicate."

        voucher_data = {
            'type': 'Receipt',
            'party': party_name,
            'amount': amount,
            'payment_method': payment_method,
            'date': date or _today(),
            'description': description,
            'tenant_id': _get_tenant()
        }

        import asyncio, nest_asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        nest_asyncio.apply(loop)
        result = loop.run_until_complete(
            job_manager.enqueue_create_voucher(voucher_data=voucher_data, user_id=_get_tenant())
        )

        if isinstance(result, str):
            task_id = "queued"
        else:
            task_id = result.get('task_id', 'unknown')

        return f"✓ Receipt created for '{party_name}' (₹{amount} via {payment_method}). Task ID: {task_id}"

    except Exception as e:
        return f"✗ Error creating receipt: {str(e)}"


# ============================================================================
# INFORMATION TOOLS
# ============================================================================
@tool
def get_customer_balance(customer_name: str) -> str:
    """
    Get outstanding balance for a customer.
    Reads from local DB first (instant) — falls back to Tally if not found.
    Args:
        customer_name: Name of the customer
    """
    try:
        # DB-first
        from backend.database import SessionLocal, Ledger
        tenant_id = _get_tenant()
        db = SessionLocal()
        try:
            ledger = db.query(Ledger).filter(
                Ledger.tenant_id == tenant_id,
                Ledger.name.ilike(f"%{customer_name}%")
            ).first()
            if ledger:
                return f"Outstanding Balance for '{ledger.name}': ₹{ledger.closing_balance:,.2f}"
        finally:
            db.close()

        # Fallback: Tally
        from backend.tally_reader import TallyReader
        reader = TallyReader()
        check = reader.get_ledger_details(customer_name)
        if not check["exists"]:
            if check.get("candidates"):
                return f"Customer '{customer_name}' not found. Did you mean: {', '.join(check['candidates'])}?"
            return f"Customer '{customer_name}' not found in Tally."
        tally_name = check["name"]
        balance = reader.get_closing_balance(tally_name)
        return f"Outstanding Balance for '{tally_name}': ₹{balance}"
    except Exception as e:
        return f"Error fetching balance: {str(e)}"

@tool
def list_customers() -> str:
    """
    Get list of all ledgers (focusing on customers) in Tally using TallyReader.
    """
    try:
        from backend.tally_reader import TallyReader
        reader = TallyReader()
        ledgers = reader.get_all_ledgers()
        
        if not ledgers:
            return "No ledgers found in Tally."
        
        # Filter for typical customer names or just return top 50
        # TallyReader returns list of strings
        return "Ledgers in Tally:\n" + "\n".join(ledgers[:50])
        
    except Exception as e:
        return f"Error listing ledgers: {str(e)}"

# ============================================================================
# NEW ROBUST TALLY TOOLS (Engine & Reader)
# ============================================================================
@tool
def get_tally_transactions(
    start_date: str, 
    end_date: str, 
    party_filter: Optional[str] = None
) -> str:
    """
    Fetch transactions (Daybook) from Tally for a date range.
    Returns formatted data that MUST be displayed in the response.
    
    Args:
        start_date: YYYYMMDD string (e.g. '20260122' for Jan 22, 2026)
        end_date: YYYYMMDD string
        party_filter: Optional name of party to filter by.
    """
    try:
        from backend.tally_reader import TallyReader
        from datetime import datetime
        
        # Sanitize Dates (Remove / - .)
        c_start = start_date.replace("-", "").replace("/", "").replace(".", "").strip()
        c_end = end_date.replace("-", "").replace("/", "").replace(".", "").strip()
        
        # Heuristic: If length > 8, maybe typo at start (e.g. 22024...). Take last 8.
        if len(c_start) > 8: c_start = c_start[-8:]
        if len(c_end) > 8: c_end = c_end[-8:]
        
        if len(c_start) != 8 or len(c_end) != 8:
             return f"Invalid date format. Got '{c_start}' and '{c_end}'. Please use YYYYMMDD format."

        reader = TallyReader()
        txns = reader.get_transactions(c_start, c_end, party_filter)
        
        if not txns:
            # Format the date range for display
            try:
                start_dt = datetime.strptime(c_start, "%Y%m%d")
                end_dt = datetime.strptime(c_end, "%Y%m%d")
                date_range = f"{start_dt.strftime('%b %d, %Y')} to {end_dt.strftime('%b %d, %Y')}"
            except:
                date_range = f"{c_start} to {c_end}"
            return f"No transactions found for the period {date_range}."
        
        # Format dates for display
        try:
            start_dt = datetime.strptime(c_start, "%Y%m%d")
            end_dt = datetime.strptime(c_end, "%Y%m%d")
            if c_start == c_end:
                date_header = start_dt.strftime("%b %d, %Y")
            else:
                date_header = f"{start_dt.strftime('%b %d')} to {end_dt.strftime('%b %d, %Y')}"
        except:
            date_header = f"{c_start} to {c_end}"
        
        # Build markdown table for AI to display
        output = f"📊 **Transactions for {date_header}** ({len(txns)} found)\n\n"
        output += "| Date | Type | Party | Amount | Ref |\n"
        output += "|------|------|-------|--------|-----|\n"
        
        total_sales = 0.0
        total_purchases = 0.0
        total_receipts = 0.0
        total_payments = 0.0
        
        for txn in txns[:15]:  # Limit for context window
            # Get amount from ledger entries
            amt = 0.0
            try:
                entries = txn.get('ledger_entries', [])
                if entries:
                    amt = abs(float(entries[0].get('amount', 0)))
            except:
                pass
            
            # Track totals by type
            v_type = (txn.get('type') or '').lower()
            if 'sale' in v_type:
                total_sales += amt
            elif 'purchase' in v_type:
                total_purchases += amt
            elif 'receipt' in v_type:
                total_receipts += amt
            elif 'payment' in v_type:
                total_payments += amt
            
            # Format date
            txn_date = txn.get('date', '')
            try:
                dt = datetime.strptime(txn_date, "%Y%m%d")
                txn_date = dt.strftime("%d %b")
            except:
                pass
            
            # Format amount in Indian style
            amt_str = f"₹{amt:,.0f}" if amt else "-"
            
            output += f"| {txn_date} | {txn['type']} | {txn['party'][:20]} | {amt_str} | {txn['number'][:10]} |\n"
        
        if len(txns) > 15:
            output += f"\n*... and {len(txns) - 15} more transactions*\n"
        
        # Summary
        output += "\n### 📈 Summary\n"
        if total_sales > 0:
            output += f"- **Total Sales:** ₹{total_sales:,.0f}\n"
        if total_purchases > 0:
            output += f"- **Total Purchases:** ₹{total_purchases:,.0f}\n"
        if total_receipts > 0:
            output += f"- **Total Receipts:** ₹{total_receipts:,.0f}\n"
        if total_payments > 0:
            output += f"- **Total Payments:** ₹{total_payments:,.0f}\n"
        
        grand_total = total_sales + total_purchases + total_receipts + total_payments
        if grand_total > 0:
            output += f"\n**Grand Total: ₹{grand_total:,.0f}**"
        
        return output
        
    except Exception as e:
        return f"Error fetching transactions: {e}"


@tool
def get_tally_ledger_details(name: str) -> str:
    """
    Check if a Ledger exists in Tally and get its details.
    Args:
        name: Name of the ledger/party to find.
    """
    try:
        from backend.tally_reader import TallyReader
        reader = TallyReader()
        res = reader.get_ledger_details(name)
        return json.dumps(res, indent=2)
    except Exception as e:
        return f"Error checking ledger: {e}"

@tool
def create_purchase_voucher_verified(
    party_name: str,
    items: List[Dict[str, Any]],
    date: str = "20240401",
    party_state: str = "Karnataka"
) -> str:
    """
    Create a Purchase Voucher with strict Verification and optional GST.
    Uses 'Chain of Truth' to ensure Ledgers/Items exist before creation.
    
    Args:
        party_name: Name of Supplier.
        items: List of dicts with keys: {'name', 'unit', 'quantity', 'rate', 'tax_rate'(optional)}.
        date: YYYYMMDD.
        party_state: State of supplier (for GST logic).
    """
    try:
        from backend.tally_engine import TallyEngine
        engine = TallyEngine()
        payload = {
            "voucher_type": "Purchase",
            "date": date,
            "party_name": party_name,
            "party_state": party_state,
            "items": items
        }
        res = engine.process_purchase_request(payload)
        return json.dumps(res)
    except Exception as e:
        return f"Error creating voucher: {e}"

@tool
def check_stock_levels() -> str:
    """
    Get current stock summary (Items, Quantity, Value).
    Reads from local DB — instant, no Tally required.
    Returns JSON string for table rendering.
    """
    try:
        from backend.database import SessionLocal, StockItem
        tenant_id = _get_tenant()
        db = SessionLocal()
        try:
            items = db.query(StockItem).filter(StockItem.tenant_id == tenant_id).all()
            if items:
                data = [
                    {
                        "name": i.name,
                        "closing_balance": i.closing_balance or 0,
                        "rate": i.rate or 0,
                        "value": (i.closing_balance or 0) * (i.rate or 0)
                    }
                    for i in items
                ]
                return json.dumps(data)
        finally:
            db.close()

        # Fallback: Tally
        from backend.tally_reader import TallyReader
        reader = TallyReader()
        data = reader.get_stock_summary()
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def check_outstanding_payments() -> str:
    """
    Get list of customers with outstanding payments (Receivables).
    Reads from local DB — instant, no Tally required.
    Returns JSON string for table rendering.
    """
    try:
        from backend.database import SessionLocal, Ledger
        from sqlalchemy import desc
        tenant_id = _get_tenant()
        db = SessionLocal()
        try:
            debtors = db.query(Ledger).filter(
                Ledger.tenant_id == tenant_id,
                Ledger.parent.ilike("%debtor%"),
                Ledger.closing_balance > 0
            ).order_by(desc(Ledger.closing_balance)).all()
            if debtors:
                data = [
                    {"party_name": d.name, "amount": d.closing_balance}
                    for d in debtors
                ]
                return json.dumps(data)
        finally:
            db.close()

        # Fallback: Tally
        from backend.tally_reader import TallyReader
        reader = TallyReader()
        data = reader.get_receivables()
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def create_tally_voucher(
    voucher_type: str,
    party_name: str,
    ledger_name: str = "Cash",
    amount: float = 0.0,
    items: List[ItemEntry] = None,
    description: str = "",
    date: str = ""
) -> str:
    """
    Universal Tally Voucher Creator (Sales, Purchase, Payment, Receipt).
    Use this for ANY financial transaction request.

    Args:
        voucher_type: One of ['Sales', 'Purchase', 'Payment', 'Receipt', 'Contra'].
        party_name: The main party or expense ledger (e.g., "Raj Traders", "Office Rent").
        ledger_name: The source/dest ledger (e.g., "Cash", "HDFC Bank"). Default: "Cash".
                     For Sales/Purchase, this is ignored (uses internal Sales/Purchase A/c).
        amount: Total amount. Auto-calculated if items provided.
        items: List of items (Only for Sales/Purchase).
        description: Narration.
        date: Date in YYYYMMDD or YYYY-MM-DD. Defaults to today.
    """
    try:
        from backend.tally_engine import TallyEngine
        voucher_type = voucher_type.title()
        print(f"🔧 Tool called: create_tally_voucher ({voucher_type})")

        # Idempotency guard for financial vouchers
        if voucher_type in ["Receipt", "Payment"] and amount > 0:
            if _is_duplicate_voucher(party_name, amount, voucher_type):
                return f"⚠️ A {voucher_type} for '{party_name}' of ₹{amount} was already created just now. Skipping duplicate."

        # Default to today if no date
        txn_date = (date.replace("-", "") if date else _today())

        engine = TallyEngine()

        # Parse items
        items_payload = []
        if items:
            import re
            for item in items:
                raw_qty = item.qty.lower()
                qty_match = re.match(r"([\d\.]+)\s*(\w+)?", raw_qty)
                qty_val, unit_val = 1.0, "kg"
                if qty_match:
                    qty_val = float(qty_match.group(1))
                    if qty_match.group(2):
                        unit_val = qty_match.group(2)
                rate_match = re.match(r"([\d\.]+)", str(item.rate))
                rate_val = float(rate_match.group(1)) if rate_match else 0.0
                items_payload.append({
                    "name": item.name,
                    "quantity": qty_val,
                    "unit": unit_val,
                    "rate": rate_val,
                    "taxable_amount": item.amount
                })

        if voucher_type in ["Sales", "Purchase"]:
            payload = {
                "voucher_type": voucher_type,
                "party_name": party_name,
                "items": items_payload,
                "date": txn_date
            }
            if voucher_type == "Sales":
                res = engine.process_sales_request(payload)
            else:
                res = engine.process_purchase_request(payload)
        else:
            payload = {
                "voucher_type": voucher_type,
                "party_name": party_name,
                "amount_ledger": ledger_name,
                "amount": amount,
                "date": txn_date
            }
            res = engine.process_financial_voucher(payload)

        if res.get("status") == "success":
            return f"✅ {voucher_type} Voucher Created! {res.get('message')}"
        else:
            return f"❌ Failed: {res.get('message')}"

    except Exception as e:
        return f"Error creating voucher: {str(e)}"

# ============================================================================
# EXPORT ALL TOOLS
# ============================================================================
TOOLS = [
    create_customer,
    create_vendor,
    create_sales_invoice,
    create_purchase_invoice,
    create_receipt,
    get_customer_balance,
    list_customers,
    # New Tools
    get_tally_transactions,
    get_tally_ledger_details,
    create_purchase_voucher_verified,
    create_tally_voucher, # Universal Tool
    get_top_outstanding,
    # Reporting Tools
    check_stock_levels,
    check_outstanding_payments
]

# Exports for Graph/Routers
ALL_TOOLS = TOOLS

# Read-only tools
SAFE_TOOLS = [
    get_customer_balance,
    list_customers,
    get_tally_transactions,
    get_tally_ledger_details,
    check_stock_levels,
    check_outstanding_payments
]

# Tools that modify state
SENSITIVE_TOOLS = [
    create_customer,
    create_vendor,
    create_sales_invoice,
    create_purchase_invoice,
    create_receipt,
    create_purchase_voucher_verified,
    create_tally_voucher
]
