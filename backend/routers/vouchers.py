from fastapi import APIRouter, Depends, HTTPException, Body, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import os
import logging

from backend.database import get_db, Voucher, Ledger
from backend.tally_connector import TallyConnector
from backend.compliance.audit_service import AuditService
from backend.compliance.gst_engine import GSTEngine
from backend.dependencies import get_api_key
from backend.auth import get_current_tenant_id
from backend.sync_engine import sync_engine
from backend.tally_engine import TallyEngine
from backend.services.ledger_service import LedgerService, get_or_create_ledger

# Initialize Router (No prefix to allow flexible paths like /ledgers/.../vouchers)
router = APIRouter(tags=["vouchers"])
logger = logging.getLogger("vouchers")

# ⚠️  Do NOT hardcode company name here.
# TALLY_COMPANY is set dynamically by api.py at startup from k24_config.json.
# Reading it lazily (per-request via os.getenv) ensures every user gets
# their own company — not "Krishasales" or any other hardcoded default.
TALLY_URL = os.getenv("TALLY_URL", "http://localhost:9000")
TALLY_TIMEOUT = int(os.getenv("TALLY_TIMEOUT", "60"))

def _get_tally_connector() -> TallyConnector:
    """Returns a TallyConnector using the CURRENT company name from config.
    Called per-request so it always reflects k24_config.json loaded at startup.
    """
    company = os.getenv("TALLY_COMPANY", "")  # No hardcoded fallback
    url = os.getenv("TALLY_URL", "http://localhost:9000")
    return TallyConnector(url=url, company_name=company)

# Single engine instance is OK (URL-only, stateless)
engine = TallyEngine(tally_url=TALLY_URL)

# --- Pydantic Models ---

class ReceiptVoucherRequest(BaseModel):
    party_name: str
    amount: float
    deposit_to: str = "Cash"
    narration: str = ""
    date: str  # YYYY-MM-DD
    reason: Optional[str] = "New Entry"

class SalesInvoiceItem(BaseModel):
    description: str
    quantity: float
    rate: float
    amount: float

class SalesInvoiceRequest(BaseModel):
    party_name: str
    invoice_number: str = ""
    date: str  # YYYY-MM-DD
    items: list[SalesInvoiceItem]
    subtotal: float
    discount_percent: float = 0
    discount_amount: float = 0
    gst_rate: float = 0
    gst_amount: float = 0
    grand_total: float
    narration: str = ""

class PaymentVoucherRequest(BaseModel):
    party_name: str
    amount: float
    bank_cash_ledger: str = "Cash"
    narration: str = ""
    date: str = datetime.now().strftime("%Y-%m-%d")
    gst_rate: Optional[float] = 0.0
    gst_is_expense: bool = False

class VoucherDraft(BaseModel):
    voucher_type: str
    party_name: str
    amount: float
    date: Optional[str] = None
    narration: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = []

# --- Endpoints ---

from datetime import date, timedelta
from backend.tally_reader import TallyReader
from backend.routers.data_utils import normalize_tally_voucher
import time

# --- In-memory Tally Voucher Cache ---
# Caches the full normalized+sorted voucher list per (start_date, end_date) key.
# Entries expire after CACHE_TTL seconds to balance freshness vs. performance.
CALLY_CACHE_TTL = 60   # seconds
_voucher_cache: dict = {}  # key -> {"data": [...], "ledger_map": {...}, "ts": float}

