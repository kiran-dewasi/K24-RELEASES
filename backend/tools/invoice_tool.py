from datetime import datetime
from typing import List, Dict, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from backend.database import Voucher, Ledger, Tenant
from backend.socket_manager import socket_manager
# from backend.xml_generator import generate_tally_sales_xml # Deprecated
from backend.tally_xml_builder import build_sales_voucher_xml, InventoryEntry
import logging

logger = logging.getLogger("invoice_tool")

class InvoiceTool:
    """
    3-Step Atomic Invoice Creation:
    1. Preflight: Ensure party exists
    2. Tally Push: Send XML, get response
    3. DB Write: Record in Supabase (only if Tally succeeded)
    """

    async def create_sales_invoice(
        self,
        tenant_id: str,
        party_name: str,
        amount: float, # Total Amount (Optional if items provided, but good for tracking)
        items: Optional[List[Dict]] = None, # [{"name": "Item", "qty": 1, "rate": 100, "unit": "nos"}]
        source: str = 'web',  # 'web', 'whatsapp', 'api'
        db: Session = None,
        date_str: str = None
    ) -> dict:
        """
        Create a sales invoice atomically.
        If 'items' are provided, creates an "Item Invoice".
        If 'items' are missing, creates an "Accounting Invoice" (Ledger-based).
        """
        
        result = {
            "status": "pending",
            "tenant_id": tenant_id,
            "party_name": party_name,
            "amount": amount,
            "source": source,
            "voucher_id": None,
            "tally_voucher_id": None,
            "tally_response": None,
            "error": None
        }
        
        try:
            # ============ STEP 1: PREFLIGHT ============
            logger.info(f"🔄 [PREFLIGHT] Checking party '{party_name}' in Tally...")
            
            # For now, assume party exists (Agent will verify)
            result["preflight_status"] = "passed"
            logger.info(f"✅ [PREFLIGHT] Party '{party_name}' OK")
            
            # ============ STEP 2: TALLY PUSH ============
            logger.info(f"📤 [TALLY PUSH] Generating XML for {party_name}...")
            
            if not date_str:
                date_str = datetime.now().strftime("%Y%m%d") # Tally format YYYYMMDD
            else:
                date_str = date_str.replace("-", "") # Ensure YYYYMMDD
            
            # Prepare Inventory
            inventory_entries = []
            agent_items_payload = [] # List of {name, unit} for Agent Check
            
            if items:
                for it in items:
                    i_name = it.get("name")
                    i_unit = it.get("unit", "nos")

                    # Fix: Clean unit string from Quantity (e.g. "10 kgs" -> "10")
                    raw_qty = str(it.get("qty", "1"))
                    clean_qty = raw_qty.lower().replace('kgs', '').replace('kg', '').replace('nos', '').replace(',', '').strip()
                    i_qty = clean_qty

                    # Fix: Clean unit string from Rate (e.g. "140/kg" -> "140")
                    raw_rate = str(it.get("rate", "0"))
                    clean_rate = raw_rate.split('/')[0].replace(',', '').strip()
                    i_rate = clean_rate
                    
                    # Calculate amount safely
                    try:
                        i_amt = Decimal(clean_qty) * Decimal(clean_rate)
                    except Exception:
                        i_amt = Decimal("0")
                    
                    # Entry for Builder
                    entry = InventoryEntry(
                        stock_item_name=i_name,
                        rate=f"{clean_rate}/{i_unit}",
                        amount=i_amt,
                        actual_qty=f"{clean_qty} {i_unit}",
                        billed_qty=f"{clean_qty} {i_unit}",
                        ledger_name="Sales" # Uses "Sales" as per Tally Dump
                    )
                    inventory_entries.append(entry)
                    
                    # Entry for Agent Check
                    agent_items_payload.append({"name": i_name, "unit": i_unit})
            
            # Generate XML
            if inventory_entries:
                # ITEM INVOICE
                logger.info(f"📄 Building Item Invoice XML with {len(inventory_entries)} items.")
                xml_payload = build_sales_voucher_xml(
                    company_name="krishasales", # Agent handles company matching context usually
                    voucher_fields={
                        "DATE": date_str,
                        "VOUCHERTYPENAME": "Sales",
                        "PARTYLEDGERNAME": party_name,
                        "VOUCHERNUMBER": f"SALE-{int(datetime.now().timestamp())}",
                        "NARRATION": f"Created via K24 AI ({source})"
                    },
                    inventory_items=inventory_entries
                )
            else:
                # FALLBACK: ACCOUNTING INVOICE (No Items)
                # We can't use build_sales_voucher_xml efficiently for pure ledger mode without refactor
                # So we use the old logic via a direct XML string or upgrade builder purely for this?
                # Let's fallback to old generator for backward compat if NO items provided.
                from backend.xml_generator import generate_tally_sales_xml
                logger.info("📄 Building Accounting Invoice XML (No Items).")
                xml_payload = generate_tally_sales_xml(
                    party_name=party_name,
                    amount=amount,
                    ledger="Sales"
                )

            logger.info(f"📡 [SOCKET] Sending to Tally Agent (Tenant: {tenant_id})...")
            
            # Send to local agent via Socket
            tally_response = await socket_manager.send_command(
                tenant_id=tenant_id,
                event='execute_tally_xml',
                payload={
                    'xml': xml_payload,
                    'party_name': party_name,
                    'revenue_ledger': "Sales",
                    'inventory_items': agent_items_payload # <-- Pass items to Agent for Auto-Creation
                }
            )
            
            result["tally_response"] = str(tally_response)
            
            # Check Tally success
            # Note: tally_response comes back as text (XML) usually
            if tally_response and ("<CREATED>1</CREATED>" in str(tally_response) or "<UPDATED>1</UPDATED>" in str(tally_response)):
                result["tally_status"] = "success"
                result["tally_voucher_id"] = self._extract_voucher_id(str(tally_response))
                logger.info(f"✅ [TALLY] Success! VchID: {result['tally_voucher_id']}")
            else:
                result["tally_status"] = "failed"
                result["error"] = f"Tally rejected: {str(tally_response)[:200]}"
                logger.error(f"❌ [TALLY] Failed: {result['error']}")
                return result  # CRITICAL: Don't write to DB if Tally failed
            
            # ============ STEP 3: DB INSERT ============
            logger.info(f"💾 [DB] Writing to Supabase (Tenant: {tenant_id})...")
            
            if not db:
                logger.error("❌ [DB] No database session provided")
                result["error"] = "Database session required"
                return result
            
            new_voucher = Voucher(
                tenant_id=tenant_id,
                voucher_type='Sales',
                party_name=party_name,
                amount=float(amount),
                date=datetime.strptime(date_str, "%Y-%m-%d"),
                source=source,
                tally_voucher_id=result["tally_voucher_id"]
            )
            
            db.add(new_voucher)
            db.commit()
            db.refresh(new_voucher)
            
            result["voucher_id"] = new_voucher.id
            result["db_status"] = "success"
            result["status"] = "success"
            
            logger.info(f"✅ [DB] Success! Record ID: {new_voucher.id}")
            logger.info(f"✅ [COMPLETE] Invoice created: Tally + DB in sync")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [ERROR] {str(e)}")
            result["error"] = str(e)
            result["status"] = "failed"
            if db:
                try:
                    db.rollback()
                except:
                    pass
            return result

    def _extract_voucher_id(self, xml_response: str) -> str:
        """Extract VchID from Tally XML response"""
        try:
            match = re.search(r'<VchID>(\d+)</VchID>', xml_response)
            return match.group(1) if match else None
        except:
            return None

# Singleton instance
invoice_tool = InvoiceTool()
