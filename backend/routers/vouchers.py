from fastapi import APIRouter, Depends, HTTPException, Body
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

# Initialize Tally Engine (Unified Logic)
TALLY_COMPANY = os.getenv("TALLY_COMPANY", "Krishasales")
TALLY_URL = os.getenv("TALLY_URL", "http://localhost:9000")
# Legacy Connector for some reads if needed, but Engine handles writes
tally_connector = TallyConnector(url=TALLY_URL, company_name=TALLY_COMPANY)
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

@router.get("/vouchers", dependencies=[Depends(get_api_key)])
async def get_vouchers(
    voucher_type: Optional[str] = None, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    search_query: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db), 
    tenant_id: str = Depends(get_current_tenant_id)
):
    """Fetch vouchers directly from Tally (Live Daybook) with Pagination"""
    try:
        # Default Daybook View: Today if not specified
        today = date.today()
        
        if not start_date:
            start_date = today.strftime("%Y%m%d")
        if not end_date:
            end_date = today.strftime("%Y%m%d")
        
        # --- Cache Check ---
        # Re-use the full normalized list for the same date range within TTL.
        cache_key = (start_date, end_date)
        cached = _voucher_cache.get(cache_key)
        now = time.time()
        
        if cached and (now - cached["ts"]) < CALLY_CACHE_TTL:
            # Cache HIT: use pre-fetched data
            all_normalized = cached["data"]
            ledger_map = cached["ledger_map"]
            logger.debug(f"[Cache HIT] {cache_key} — {len(all_normalized)} vouchers")
        else:
            # Cache MISS: hit Tally
            reader = TallyReader()
            raw_txns = reader.get_transactions(start_date, end_date)
            
            # Pre-fetch Ledger Map for ID linking
            all_ledgers = db.query(Ledger.name, Ledger.id).all()
            ledger_map = {l.name.lower(): l.id for l in all_ledgers}
            
            all_normalized = []
            for txn in raw_txns:
                # Strict Date Filter (Python Side)
                txn_date = txn.get("date", "")
                if start_date and txn_date < start_date:
                    continue
                if end_date and txn_date > end_date:
                    continue

                norm_v = normalize_tally_voucher(txn)
                
                # Inject Ledger ID if found in local DB
                p_name = norm_v.get("party_name", "").lower()
                if p_name in ledger_map:
                    norm_v["ledger_id"] = ledger_map[p_name]
                
                all_normalized.append(norm_v)
            
            # Sort by date desc
            all_normalized.sort(key=lambda x: x["date"], reverse=True)
            
            # Store in cache
            _voucher_cache[cache_key] = {
                "data": all_normalized,
                "ledger_map": ledger_map,
                "ts": now,
            }
            logger.info(f"[Cache MISS] Fetched {len(all_normalized)} vouchers from Tally for {cache_key}")
        
        # Apply in-memory filters (type + search) on cached data
        normalized_vouchers = []
        for norm_v in all_normalized:
            # Filter by TYPE if requested
            if voucher_type:
                if voucher_type.lower() != "all_types" and voucher_type.lower() not in norm_v["voucher_type"].lower():
                    continue

            # Filter by Search Query
            if search_query:
                q = search_query.lower()
                match = (
                    q in str(norm_v.get("party_name", "")).lower() or
                    q in str(norm_v.get("voucher_number", "")).lower() or
                    q in str(norm_v.get("amount", "")).lower() or
                    q in str(norm_v.get("narration", "")).lower()
                )
                if not match:
                    continue
            
            normalized_vouchers.append(norm_v)
        
        # Pagination Logic
        total_count = len(normalized_vouchers)
        start_index = (page - 1) * limit
        end_index = start_index + limit
        paginated_vouchers = normalized_vouchers[start_index:end_index]
        
        return {
            "vouchers": paginated_vouchers,
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit
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