@router.get("/vouchers/detail", dependencies=[Depends(get_api_key)])
async def get_voucher_detail(
    voucher_number: str,
    voucher_type: Optional[str] = None,
    guid: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    🔍 Fetch full voucher detail including line items (inventory entries)
    from Tally. Used for transaction drill-down in the 360° profile.

    Returns:
        - voucher header (date, type, party, narration)
        - items[] with name, quantity, rate, amount
        - ledgers[] (accounting entries)
        - tax_breakdown[]
        - total_amount
    """
    try:
        # ── Step 1: Look up voucher in local DB ──────────────────────────────
        db_query = db.query(Voucher).filter(Voucher.voucher_number == voucher_number)
        if voucher_type:
            db_query = db_query.filter(Voucher.voucher_type == voucher_type)
        db_voucher = db_query.first()

        if not db_voucher:
            raise HTTPException(status_code=404, detail=f"Voucher '{voucher_number}' not found")

        logger.info(
            f"Voucher detail: #{voucher_number} type={db_voucher.voucher_type} "
            f"inv_items={len(db_voucher.inventory_entries or [])} "
            f"led_entries={len(db_voucher.ledger_entries or [])}"
        )

        # ── Step 2: Build response from DB (preferred — fast, offline-safe) ──
        inv_entries = db_voucher.inventory_entries or []
        led_entries = db_voucher.ledger_entries or []
        tax_breakdown = [l for l in led_entries if l.get("is_tax")]

        # ── Step 3: If DB has no line items, try Tally live as fallback ──────
        source = "local_db"
        if not inv_entries and not led_entries:
            logger.info(f"No line items in DB for #{voucher_number} — trying Tally live fallback")
            try:
                voucher_date_str = db_voucher.date.strftime("%Y%m%d") if db_voucher.date else None
                effective_guid = guid or db_voucher.guid
                tally_detail = _get_tally_connector().fetch_voucher_with_line_items(
                    voucher_number=voucher_number,
                    voucher_type=voucher_type,
                    guid=effective_guid,
                    voucher_date=voucher_date_str,
                )
                if tally_detail:
                    inv_entries = tally_detail.get("items", [])
                    led_entries = tally_detail.get("ledger_entries", [])
                    tax_breakdown = tally_detail.get("tax_breakdown", [])
                    source = "tally"
            except Exception as te:
                logger.warning(f"Tally live fallback failed for #{voucher_number}: {te}")

        return {
            "voucher_number": db_voucher.voucher_number,
            "date": db_voucher.date.strftime("%Y-%m-%d") if db_voucher.date else "",
            "voucher_type": db_voucher.voucher_type,
            "party_name": db_voucher.party_name,
            "narration": db_voucher.narration or "",
            "guid": db_voucher.guid or "",
            "items": inv_entries,
            "ledger_entries": led_entries,
            "tax_breakdown": tax_breakdown,
            "total_amount": db_voucher.amount,
            "source": source,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to fetch voucher detail for {voucher_number}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vouchers", dependencies=[Depends(get_api_key)])
async def get_vouchers(
    voucher_type: Optional[str] = None, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    search_query: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Fetch vouchers directly from Tally (Live Daybook) with Pagination.
    
    Daybook reads live data from Tally — not tenant-scoped from DB.
    Auth is optional: if a valid JWT exists, we use its tenant_id; 
    otherwise we fall back gracefully to 'default' (dev / local mode).
    """
    # Graceful tenant resolution — pull from env if not in a JWT session
    tenant_id = os.getenv("TENANT_ID", "default")
    try:
        from fastapi.security import OAuth2PasswordBearer
        from backend.auth import get_current_tenant_id as _get_tid, get_current_user
        from backend.database import get_db as _get_db
        if request:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                from backend.auth import SECRET_KEY, ALGORITHM
                from jose import jwt as _jwt, JWTError
                payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                username = payload.get("sub")
                if username:
                    from backend.database import User
                    user = db.query(User).filter(User.username == username).first()
                    if user and user.tenant_id:
                        tenant_id = user.tenant_id
    except Exception:
        pass 
    try:
        # 1. Normalize dates
        today = date.today()
        if not start_date:
            start_date = today.strftime("%Y%m%d")
        if not end_date:
            end_date = today.strftime("%Y%m%d")
            
        logger.info(f"📊 Fetching vouchers for range: {start_date} to {end_date} (Tenant: {tenant_id})")

        # ── Step 1: Check Local DB first (Very Fast) ────────────────────────
        # ⚙️  FIX: d_end must be END-of-day (23:59:59) so the full end date is included.
        # Without this, a query for "today" would miss all of today's entries because
        # strptime gives midnight (00:00:00), and datetime comparisons are exclusive.
        d_start = datetime.strptime(start_date, "%Y%m%d")
        d_end   = datetime.strptime(end_date, "%Y%m%d").replace(hour=23, minute=59, second=59)
        
        db_query = db.query(Voucher).filter(
            Voucher.tenant_id == tenant_id,
            Voucher.date >= d_start,
            Voucher.date <= d_end
        )

        # Apply voucher type filter at DB level
        if voucher_type and voucher_type.lower() != "all_types":
            db_query = db_query.filter(Voucher.voucher_type.ilike(f"%{voucher_type}%"))

        db_vouchers = db_query.order_by(Voucher.date.desc()).all()
        
        local_data = []
        for v in db_vouchers:
            local_data.append({
                "voucher_number": v.voucher_number,
                "date": v.date.strftime("%Y%m%d") if v.date else "",
                "voucher_type": v.voucher_type,
                "party_name": v.party_name,
                "amount": v.amount,
                "narration": v.narration,
                "guid": v.guid,
                "source": "database"
            })
            
        # ── Step 2: DB-first, Tally as fallback ────────────────────────────
        # Return DB data immediately to avoid Tally timeouts.
        # Only hit Tally if DB is completely empty for this range.
        if local_data:
            logger.info(f"✅ Returning {len(local_data)} vouchers from local DB (range: {start_date}→{end_date})")
            normalized_vouchers = local_data
        else:
            # Fallback to Tally for live/filtered data
            logger.info("📡 DB empty for this range — falling back to live Tally fetch")
            try:
                reader = TallyReader()
                raw_txns = reader.get_transactions(start_date, end_date)
                
                all_ledgers = db.query(Ledger.name, Ledger.id).all()
                ledger_map = {l.name.lower(): l.id for l in all_ledgers}
                
                normalized_vouchers = []
                for txn in raw_txns:
                    norm_v = normalize_tally_voucher(txn)
                    p_name = norm_v.get("party_name", "").lower()
                    if p_name in ledger_map:
                        norm_v["ledger_id"] = ledger_map[p_name]
                    norm_v["source"] = "tally_live"
                    normalized_vouchers.append(norm_v)
            except Exception as te:
                logger.warning(f"Tally fallback failed: {te}")
                normalized_vouchers = []

        # 3. Mandatory date-range filter (applies to ALL sources — DB and Tally)
        # ⚙️  ROOT CAUSE FIX: Tally returns ALL historical vouchers; we must filter
        # explicitly here so only the requested date range reaches the frontend.
        normalized_vouchers = [
            v for v in normalized_vouchers
            if start_date <= (v.get("date") or "") <= end_date
        ]

        # 4. Apply search filter
        if search_query:
            q = search_query.lower()
            normalized_vouchers = [
                v for v in normalized_vouchers 
                if q in str(v.get("party_name", "")).lower() or 
                   q in str(v.get("voucher_number", "")).lower() or
                   q in str(v.get("narration", "")).lower()
            ]
            
        normalized_vouchers.sort(key=lambda x: x["date"], reverse=True)
        
        # 4. Pagination
        total_count = len(normalized_vouchers)
        start_index = (page - 1) * limit
        end_index = start_index + limit
        paginated = normalized_vouchers[start_index:end_index]
        
        return {
            "vouchers": paginated,
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit,
            "tenant_id": tenant_id
        }
        
    except Exception as e:
        logger.exception("Failed to fetch vouchers from Tally")
        return {
            "vouchers": [],
            "total_count": 0, 
            "page": page,
            "limit": limit,
            "total_pages": 0
        }

@router.get("/ledgers/{ledger_name}/vouchers", dependencies=[Depends(get_api_key)])
async def get_ledger_vouchers(ledger_name: str):
    """Fetch vouchers for a specific ledger"""
    try:
        # Utilize tally_connector for reading logic
        df = tally_connector.fetch_ledger_vouchers(ledger_name)
        if df.empty:
            return {"vouchers": []}
        return {"vouchers": df.to_dict(orient="records")}
    except Exception as e:
        logger.exception(f"Failed to fetch vouchers for {ledger_name}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vouchers", dependencies=[Depends(get_api_key)])
async def create_voucher_endpoint(voucher: VoucherDraft, db: Session = Depends(get_db)):
    """
    Create a voucher in Tally via the Sync Engine (Transactional).
    Includes GST Tax Calculation and AUTO-LEDGER creation.
    """
    try:
        # 1. Construct voucher data
        voucher_data = voucher.dict()
        if not voucher_data.get('date'):
            voucher_data['date'] = datetime.now().strftime("%Y%m%d")

        # 🆕 AUTO-CREATE LEDGER (Tally-like behavior)
        # Creates party ledger if it doesn't exist, uses smart group inference
        party_ledger_id = get_or_create_ledger(
            db=db,
            ledger_name=voucher.party_name,
            voucher_type=voucher.voucher_type  # Context for smart group inference
        )
        logger.info(f"📒 Party Ledger: '{voucher.party_name}' -> ID: {party_ledger_id}")
        
        # Fetch the ledger to get GSTIN for tax calculation
        party_ledger = db.query(Ledger).filter(Ledger.id == party_ledger_id).first() if party_ledger_id else None
        party_gstin = party_ledger.gstin if party_ledger else None
        
        # Company GSTIN (Env or Default)
        company_gstin = os.getenv("COMPANY_GSTIN", "27ABCDE1234F1Z5") # Default to Maharashtra
        
        if party_gstin and company_gstin:
            tax_info = GSTEngine.calculate_tax(voucher.amount, party_gstin, company_gstin)
            
            # Append Tax Info to Narration
            tax_str = f" [Tax: {tax_info['type']} ₹{tax_info['total_tax']} (IGST: {tax_info['igst']}, CGST: {tax_info['cgst']}, SGST: {tax_info['sgst']})]"
            if voucher_data.get('narration'):
                voucher_data['narration'] += tax_str
            else:
                voucher_data['narration'] = tax_str.strip()
                
            # Add tax info to response data (for frontend/debug)
            voucher_data['tax_info'] = tax_info

        # 3. Use Unified Tally Engine
        result = engine.process_voucher(voucher_data)
        tally_success = result.get("status") == "success"

        if not tally_success:
             # STRICT MODE: Fail if Tally fails
             error_msg = result.get('message', 'Failed to create voucher in Tally')
             raise HTTPException(status_code=400, detail=error_msg)

        # 4. Save to Database with linked ledger
        voucher_record = Voucher(
            guid=f"K24-{datetime.now().timestamp()}",
            voucher_number=voucher_data.get("voucher_number") or f"GEN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            date=datetime.strptime(str(voucher_data['date']), "%Y%m%d"), # Assuming date was normalized to YYYYMMDD
            voucher_type=voucher_data.get("voucher_type", "Journal"),
            party_name=voucher_data.get("party_name", "Unknown"),
            amount=voucher_data.get("amount", 0.0),
            narration=voucher_data.get("narration", ""),
            sync_status="SYNCED",
            ledger_id=party_ledger_id  # 🆕 Link to ledger
        )
        db.add(voucher_record)
        db.commit()
        
        return {
            "status": "success", 
            "message": result.get('message', 'Voucher Created'), 
            "tally_response": result,
            "tax_info": voucher_data.get('tax_info'),
            "db_id": voucher_record.id
        }

    except Exception as e:
        logger.error(f"Failed to create voucher: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vouchers/{voucher_id}/undo", dependencies=[Depends(get_api_key)])
async def undo_voucher_endpoint(voucher_id: int):
    """
    Undo a voucher (Delete from Tally & Local DB).
    """
    result = sync_engine.undo_voucher_safe(voucher_id)
    if result["success"]:
        return {"status": "success", "message": result["message"]}
    else:
        return JSONResponse(status_code=400, content={"status": "error", "message": result["error"]})

# --- Migrated Custom Endpoints ---

@router.post("/vouchers/receipt", dependencies=[Depends(get_api_key)])
async def create_receipt_voucher(request: ReceiptVoucherRequest, db: Session = Depends(get_db)):
    """Create a Receipt voucher and push to Tally + Save to Database"""
    try:
        # Convert date format YYYY-MM-DD to YYYYMMDD
        date_obj = datetime.strptime(request.date, "%Y-%m-%d")
        tally_date = date_obj.strftime("%Y%m%d")
        
        # 🆕 AUTO-CREATE LEDGER (Tally-like behavior)
        # Creates party ledger if it doesn't exist, or reuses existing one
        party_ledger_id = get_or_create_ledger(
            db=db,
            ledger_name=request.party_name,
            voucher_type="Receipt",  # Context for smart group inference
            under_group="Sundry Debtors"  # Receipts are from customers
        )
        logger.info(f"📒 Party Ledger: '{request.party_name}' -> ID: {party_ledger_id}")
        
        # 🛡️ IDEMPOTENCY: Prevent double-tap duplicate push
        from datetime import timedelta
        sixty_secs_ago = datetime.utcnow() - timedelta(seconds=60)
        existing = db.query(Voucher).filter(
            Voucher.voucher_type == "Receipt",
            Voucher.party_name == request.party_name,
            Voucher.amount == request.amount,
            Voucher.date == date_obj,
            Voucher.sync_status == "SYNCED"
        ).filter(Voucher.id > 0).order_by(Voucher.id.desc()).first()
        if existing:
            logger.warning(f"⚠️ Duplicate receipt detected for {request.party_name} ₹{request.amount} — returning existing #{existing.voucher_number}")
            return {
                "status": "success",
                "message": f"Receipt already exists (duplicate prevented)",
                "voucher": {"party_name": existing.party_name, "amount": existing.amount},
                "db_id": existing.id
            }

        # Prepare voucher data for Tally
        voucher_data = {
            "voucher_type": "Receipt",
            "date": tally_date,
            "party_name": request.party_name,
            "amount": request.amount,
            "narration": request.narration or f"Receipt from {request.party_name}",
            "deposit_to": request.deposit_to
        }
        
        # Push to Tally via Unified Engine
        result = engine.process_voucher(voucher_data)
        tally_success = result.get("status") == "success"
        
        if not tally_success:
             # STRICT MODE
             error_msg = result.get('message', 'Failed to create receipt in Tally')
             raise HTTPException(status_code=400, detail=error_msg)
        
        # Save to Database (Metadata) with linked ledger
        voucher_record = Voucher(
            guid=f"K24-{datetime.now().timestamp()}",  # Generate temp GUID
            voucher_number=f"RCP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            date=date_obj,
            voucher_type="Receipt",
            party_name=request.party_name,
            amount=request.amount,
            narration=request.narration or f"Receipt from {request.party_name}",
            sync_status="SYNCED",
            ledger_id=party_ledger_id  # 🆕 Link to ledger
        )
        db.add(voucher_record)
        db.commit()
        db.refresh(voucher_record)
        
        # 🛡️ AUDIT LOGGING (MCA Compliance)
        try:
            AuditService.log_change(
                db=db,
                entity_type="Voucher",
                entity_id=voucher_record.voucher_number,
                action="CREATE",
                user_id="kiran",  # TODO: Get from auth context
                old_data=None,
                new_data={
                    "amount": request.amount,
                    "party": request.party_name,
                    "date": request.date,
                    "xml_payload": result.get("raw_request"),
                    "tally_response": result.get("raw_response")
                },
                reason=request.reason or "New Entry"
            )
        except Exception as log_e:
            logger.error(f"Failed to audit log: {log_e}")
        
        return {
            "status": "success",
            "message": f"Receipt voucher created for ₹{request.amount}",
            "voucher": voucher_data,
            "db_id": voucher_record.id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.exception("Failed to create receipt voucher")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vouchers/sales", dependencies=[Depends(get_api_key)])
async def create_sales_invoice(request: SalesInvoiceRequest, db: Session = Depends(get_db)):
    """Create a Sales Invoice with multiple line items and push to Tally + Save to Database"""
    try:
        # Convert date format
        try:
            date_obj = datetime.strptime(request.date, "%Y-%m-%d")
            tally_date = date_obj.strftime("%Y%m%d")
        except ValueError:
             raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD")

        # 🆕 AUTO-CREATE LEDGER (Tally-like behavior)
        # Creates customer ledger if it doesn't exist, or reuses existing one
        party_ledger_id = get_or_create_ledger(
            db=db,
            ledger_name=request.party_name,
            voucher_type="Sales",  # Context: Sales = Customer = Sundry Debtors
            under_group="Sundry Debtors"
        )
        logger.info(f"📒 Customer Ledger: '{request.party_name}' -> ID: {party_ledger_id}")
        
        # 🛡️ IDEMPOTENCY: Prevent double-tap duplicate push
        from datetime import timedelta
        existing = db.query(Voucher).filter(
            Voucher.voucher_type == "Sales",
            Voucher.party_name == request.party_name,
            Voucher.amount == request.grand_total,
            Voucher.date == date_obj,
            Voucher.sync_status == "SYNCED"
        ).order_by(Voucher.id.desc()).first()
        if existing:
            logger.warning(f"⚠️ Duplicate sales invoice detected for {request.party_name} ₹{request.grand_total} — returning existing #{existing.voucher_number}")
            return {
                "status": "success",
                "message": f"Sales invoice already exists (duplicate prevented)",
                "invoice": {"party": existing.party_name, "total": existing.amount},
                "db_id": existing.id
            }

        # Prepare voucher data for Tally
        voucher_data = {
            "voucher_type": "Sales",
            "date": tally_date,
            "party_name": request.party_name,
            "amount": request.grand_total,
            "narration": request.narration or f"Sales Invoice for {request.party_name}",
            "gst_rate": request.gst_rate, # Pass GST Rate to Engine
            "items": [
                {
                    "name": item.description,
                    "quantity": item.quantity,
                    "rate": item.rate,
                    "amount": item.amount
                }
                for item in request.items
            ]
        }
        
        # Push to Tally via Unified Engine
        result = engine.process_voucher(voucher_data)
        tally_success = result.get("status") == "success"
        
        if not tally_success:
             # STRICT MODE
             error_msg = result.get('message', 'Failed to create Invoice in Tally')
             raise HTTPException(status_code=400, detail=error_msg)
        
        # Save to Database with linked ledger
        voucher_record = Voucher(
            guid=f"K24-{datetime.now().timestamp()}",
            voucher_number=request.invoice_number or f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            date=date_obj,
            voucher_type="Sales",
            party_name=request.party_name,
            amount=request.grand_total,
            narration=request.narration or f"Sales Invoice for {request.party_name}",
            sync_status="SYNCED",
            ledger_id=party_ledger_id  # 🆕 Link to ledger
        )
        db.add(voucher_record)
        db.commit()
        db.refresh(voucher_record)

        # 🛡️ AUDIT LOGGING (Fine-Tuning Gold)
        try:
            AuditService.log_change(
                db=db,
                entity_type="Voucher",
                entity_id=voucher_record.voucher_number,
                action="CREATE",
                user_id="kiran", 
                old_data=None,
                new_data={
                    "amount": request.grand_total,
                    "party": request.party_name,
                    "date": request.date,
                    "xml_payload": result.get("raw_request"),
                    "tally_response": result.get("raw_response")
                },
                reason=request.narration or "Sales Invoice"
            )
        except Exception as log_e:
            logger.error(f"Failed to audit log: {log_e}")
        
        return {
            "status": "success",
            "message": f"Sales Invoice created for ₹{request.grand_total:,.2f}",
            "invoice": {
                "party": request.party_name,
                "total": request.grand_total,
                "items_count": len(request.items),
                "gst_amount": request.gst_amount
            },
            "db_id": voucher_record.id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.exception("Failed to create sales invoice")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vouchers/payment", dependencies=[Depends(get_api_key)])
async def create_payment_voucher(request: PaymentVoucherRequest, db: Session = Depends(get_db)):
    """Create a Payment voucher and push to Tally + Save to Database"""
    try:
        # Convert date format
        date_obj = datetime.strptime(request.date, "%Y-%m-%d")
        tally_date = date_obj.strftime("%Y%m%d")
        
        # Generator Voucher Number first
        v_num = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 🆕 AUTO-CREATE LEDGER (Tally-like behavior)
        # Creates vendor ledger if it doesn't exist, or reuses existing one
        party_ledger_id = get_or_create_ledger(
            db=db,
            ledger_name=request.party_name,
            voucher_type="Payment",  # Context: Payment = Vendor = Sundry Creditors
            under_group="Sundry Creditors"
        )
        logger.info(f"📒 Vendor Ledger: '{request.party_name}' -> ID: {party_ledger_id}")

        # 🛡️ IDEMPOTENCY: Prevent double-tap duplicate push
        from datetime import timedelta
        existing = db.query(Voucher).filter(
            Voucher.voucher_type == "Payment",
            Voucher.party_name == request.party_name,
            Voucher.amount == request.amount,
            Voucher.date == date_obj,
            Voucher.sync_status == "SYNCED"
        ).order_by(Voucher.id.desc()).first()
        if existing:
            logger.warning(f"⚠️ Duplicate payment detected for {request.party_name} ₹{request.amount} — returning existing #{existing.voucher_number}")
            return {
                "status": "success",
                "message": f"Payment already exists (duplicate prevented)",
                "voucher": {"party_name": existing.party_name, "amount": existing.amount},
                "db_id": existing.id
            }

        # Prepare voucher data for Tally
        voucher_data = {
            "voucher_type": "Payment",
            "voucher_number": v_num,
            "date": tally_date,
            "party_name": request.party_name,
            "amount": request.amount,
            "narration": request.narration or f"Payment to {request.party_name}",
            "deposit_to": request.bank_cash_ledger, # In Tally logic, this is the Credit ledger (Cash/Bank)
            "gst_rate": request.gst_rate,
            "gst_is_expense": request.gst_is_expense
        }
        
        # Push to Tally via Unified Engine
        result = engine.process_voucher(voucher_data)
        tally_success = result.get("status") == "success"
        
        if not tally_success:
             # STRICT MODE
             error_msg = result.get('message', 'Failed to create Payment in Tally')
             raise HTTPException(status_code=400, detail=error_msg)
        
        # Save to Database with linked ledger
        voucher_record = Voucher(
            guid=f"K24-{datetime.now().timestamp()}",
            voucher_number=v_num,
            date=date_obj,
            voucher_type="Payment",
            party_name=request.party_name,
            amount=request.amount,
            narration=request.narration or f"Payment to {request.party_name}",
            sync_status="SYNCED",
            ledger_id=party_ledger_id  # 🆕 Link to ledger
        )
        db.add(voucher_record)
        db.commit()
        db.refresh(voucher_record)
        
        return {
            "status": "success",
            "message": f"Payment created for ₹{request.amount}",
            "voucher": voucher_data,
            "db_id": voucher_record.id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.exception("Failed to create payment voucher")
        raise HTTPException(status_code=500, detail=str(e))
