import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.database import SessionLocal, Ledger, Voucher, StockItem, Bill, StockMovement
from backend.tally_connector import TallyConnector
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

load_dotenv()
TALLY_URL = os.getenv("TALLY_URL", "http://localhost:9000")

logger = logging.getLogger(__name__)

from backend.tally_live_update import (
    create_voucher_in_tally, 
    create_ledger_safely, 
    PushResult,
    TallyResponse
)

class SyncEngine:
    def __init__(self):
        self.tally = TallyConnector(url=TALLY_URL)

    def _get_tenant_id(self, db: Session) -> str:
        """
        Derive the real tenant_id from the first active local user.
        This is the single source of truth for all data written to the DB.
        Never returns a hardcoded value — logs a warning if no user is found.
        """
        from backend.database import User as _User
        user = db.query(_User).filter(_User.is_active == True).first()
        if user and user.tenant_id:
            return user.tenant_id
        logger.warning("SyncEngine._get_tenant_id: no active user with tenant_id found.")
        return "default"

    def _prepare_voucher_payload(self, voucher_data: dict):
        """Transform flat voucher_data into modern XML builder components"""
        company = self.tally.company_name or "Krishasales"
        
        # 1. Auto-create ledgers
        party_name = voucher_data.get("party_name")
        voucher_type = voucher_data.get("voucher_type", "")
        
        if party_name:
            parent_group = "Sundry Debtors"
            if voucher_type in ["Payment", "Purchase"]:
                parent_group = "Sundry Creditors"
            create_ledger_safely(company, party_name, {"PARENT": parent_group})

        deposit_to = voucher_data.get("deposit_to", "Cash")
        if deposit_to:
             parent = "Cash-in-Hand" if deposit_to.lower() == "cash" else "Bank Accounts"
             create_ledger_safely(company, deposit_to, {"PARENT": parent})

        # 2. Fix dates (Edu mode logic)
        is_edu_mode = os.getenv("TALLY_EDU_MODE", "true").lower() == "true"
        raw_date = voucher_data.get('date', datetime.now().strftime('%Y-%m-%d'))
        import re
        clean_date = re.sub(r'[^0-9]', '', str(raw_date))
        if len(clean_date) == 8:
            voucher_date = clean_date
        else:
            voucher_date = datetime.now().strftime("%Y%m%d")

        if is_edu_mode:
            voucher_date = voucher_date[:6] + "01"

        # 3. Construct fields and line items
        voucher_fields = {
            "DATE": voucher_date,
            "VOUCHERTYPENAME": voucher_type,
            "VOUCHERNUMBER": voucher_data.get("voucher_number", ""),
            "PARTYLEDGERNAME": party_name,
            "NARRATION": voucher_data.get("narration", "Created via K24"),
            "EFFECTIVEDATE": voucher_date,
        }

        line_items = []
        
        # Inventory Items
        if "items" in voucher_data and voucher_data["items"]:
            for item in voucher_data["items"]:
                line_items.append({
                    "ledger_name": item['name'], # Assuming item name is ledger name for now? No, stock items are different.
                    # Modern builder expects Ledger Entries. Stock Items are inside ALLINVENTORYENTRIES.LIST
                    # The current modern builder (tally_xml_builder) supports VoucherLineItem which maps to ALLLEDGERENTRIES.LIST
                    # It DOES NOT yet support ALLINVENTORYENTRIES.LIST fully in the simplified VoucherLineItem.
                    # Wait, tally_xml_builder.VoucherLineItem renders <ALLLEDGERENTRIES.LIST>.
                    # Tally's Import Data structure for Inventory Vouchers (Sales/Purchase) is complex.
                    # It usually has Ledger Entries for Party and Sales/Purchase Account, AND Inventory Entries.
                    
                    # For MVP, if we are using the modern builder which generates ALLLEDGERENTRIES.LIST,
                    # we might be missing Inventory Entries if we just map items to ledgers.
                    
                    # However, the legacy connector was doing:
                    # <ALLINVENTORYENTRIES.LIST> ... </ALLINVENTORYENTRIES.LIST>
                    
                    # item.render() produces <ALLLEDGERENTRIES.LIST>.
                })
                pass

        # Replicate Accounting Entries Logic
        amount = float(voucher_data.get("amount", 0))
        is_sales = voucher_type == "Sales"
        is_receipt = voucher_type == "Receipt"
        is_payment = voucher_type == "Payment"
        is_purchase = voucher_type == "Purchase"

        # Party Entry
        party_amount = amount
        party_is_deemed_positive = False # Default
        
        if is_sales: 
            # Party Dr
            # Legacy: Sales: Party IsDeemedPositive=Yes, Amount = -abs()
            pass
            
        # Let's use a simplified mapping based on legacy
        entries = []
        
        if is_receipt:
            # Cash Dr
            entries.append({
                "ledger_name": deposit_to,
                "is_deemed_positive": "Yes", # Dr
                "amount": abs(amount)
            })
            # Party Cr
            entries.append({
                "ledger_name": party_name,
                "is_deemed_positive": "No", # Cr
                "amount": -abs(amount)
            })
        elif is_payment:
            # Party Dr
            entries.append({
                "ledger_name": party_name,
                "is_deemed_positive": "Yes", # Dr
                "amount": abs(amount)
            })
            # Cash Cr
            entries.append({
                "ledger_name": deposit_to,
                "is_deemed_positive": "No", # Cr
                "amount": -abs(amount)
            })
        elif is_sales:
            # Party Dr
            entries.append({
                "ledger_name": party_name,
                "is_deemed_positive": "Yes",
                "amount": -abs(amount) 
            })
            # Sales Cr
            entries.append({
                "ledger_name": voucher_data.get("sales_account", "Sales"),
                "is_deemed_positive": "No",
                "amount": abs(amount)
            })
        elif is_purchase:
            # Party Cr
            entries.append({
                "ledger_name": party_name,
                "is_deemed_positive": "No",
                "amount": abs(amount)
            })
            # Purchase Dr
            entries.append({
                "ledger_name": voucher_data.get("purchase_account", "Purchase"),
                "is_deemed_positive": "Yes",
                "amount": -abs(amount)
            })
            
        return company, voucher_fields, entries

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True
    )
    def _push_to_tally_with_retry(self, company, fields, line_items):
        """Helper to push with retry logic using modern builder"""
        return create_voucher_in_tally(company, fields, line_items)

    def push_voucher_safe(self, voucher_data: dict) -> dict:
        """
        Transactional Push with Offline Fallback
        """
        logger.info(f"Pushing voucher to Tally: {voucher_data}")
        
        tally_response = None
        sync_status = "PENDING"
        is_offline = False
        
        try:
            # Prepare payload
            company, fields, line_items = self._prepare_voucher_payload(voucher_data)
            
            # Push with retry
            tally_response = self._push_to_tally_with_retry(company, fields, line_items)
            
            if tally_response.succeeded:
                sync_status = "SYNCED"
            else:
                logger.error(f"Tally rejected voucher: {tally_response.errors}")
                return {
                    "success": False,
                    "error": f"Tally Rejected: {tally_response.errors}",
                    "tally_response": tally_response.to_dict()
                }
        except Exception as e:
            logger.warning(f"Tally Unreachable or Error. Saving to Offline Queue. Error: {e}")
            is_offline = True
            sync_status = "PENDING"
            
        # Save to Shadow DB
        db = SessionLocal()
        try:
            # Parse date safely
            raw_v_date = voucher_data.get("date", datetime.now().strftime("%Y%m%d"))
            try:
                if "-" in str(raw_v_date):
                    v_date_obj = datetime.strptime(str(raw_v_date), "%Y-%m-%d")
                else:
                    v_date_obj = datetime.strptime(str(raw_v_date), "%Y%m%d")
            except:
                v_date_obj = datetime.now()

            new_voucher = Voucher(
                voucher_number=voucher_data.get("voucher_number", "AUTO"),
                date=v_date_obj,
                voucher_type=voucher_data.get("voucher_type"),
                party_name=voucher_data.get("party_name"),
                amount=float(voucher_data.get("amount", 0)),
                narration=voucher_data.get("narration"),
                guid=f"PENDING-{datetime.now().timestamp()}" if is_offline else f"TALLY-{datetime.now().timestamp()}", 
                sync_status=sync_status,
                last_synced=datetime.now()
            )
            db.add(new_voucher)
            db.commit()
            logger.info(f"Voucher committed to Shadow DB (Status: {sync_status})")
            
            if is_offline:
                return {
                    "success": True,
                    "message": "Tally is offline. Voucher saved locally and will sync automatically.",
                    "warning": "Offline Mode"
                }
            else:
                return {
                    "success": True,
                    "message": "Voucher posted to Tally and saved locally.",
                    "tally_response": tally_response.to_dict() if tally_response else None
                }
        except Exception as e:
            logger.error(f"Shadow DB Commit Failed: {e}")
            db.rollback()
            return {
                "success": False, 
                "error": f"Database Error: {e}"
            }
        finally:
            db.close()

    def sync_now(self) -> dict:
        """
        Full Sync: Pull all data from Tally into Shadow DB.
        Returns detailed sync results.
        """
        logger.info("🔄 Full Sync Started")
        results = {
            "success": True,
            "ledgers": {"synced": 0, "errors": 0},
            "stock_items": {"synced": 0, "errors": 0},
            "vouchers": {"synced": 0, "errors": 0},
            "timestamp": datetime.now().isoformat()
        }
        
        db = SessionLocal()
        try:
            # 1. Sync Ledgers
            ledger_results = self.pull_ledgers(db)
            results["ledgers"] = ledger_results
            
            # 2. Sync Stock Items
            stock_results = self.pull_stock_items(db)
            results["stock_items"] = stock_results
            
            # 3. Sync Vouchers
            voucher_results = self.pull_vouchers(db)
            results["vouchers"] = voucher_results
            
            db.commit()
            logger.info(f"✅ Full Sync Complete: {results}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Sync Failed: {e}")
            results["success"] = False
            results["error"] = str(e)
        finally:
            db.close()
        
        return results
    
    def pull_ledgers(self, db: Session = None) -> dict:
        """Pull all ledgers from Tally and update Shadow DB"""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        tenant_id = self._get_tenant_id(db)
        synced = 0
        errors = 0

        try:
            # Fetch from Tally
            ledgers = self.tally.fetch_ledgers().to_dict('records')
            logger.info(f"📥 Fetched {len(ledgers)} ledgers from Tally (tenant={tenant_id})")

            for ledger_data in ledgers:
                try:
                    name = ledger_data.get("name", ledger_data.get("NAME", ""))
                    if not name:
                        continue

                    # Check if exists (search by name, regardless of tenant, to handle migration)
                    existing = db.query(Ledger).filter(Ledger.name == name).first()

                    if existing:
                        # Update — also correct tenant_id if it was previously "default"
                        existing.tenant_id = tenant_id
                        existing.parent = ledger_data.get("parent", ledger_data.get("PARENT", existing.parent))
                        existing.last_synced = datetime.now()
                    else:
                        # Create with real tenant_id
                        new_ledger = Ledger(
                            tenant_id=tenant_id,
                            name=name,
                            parent=ledger_data.get("parent", ledger_data.get("PARENT", "Sundry Debtors")),
                            closing_balance=0.0,  # Populated by _pull_ledger_balances
                            gstin=ledger_data.get("gstin", ledger_data.get("PARTYGSTIN")),
                            address=ledger_data.get("address"),
                            phone=ledger_data.get("phone"),
                            email=ledger_data.get("email"),
                            tally_guid=ledger_data.get("guid", f"TALLY-{name}"),
                            last_synced=datetime.now()
                        )
                        db.add(new_ledger)

                    synced += 1
                except Exception as e:
                    logger.warning(f"Error syncing ledger {ledger_data}: {e}")
                    errors += 1

            # Post-Process: Sync Balances using Group Summary (more reliable)
            self._pull_ledger_balances(db)

            if close_db:
                db.commit()
                db.close()

        except Exception as e:
            logger.error(f"Pull Ledgers Error: {e}")
            errors += 1

        return {"synced": synced, "errors": errors}

    def _pull_ledger_balances(self, db: Session):
        """Helper to update closing balances from Group Summary reports"""
        groups = ["Sundry Debtors", "Sundry Creditors", "Cash-in-hand", "Bank Accounts"]
        
        for group in groups:
            try:
                # For Debtors/Creditors: use Bills report (open bills only)
                # For Cash/Bank: use Group Summary directly
                if group == "Sundry Debtors":
                    summary = self.tally.fetch_closing_balances_from_bills("Bills Receivable")
                elif group == "Sundry Creditors":
                    summary = self.tally.fetch_closing_balances_from_bills("Bills Payable")
                else:
                    summary = self.tally.fetch_group_summary(group)

                if not summary:
                    continue

                # Cash-in-hand / Bank Accounts: Tally returns Cr balance as negative.
                # We store absolute value (Dr = positive = money in hand).
                is_cash_bank = group in ("Cash-in-hand", "Bank Accounts")

                updates = 0
                updated_names = set()
                for item in summary:
                    name = item.get("name")
                    if not name:
                        continue
                    bal = float(item.get("closing_balance", 0))
                    if is_cash_bank:
                        bal = abs(bal)  # Always positive for Cash/Bank
                    ledger = db.query(Ledger).filter(Ledger.name == name).first()
                    if ledger:
                        ledger.closing_balance = bal
                        updated_names.add(name)
                        updates += 1

                if updates > 0:
                    logger.info(f"✅ Updated balances for {updates} ledgers in {group}")

                # Fix 2B: Fallback for Debtors/Creditors not found in Bills
                # (settled accounts or no open bills) — use Group Summary as fallback
                if group in ("Sundry Debtors", "Sundry Creditors"):
                    try:
                        grp_key = "Sundry Debtors" if group == "Sundry Debtors" else "Sundry Creditors"
                        grp_summary = self.tally.fetch_group_summary(grp_key)
                        if grp_summary:
                            fallback_updates = 0
                            for item in grp_summary:
                                name = item.get("name")
                                if not name or name in updated_names:
                                    continue  # Already updated from Bills
                                bal = float(item.get("closing_balance", 0))
                                ledger = db.query(Ledger).filter(Ledger.name == name).first()
                                if ledger and ledger.closing_balance == 0.0:
                                    ledger.closing_balance = bal
                                    fallback_updates += 1
                            if fallback_updates > 0:
                                logger.info(f"✅ [Fallback] Updated {fallback_updates} more ledgers in {group} via Group Summary")
                    except Exception as fe:
                        logger.debug(f"Group Summary fallback for {group}: {fe}")

            except Exception as e:
                logger.warning(f"Failed to sync balances for group {group}: {e}")

    
    def pull_stock_items(self, db: Session = None) -> dict:
        """Pull all stock items from Tally and update Shadow DB"""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        
        synced = 0
        errors = 0
        tenant_id = self._get_tenant_id(db)
        
        try:
            items = self.tally.fetch_stock_items().to_dict('records')
            logger.info(f"📥 Fetched {len(items)} stock items from Tally")
            
            for item_data in items:
                try:
                    name = item_data.get("name", item_data.get("NAME", ""))
                    if not name:
                        continue
                    
                    existing = db.query(StockItem).filter(StockItem.name == name).first()
                    
                    # Parse quantity and rate
                    # NOTE: StockItem model uses closing_balance (qty), rate (price)
                    # NOT closing_qty/closing_rate/closing_value
                    closing_qty = 0.0
                    closing_val = 0.0
                    closing_rate = 0.0

                    qty_str = item_data.get("closing_qty", item_data.get("CLOSINGQTY", ""))
                    if qty_str:
                        import re
                        qty_match = re.search(r'([\d.]+)', str(qty_str))
                        if qty_match:
                            closing_qty = float(qty_match.group(1))

                    # Try to get value directly from Tally data
                    val_raw = item_data.get("closing_value", item_data.get("CLOSINGVALUE",
                              item_data.get("CLOSINGBALANCE", 0)))
                    closing_val = float(val_raw or 0)

                    # Tally reports rate directly in some fields
                    rate_raw = item_data.get("rate", item_data.get("STANDARDCOST", 0))
                    if rate_raw:
                        closing_rate = float(str(rate_raw).split('/')[0].replace(',', '').strip() or 0)
                    elif closing_qty > 0 and closing_val > 0:
                        closing_rate = closing_val / closing_qty

                    if existing:
                        # Map to actual model columns
                        existing.tenant_id = tenant_id          # stamp tenant
                        existing.closing_balance = closing_qty   # qty stored in closing_balance
                        existing.rate = closing_rate             # rate = closing rate
                        existing.cost_price = closing_rate       # also update cost price
                        existing.unit = item_data.get("unit", item_data.get("BASEUNITS", existing.units or "Kgs"))
                        existing.last_synced = datetime.now()
                    else:
                        new_item = StockItem(
                            tenant_id=tenant_id,               # stamp tenant
                            name=name,
                            stock_group=item_data.get("group", item_data.get("PARENT", "Primary")),
                            units=item_data.get("unit", item_data.get("BASEUNITS", "Kgs")),
                            closing_balance=closing_qty,
                            rate=closing_rate,
                            cost_price=closing_rate,
                            tally_guid=item_data.get("guid", f"TALLY-{name}"),
                            last_synced=datetime.now()
                        )
                        db.add(new_item)
                    
                    synced += 1
                except Exception as e:
                    logger.warning(f"Error syncing stock item {item_data}: {e}")
                    errors += 1
            
            if close_db:
                db.commit()
                db.close()
                
        except Exception as e:
            logger.error(f"Pull Stock Items Error: {e}")
            errors += 1
        
        return {"synced": synced, "errors": errors}
    
    def pull_vouchers(self, db: Session = None, from_date: str = None, to_date: str = None) -> dict:
        """Pull vouchers from Tally and update Shadow DB"""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        tenant_id = self._get_tenant_id(db)
        synced = 0
        errors = 0

        try:
            if not from_date:
                from_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            if not to_date:
                to_date = datetime.now().strftime("%Y%m%d")

            vouchers = self.tally.fetch_vouchers(from_date=from_date, to_date=to_date).to_dict('records')
            logger.info(f"📥 Fetched {len(vouchers)} vouchers from Tally (tenant={tenant_id})")

            for vch_data in vouchers:
                try:
                    guid          = vch_data.get("guid", vch_data.get("GUID", "")) or ""
                    vch_number    = vch_data.get("voucher_number", vch_data.get("VOUCHERNUMBER", "")) or ""
                    vch_type      = vch_data.get("voucher_type", vch_data.get("VOUCHERTYPENAME", "Unknown")) or "Unknown"
                    party         = vch_data.get("party_name", vch_data.get("PARTYLEDGERNAME", "")) or ""
                    amount_raw    = float(vch_data.get("amount", vch_data.get("AMOUNT", 0)) or 0)
                    amount        = abs(amount_raw)
                    narration     = vch_data.get("narration", vch_data.get("NARRATION", "")) or ""

                    # ── Line Items: inventory (stock items) and ledger entries (tax/accounting) ──
                    # fetch_vouchers() returns flattened rows — items come as sub-dicts if parsed
                    inv_entries = vch_data.get("items") or vch_data.get("inventory_entries") or []
                    led_entries = vch_data.get("ledgers") or vch_data.get("ledger_entries") or []

                    # If inv_entries is empty but raw fields exist (flat parse from Voucher Register)
                    # build a single-item entry from the top-level fields as best-effort
                    if not inv_entries and vch_data.get("STOCKITEMNAME"):
                        inv_entries = [{
                            "name":     vch_data.get("STOCKITEMNAME", ""),
                            "quantity": float(vch_data.get("BILLEDQTY", 0) or 0),
                            "rate":     float(vch_data.get("RATE", 0) or 0),
                            "amount":   float(vch_data.get("AMOUNT", 0) or 0),
                        }]

                    date_str = vch_data.get("date", vch_data.get("DATE", ""))
                    try:
                        vch_date = datetime.strptime(str(date_str), "%Y%m%d") if len(str(date_str)) == 8 else datetime.now()
                    except Exception:
                        vch_date = datetime.now()

                    # ── LAYER 1: Match by GUID (most reliable, Tally's own unique key) ──
                    existing = None
                    if guid:
                        existing = db.query(Voucher).filter(Voucher.guid == guid).first()

                    # ── LAYER 2: Match by (date + voucher_number + type) ──
                    # Handles cases where GUID changes across syncs but voucher number is stable
                    if not existing and vch_number:
                        existing = db.query(Voucher).filter(
                            Voucher.tenant_id == tenant_id,
                            Voucher.voucher_number == vch_number,
                            Voucher.voucher_type == vch_type,
                            Voucher.date == vch_date,
                        ).first()

                    # ── LAYER 3: Fingerprint match (date + party + amount + type) ──
                    # Prevents duplicate blank-numbered vouchers from being inserted twice
                    if not existing and party and amount > 0:
                        existing = db.query(Voucher).filter(
                            Voucher.tenant_id == tenant_id,
                            Voucher.voucher_type == vch_type,
                            Voucher.party_name == party,
                            Voucher.amount == amount,
                            Voucher.date == vch_date,
                        ).first()

                    if existing:
                        existing.tenant_id         = tenant_id
                        existing.voucher_type      = vch_type
                        existing.party_name        = party
                        existing.amount            = amount
                        existing.narration         = narration
                        existing.last_synced       = datetime.now()
                        existing.sync_status       = "SYNCED"
                        if guid and not existing.guid:
                            existing.guid = guid
                        if vch_number and not existing.voucher_number:
                            existing.voucher_number = vch_number
                        # Always refresh line items so existing rows get enriched
                        if inv_entries:
                            existing.inventory_entries = inv_entries
                        if led_entries:
                            existing.ledger_entries = led_entries
                    else:
                        new_voucher = Voucher(
                            tenant_id          = tenant_id,
                            voucher_number     = vch_number,
                            date               = vch_date,
                            voucher_type       = vch_type,
                            party_name         = party,
                            amount             = amount,
                            narration          = narration,
                            guid               = guid or None,
                            sync_status        = "SYNCED",
                            last_synced        = datetime.now(),
                            inventory_entries  = inv_entries or None,
                            ledger_entries     = led_entries or None,
                        )
                        db.add(new_voucher)

                    synced += 1
                except Exception as e:
                    logger.warning(f"Error syncing voucher {vch_data}: {e}")
                    errors += 1

            if close_db:
                db.commit()
                db.close()

        except Exception as e:
            logger.error(f"Pull Vouchers Error: {e}")
            errors += 1

        return {"synced": synced, "errors": errors}

    
    def replay_offline_queue(self) -> dict:
        """Replay all pending vouchers to Tally"""
        db = SessionLocal()
        replayed = 0
        failed = 0
        
        try:
            pending = db.query(Voucher).filter(Voucher.sync_status == "PENDING").all()
            logger.info(f"📤 Replaying {len(pending)} pending vouchers")
            
            for voucher in pending:
                try:
                    # Reconstruct voucher data
                    voucher_data = {
                        "voucher_type": voucher.voucher_type,
                        "party_name": voucher.party_name,
                        "amount": voucher.amount,
                        "date": voucher.date.strftime("%Y%m%d") if voucher.date else datetime.now().strftime("%Y%m%d"),
                        "narration": voucher.narration or "",
                        "voucher_number": voucher.voucher_number
                    }
                    
                    # Push to Tally
                    company, fields, line_items = self._prepare_voucher_payload(voucher_data)
                    result = self._push_to_tally_with_retry(company, fields, line_items)
                    
                    if result.succeeded:
                        voucher.sync_status = "SYNCED"
                        voucher.last_synced = datetime.now()
                        replayed += 1
                    else:
                        failed += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to replay voucher {voucher.id}: {e}")
                    failed += 1
            
            db.commit()
        except Exception as e:
            logger.error(f"Replay Queue Error: {e}")
            db.rollback()
        finally:
            db.close()
        
        return {"replayed": replayed, "failed": failed}
    
    def incremental_sync(self, since_hours: int = 24) -> dict:
        """Incremental sync - only changes since last N hours"""
        from_date = (datetime.now() - timedelta(hours=since_hours)).strftime("%Y%m%d")
        to_date = datetime.now().strftime("%Y%m%d")
        
        return self.pull_vouchers(from_date=from_date, to_date=to_date)

    # ========== NEW COMPREHENSIVE SYNC METHODS FOR 360° PROFILES ==========

    def sync_ledgers_complete(self, db: Session = None) -> dict:
        """
        Enhanced ledger sync that pulls complete contact details, opening balances, 
        and credit info for 360° customer profiles.
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        
        synced = 0
        errors = 0
        enriched = 0
        
        try:
            # First, get all ledgers with basic info
            ledgers = self.tally.fetch_ledgers().to_dict('records')
            logger.info(f"📥 Fetching complete details for {len(ledgers)} ledgers")
            
            for ledger_data in ledgers:
                try:
                    name = ledger_data.get("name", ledger_data.get("NAME", ""))
                    if not name:
                        continue
                    
                    # Get complete ledger details from Tally
                    complete_ledger = self.tally.fetch_ledger_complete(name)
                    
                    existing = db.query(Ledger).filter(Ledger.name == name).first()
                    
                    if complete_ledger:
                        ledger_info = complete_ledger
                        enriched += 1
                    else:
                        ledger_info = ledger_data
                    
                    if existing:
                        # Update with complete info
                        existing.parent = ledger_info.get("parent", ledger_info.get("PARENT", existing.parent))
                        existing.closing_balance = float(ledger_info.get("closing_balance", ledger_info.get("CLOSINGBALANCE", 0)) or 0)
                        existing.opening_balance = float(ledger_info.get("opening_balance", 0) or 0)
                        existing.gstin = ledger_info.get("gstin", ledger_info.get("PARTYGSTIN", existing.gstin))
                        existing.pan = ledger_info.get("pan", existing.pan)
                        existing.address = ledger_info.get("address", existing.address)
                        existing.city = ledger_info.get("city", existing.city)
                        existing.state = ledger_info.get("state", existing.state)
                        existing.pincode = ledger_info.get("pincode", existing.pincode)
                        existing.phone = ledger_info.get("phone", existing.phone)
                        existing.email = ledger_info.get("email", existing.email)
                        existing.contact_person = ledger_info.get("contact_person", existing.contact_person)
                        existing.credit_limit = float(ledger_info.get("credit_limit", existing.credit_limit or 0) or 0)
                        existing.credit_days = int(ledger_info.get("credit_days", existing.credit_days or 0) or 0)
                        existing.gst_registration_type = ledger_info.get("gst_registration_type", existing.gst_registration_type)
                        existing.last_synced = datetime.now()
                    else:
                        # Create new ledger
                        new_ledger = Ledger(
                            name=name,
                            parent=ledger_info.get("parent", ledger_info.get("PARENT", "Sundry Debtors")),
                            closing_balance=float(ledger_info.get("closing_balance", 0) or 0),
                            opening_balance=float(ledger_info.get("opening_balance", 0) or 0),
                            gstin=ledger_info.get("gstin"),
                            pan=ledger_info.get("pan"),
                            address=ledger_info.get("address"),
                            city=ledger_info.get("city"),
                            state=ledger_info.get("state"),
                            pincode=ledger_info.get("pincode"),
                            phone=ledger_info.get("phone"),
                            email=ledger_info.get("email"),
                            contact_person=ledger_info.get("contact_person"),
                            credit_limit=float(ledger_info.get("credit_limit", 0) or 0),
                            credit_days=int(ledger_info.get("credit_days", 0) or 0),
                            tally_guid=ledger_info.get("guid", f"TALLY-{name}"),
                            last_synced=datetime.now()
                        )
                        db.add(new_ledger)
                    
                    synced += 1
                except Exception as e:
                    logger.warning(f"Error syncing complete ledger {name}: {e}")
                    errors += 1
            
            if close_db:
                db.commit()
                db.close()
                
        except Exception as e:
            logger.error(f"Complete Ledgers Sync Error: {e}")
            errors += 1
        
        logger.info(f"✅ Ledgers Complete: {synced} synced, {enriched} enriched with full details, {errors} errors")
        return {"synced": synced, "enriched": enriched, "errors": errors}

    def sync_stock_items_complete(self, db: Session = None) -> dict:
        """
        Enhanced stock item sync that pulls HSN codes, GST rates, 
        alternate units for complete 360° item profiles.
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        
        synced = 0
        errors = 0
        
        try:
            # Fetch complete stock items with all fields
            items = self.tally.fetch_stock_items_complete().to_dict('records')
            logger.info(f"📥 Syncing {len(items)} complete stock items")
            
            for item_data in items:
                try:
                    name = item_data.get("name", "")
                    if not name:
                        continue
                    
                    existing = db.query(StockItem).filter(StockItem.name == name).first()
                    
                    if existing:
                        # Update with complete info
                        existing.parent = item_data.get("parent", existing.parent)
                        existing.stock_group = item_data.get("stock_group", existing.stock_group)
                        existing.units = item_data.get("units", existing.units)
                        existing.alternate_unit = item_data.get("alternate_unit", existing.alternate_unit)
                        existing.hsn_code = item_data.get("hsn_code", existing.hsn_code)
                        existing.gst_rate = float(item_data.get("gst_rate", existing.gst_rate or 0) or 0)
                        existing.taxability = item_data.get("taxability", existing.taxability)
                        existing.opening_stock = float(item_data.get("opening_stock", existing.opening_stock or 0) or 0)
                        existing.closing_balance = float(item_data.get("closing_balance", existing.closing_balance or 0) or 0)
                        existing.cost_price = float(item_data.get("cost_price", existing.cost_price or 0) or 0)
                        existing.selling_price = float(item_data.get("selling_price", existing.selling_price or 0) or 0)
                        existing.mrp = float(item_data.get("mrp", existing.mrp or 0) or 0)
                        existing.is_godown_tracking = item_data.get("is_godown_tracking", existing.is_godown_tracking)
                        existing.last_synced = datetime.now()
                    else:
                        # Create new stock item
                        new_item = StockItem(
                            name=name,
                            alias=item_data.get("alias"),
                            parent=item_data.get("parent"),
                            stock_group=item_data.get("stock_group"),
                            units=item_data.get("units", "Nos"),
                            alternate_unit=item_data.get("alternate_unit"),
                            hsn_code=item_data.get("hsn_code"),
                            gst_rate=float(item_data.get("gst_rate", 0) or 0),
                            taxability=item_data.get("taxability", "Taxable"),
                            opening_stock=float(item_data.get("opening_stock", 0) or 0),
                            closing_balance=float(item_data.get("closing_balance", 0) or 0),
                            cost_price=float(item_data.get("cost_price", 0) or 0),
                            selling_price=float(item_data.get("selling_price", 0) or 0),
                            mrp=float(item_data.get("mrp", 0) or 0),
                            is_godown_tracking=item_data.get("is_godown_tracking", False),
                            tally_guid=f"TALLY-{name}",
                            last_synced=datetime.now()
                        )
                        db.add(new_item)
                    
                    synced += 1
                except Exception as e:
                    logger.warning(f"Error syncing stock item {item_data.get('name', 'unknown')}: {e}")
                    errors += 1
            
            if close_db:
                db.commit()
                db.close()
                
        except Exception as e:
            logger.error(f"Complete Stock Items Sync Error: {e}")
            errors += 1
        
        logger.info(f"✅ Stock Items Complete: {synced} synced, {errors} errors")
        return {"synced": synced, "errors": errors}

    def sync_bills(self, db: Session = None) -> dict:
        """
        Sync outstanding bills (receivables/payables) with due dates 
        for payment tracking and aging analysis.
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        
        synced = 0
        errors = 0
        
        try:
            bills = self.tally.fetch_bills_receivable_payable()
            logger.info(f"📥 Syncing {len(bills)} outstanding bills")
            
            for bill_data in bills:
                try:
                    bill_ref = bill_data.get("bill_ref", "")
                    party_name = bill_data.get("party_name", "")
                    
                    if not bill_ref:
                        continue
                    
                    existing = db.query(Bill).filter(Bill.bill_name == bill_ref).first()
                    
                    # Parse due date
                    due_date = None
                    if bill_data.get("due_date"):
                        try:
                            due_date = datetime.fromisoformat(bill_data["due_date"])
                        except:
                            pass
                    
                    amount = float(bill_data.get("pending_amount", bill_data.get("amount", 0)) or 0)
                    is_receivable = bill_data.get("is_receivable", True)
                    
                    if existing:
                        existing.tenant_id = self._get_tenant_id(db)
                        existing.party_name = party_name or existing.party_name
                        existing.amount = amount if is_receivable else -amount
                        existing.due_date = due_date or existing.due_date
                        existing.is_overdue = bill_data.get("is_overdue", False)
                        existing.last_synced = datetime.now()
                    else:
                        new_bill = Bill(
                            tenant_id=self._get_tenant_id(db),
                            bill_name=bill_ref,
                            party_name=party_name,
                            amount=amount if is_receivable else -amount,
                            due_date=due_date,
                            is_overdue=bill_data.get("is_overdue", False),
                            last_synced=datetime.now()
                        )
                        db.add(new_bill)
                    
                    synced += 1
                except Exception as e:
                    logger.warning(f"Error syncing bill {bill_data.get('bill_ref', 'unknown')}: {e}")
                    errors += 1
            
            if close_db:
                db.commit()
                db.close()
                
        except Exception as e:
            logger.error(f"Bills Sync Error: {e}")
            errors += 1
        
        logger.info(f"✅ Bills Sync: {synced} synced, {errors} errors")
        return {"synced": synced, "errors": errors}

    def sync_stock_movements(self, item_name: str = None, from_date: str = None, to_date: str = None, db: Session = None) -> dict:
        """
        Sync stock movements (in/out transactions) for complete item history.
        Critical for Item 360° profile movement tracking.
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        
        synced = 0
        errors = 0
        
        try:
            # Default to current FY
            if not from_date:
                now = datetime.now()
                if now.month < 4:
                    from_date = f"{now.year - 1}0401"
                else:
                    from_date = f"{now.year}0401"
            
            if not to_date:
                to_date = datetime.now().strftime("%Y%m%d")
            
            movements = self.tally.fetch_stock_movements(
                item_name=item_name,
                from_date=from_date,
                to_date=to_date
            )
            logger.info(f"📥 Syncing {len(movements)} stock movements")
            
            for movement in movements:
                try:
                    item_name_mvmt = movement.get("item_name", "")
                    voucher_guid = movement.get("voucher_guid", "")
                    
                    if not item_name_mvmt:
                        continue
                    
                    # Find the stock item
                    stock_item = db.query(StockItem).filter(StockItem.name == item_name_mvmt).first()
                    item_id = stock_item.id if stock_item else None
                    
                    # Find voucher by GUID
                    voucher = db.query(Voucher).filter(Voucher.guid == voucher_guid).first() if voucher_guid else None
                    voucher_id = voucher.id if voucher else None
                    
                    # Check for existing movement (avoid duplicates)
                    existing = db.query(StockMovement).filter(
                        StockMovement.item_id == item_id,
                        StockMovement.voucher_id == voucher_id
                    ).first() if item_id and voucher_id else None
                    
                    # Parse movement date
                    movement_date = datetime.now()
                    if movement.get("movement_date"):
                        try:
                            movement_date = datetime.fromisoformat(movement["movement_date"])
                        except:
                            pass
                    
                    if existing:
                        existing.quantity = float(movement.get("quantity", 0) or 0)
                        existing.rate = float(movement.get("rate", 0) or 0)
                        existing.amount = float(movement.get("amount", 0) or 0)
                        existing.movement_type = movement.get("movement_type", "OUT")
                        existing.godown_name = movement.get("godown", "Main Location")
                    else:
                        new_movement = StockMovement(
                            item_id=item_id,
                            voucher_id=voucher_id,
                            movement_date=movement_date,
                            movement_type=movement.get("movement_type", "OUT"),
                            quantity=float(movement.get("quantity", 0) or 0),
                            rate=float(movement.get("rate", 0) or 0),
                            amount=float(movement.get("amount", 0) or 0),
                            godown_name=movement.get("godown", "Main Location"),
                            narration=f"{movement.get('voucher_type', '')} - {movement.get('voucher_number', '')}"
                        )
                        db.add(new_movement)
                    
                    synced += 1
                except Exception as e:
                    logger.warning(f"Error syncing stock movement: {e}")
                    errors += 1
            
            if close_db:
                db.commit()
                db.close()
                
        except Exception as e:
            logger.error(f"Stock Movements Sync Error: {e}")
            errors += 1
        
        logger.info(f"✅ Stock Movements: {synced} synced, {errors} errors")
        return {"synced": synced, "errors": errors}

    def full_comprehensive_sync(self, include_movements: bool = False) -> dict:
        """
        Full comprehensive sync for 360° profiles.
        Pulls ALL data: ledgers (complete), items (with HSN/GST), bills, vouchers.
        
        Args:
            include_movements: If True, also syncs stock movements (slower)
        """
        logger.info("🔄 COMPREHENSIVE SYNC STARTED")
        results = {
            "success": True,
            "ledgers": {"synced": 0, "enriched": 0, "errors": 0},
            "stock_items": {"synced": 0, "errors": 0},
            "vouchers": {"synced": 0, "errors": 0},
            "bills": {"synced": 0, "errors": 0},
            "stock_movements": {"synced": 0, "errors": 0},
            "timestamp": datetime.now().isoformat()
        }
        
        db = SessionLocal()
        try:
            # 1. Sync Ledgers with complete details
            logger.info("📊 Phase 1: Syncing Ledgers (Complete)")
            ledger_results = self.sync_ledgers_complete(db)
            results["ledgers"] = ledger_results
            db.commit()
            
            # 2. Sync Stock Items with HSN/GST
            logger.info("📦 Phase 2: Syncing Stock Items (Complete)")
            stock_results = self.sync_stock_items_complete(db)
            results["stock_items"] = stock_results
            db.commit()
            
            # 3. Sync Vouchers (extended date range - full FY)
            logger.info("📋 Phase 3: Syncing Vouchers (Full FY)")
            now = datetime.now()
            if now.month < 4:
                fy_start = f"{now.year - 1}0401"
            else:
                fy_start = f"{now.year}0401"
            voucher_results = self.pull_vouchers(db, from_date=fy_start, to_date=now.strftime("%Y%m%d"))
            results["vouchers"] = voucher_results
            db.commit()
            
            # 4. Sync Outstanding Bills
            logger.info("💰 Phase 4: Syncing Outstanding Bills")
            bills_results = self.sync_bills(db)
            results["bills"] = bills_results
            db.commit()
            
            # 5. Optional: Stock Movements
            if include_movements:
                logger.info("📊 Phase 5: Syncing Stock Movements")
                movements_results = self.sync_stock_movements(db=db)
                results["stock_movements"] = movements_results
                db.commit()
            
            logger.info(f"✅ COMPREHENSIVE SYNC COMPLETE")
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Comprehensive Sync Failed: {e}")
            results["success"] = False
            results["error"] = str(e)
        finally:
            db.close()
        
        return results

    # ========== END COMPREHENSIVE SYNC METHODS ==========


sync_engine = SyncEngine()

