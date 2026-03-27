from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from database import get_db, Ledger, Voucher
from auth import get_current_tenant_id
from tally_connector import TallyConnector
from routers.data_utils import normalize_tally_voucher
from services.ledger_service import LedgerService

import os
import logging

router = APIRouter(tags=["ledgers"])
logger = logging.getLogger("ledgers")

TALLY_URL = os.getenv("TALLY_URL", "http://localhost:9000")
tally_connector = TallyConnector(url=TALLY_URL)


# --- Pydantic Models for Ledger Operations ---

class LedgerCreateRequest(BaseModel):
    """Request model for creating a new ledger"""
    name: str
    under_group: Optional[str] = None  # Will be auto-inferred if not provided
    ledger_type: Optional[str] = None  # customer, supplier, bank, etc.
    gstin: Optional[str] = None
    pan: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    opening_balance: Optional[float] = 0.0


class LedgerSearchResponse(BaseModel):
    """Response model for ledger search results"""
    id: int
    name: str
    group: Optional[str]
    type: Optional[str]
    balance: Optional[float]
    gstin: Optional[str]


# --- Ledger Search & Autocomplete Endpoints ---

from database import get_db, StockItem
from dependencies import get_api_key, get_tenant_id

@router.get("/ledgers/search")
async def search_ledgers_for_autocomplete(
    q: str = Query(..., min_length=1, description="Search query"),
    ledger_type: Optional[str] = Query(None, description="Filter by type: customer, supplier, etc."),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    🔍 LEDGER SEARCH FOR AUTOCOMPLETE
    
    Used by voucher forms to show existing ledger suggestions as user types.
    Returns matching ledgers with basic info for dropdown display.
    
    Tally-like behavior:
    - User types 3+ characters -> show matching suggestions
    - User can select existing OR type new name
    - New names are auto-created on voucher save
    """
    try:
        ledger_service = LedgerService(db)
        results = ledger_service.search_ledgers(
            query=q,
            tenant_id=tenant_id,
            ledger_type=ledger_type,
            limit=limit
        )
        
        return {
            "status": "success",
            "query": q,
            "count": len(results),
            "ledgers": results
        }
    except Exception as e:
        logger.exception(f"Ledger search failed for query '{q}'")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ledgers")
async def create_ledger(
    request: LedgerCreateRequest,
    db: Session = Depends(get_db),
    tenant_id: str = "default"
):
    """
    🆕 CREATE NEW LEDGER
    
    Manually create a new ledger with full details.
    Auto-syncs to Tally if connected.
    
    Note: For voucher creation, ledgers are auto-created automatically.
    This endpoint is for explicit ledger management (master data entry).
    """
    try:
        ledger_service = LedgerService(db)
        
        # Check if ledger already exists
        existing = ledger_service.get_ledger_by_name(request.name, tenant_id)
        if existing:
            return {
                "status": "exists",
                "message": f"Ledger '{request.name}' already exists",
                "ledger_id": existing.id,
                "ledger": {
                    "id": existing.id,
                    "name": existing.name,
                    "group": existing.parent,
                    "type": existing.ledger_type
                }
            }
        
        # Create new ledger
        ledger_id = ledger_service.get_or_create_ledger(
            ledger_name=request.name,
            under_group=request.under_group,
            ledger_type=request.ledger_type,
            additional_data={
                "gstin": request.gstin,
                "pan": request.pan,
                "address": request.address,
                "city": request.city,
                "state": request.state,
                "phone": request.phone,
                "email": request.email,
            },
            tenant_id=tenant_id
        )
        
        if ledger_id:
            ledger = ledger_service.get_ledger_by_id(ledger_id)
            return {
                "status": "created",
                "message": f"Ledger '{request.name}' created successfully",
                "ledger_id": ledger_id,
                "ledger": {
                    "id": ledger.id,
                    "name": ledger.name,
                    "group": ledger.parent,
                    "type": ledger.ledger_type
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create ledger")
            
    except Exception as e:
        logger.exception(f"Failed to create ledger '{request.name}'")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ledgers/list")
async def list_ledgers(
    group: Optional[str] = Query(None, description="Filter by parent group"),
    ledger_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    tenant_id: str = "default"
):
    """
    📋 LIST LEDGERS
    
    Get paginated list of all ledgers with optional filtering.
    """
    try:
        query = db.query(Ledger).filter(
            Ledger.tenant_id == tenant_id,
            Ledger.is_active == True
        )
        
        if group:
            query = query.filter(Ledger.parent.ilike(f"%{group}%"))
        
        if ledger_type:
            query = query.filter(Ledger.ledger_type == ledger_type)
        
        total = query.count()
        ledgers = query.order_by(Ledger.name).offset(offset).limit(limit).all()
        
        return {
            "status": "success",
            "total": total,
            "count": len(ledgers),
            "offset": offset,
            "ledgers": [
                {
                    "id": l.id,
                    "name": l.name,
                    "alias": l.alias,
                    "group": l.parent,
                    "type": l.ledger_type,
                    "closing_balance": l.closing_balance,
                    "gstin": l.gstin,
                    "phone": l.phone,
                    "email": l.email,
                    "created_from": l.created_from,
                    "is_complete": bool(l.gstin or l.phone or l.email)  # Badge for incomplete profiles
                }
                for l in ledgers
            ]
        }
    except Exception as e:
        logger.exception("Failed to list ledgers")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ledgers/{ledger_id}")
async def get_ledger_details(
    ledger_id: int, 
    db: Session = Depends(get_db), 
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Fetch comprehensive ledger profile from local DB.
    """
    ledger = db.query(Ledger).filter(Ledger.id == ledger_id).first()
    
    if not ledger:
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Calculate current balance from Vouchers table (if synced) or Tally?
    # Strategy: Use local DB metadata + Tally Live Balance if possible.
    # For speed, use local DB 'closing_balance' if updated, or calc from vouchers.
    
    # Let's trust local DB 'closing_balance' if it's being synced. 
    # Otherwise, calculate from vouchers matching party_name.
    
    # Calculate stats from Vouchers
    # Note: Ledger ID might not be linked in Vouchers table for all ancient data, so use name.
    
    vouchers_query = db.query(Voucher).filter(Voucher.party_name == ledger.name)
    all_txns = vouchers_query.order_by(Voucher.date.asc()).all()
    
    txn_count = len(all_txns)
    last_txn = all_txns[-1] if all_txns else None
    first_txn = all_txns[0] if all_txns else None
    
    # Financial Metrics
    total_sales = sum(v.amount for v in all_txns if v.voucher_type in ['Sales', 'Receipt'])
    total_purchases = sum(v.amount for v in all_txns if v.voucher_type in ['Purchase', 'Payment'])
    
    # Monthly Trend (Last 12 Months)
    # Simple aggregation dict: "Jan 2025": 50000
    monthly_data = {}
    for v in all_txns:
        month_key = v.date.strftime("%b %Y")
        monthly_data[month_key] = monthly_data.get(month_key, 0) + v.amount
        
    # Convert to list for chart
    monthly_trend = [{"month": k, "amount": v} for k, v in monthly_data.items()]
    # Keep last 6-12 entries if needed, or sort?
    # Python dict preserves insertion order since 3.7 (if we iterated sorted txns). 
    # But let's ensure we just take the relevant ones or format nicely on frontend.
    
    # Derive State/PAN from GSTIN
    gstin = ledger.gstin or ""
    pan = gstin[2:12] if len(gstin) >= 15 else None
    state_code = gstin[:2] if len(gstin) >= 15 else None
    # Map state code to name if needed, or just return code for now
    
    # Relationship
    customer_since = first_txn.date if first_txn else None
    
    return {
        "id": ledger.id,
        "name": ledger.name,
        "group": ledger.parent,
        "closing_balance": ledger.closing_balance,
        "email": ledger.email,
        "phone": ledger.phone,
        "gstin": ledger.gstin,
        "address": ledger.address,
        "pan": pan,
        "state_code": state_code,
        "stats": {
            "transaction_count": txn_count,
            "last_transaction_date": last_txn.date if last_txn else None
        },
        "financials": {
            "total_sales": total_sales,
            "total_purchases": total_purchases,
            "customer_since": customer_since,
            "monthly_trend": monthly_trend
        }
    }

@router.get("/ledgers/{ledger_id}/transactions")
async def get_ledger_transactions(
    ledger_id: int, 
    db: Session = Depends(get_db),
    start_date: Optional[str] = None, # YYYY-MM-DD
    end_date: Optional[str] = None,
    voucher_type: Optional[str] = None, # 'Sales', 'Purchase', etc.
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Fetch transactions with advanced filtering and period-specific opening balance.
    """
    ledger = db.query(Ledger).filter(Ledger.id == ledger_id).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="Ledger not found")
    
    # Base Query
    query = db.query(Voucher).filter(Voucher.party_name == ledger.name)
    
    # 1. Calculate Opening Balance AS OF Start Date
    # Default Opening Balance (Master)
    opening_bal = ledger.opening_balance or 0.0
    
    # If start_date provided, adjust opening_bal by summing txns BEFORE start_date
    if start_date:
        try:
            s_date = datetime.strptime(start_date, "%Y-%m-%d")
            
            # Fetch all prior transactions
            prior_txns = db.query(Voucher)\
                .filter(Voucher.party_name == ledger.name)\
                .filter(Voucher.date < s_date)\
                .all()
                
            for v in prior_txns:
                # Apply Tally Logic:
                # Sales/Payment/DebitNote -> Debit (Increase +)
                # Purchase/Receipt/CreditNote -> Credit (Decrease -)
                # Assumes Ledger is Asset/Expense (Debit Nature). 
                # If Liability/Income, signs flip. 
                # Standard Tally Export: Vouchers usually have positive amounts.
                # Convention: Debit is Positive, Credit is Negative.
                
                amt = v.amount
                v_type = (v.voucher_type or "").lower()
                
                is_debit = any(x in v_type for x in ['sales', 'payment', 'debit note', 'journal']) 
                # Journal is ambiguous, usually check specific Ledger Entry flag, but simplified here.
                
                if is_debit:
                    opening_bal += amt
                else:
                    opening_bal -= amt
                    
        except ValueError:
            pass # Ignore invalid date format
            
    # 2. Apply Filters to Main Query
    if start_date:
        query = query.filter(Voucher.date >= datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        query = query.filter(Voucher.date <= datetime.strptime(end_date, "%Y-%m-%d"))
        
    if voucher_type and voucher_type != 'all':
        query = query.filter(Voucher.voucher_type.ilike(f"%{voucher_type}%"))
        
    if min_amount is not None:
        query = query.filter(Voucher.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Voucher.amount <= max_amount)
        
    if search:
        # Search Number or Narration
        query = query.filter((Voucher.voucher_number.ilike(f"%{search}%")) | (Voucher.narration.ilike(f"%{search}%")))

    # 3. Pagination & Execution
    total_count = query.count()
    
    # Sorting: Date Ascending for Running Balance view? 
    # Usually UI wants newest first, but running balance needs oldest first to calc?
    # Actually, if we have opening_bal, we can calc running balance in UI regardless of sort 
    # IF we iterate properly. 
    # Standard: Date DESC for recent first. Run Bal is tricky with Date DESC and pagination.
    # Solution: UI usually requests Date ASC for Ledger View (Book View).
    # Let's default to Date ASC for Ledger View standard.
    
    txns = query.order_by(Voucher.date.asc()).offset(offset).limit(limit).all()
        
    return {
        "transactions": txns,
        "count": total_count,
        "opening_balance": opening_bal # Balance before the first transaction in this list (or start_date)
    }

from database import InventoryEntry, StockItem

@router.get("/ledgers/{ledger_id}/items")
async def get_ledger_items(
    ledger_id: int,
    db: Session = Depends(get_db),
    limit: int = 100,
):
    """
    Fetch Inventory Items associated with this Ledger (Sales/Purchase history).
    Aggregates by Stock Item.
    """
    ledger = db.query(Ledger).filter(Ledger.id == ledger_id).first()
    if not ledger:
        # Fallback to name match if ID not reliably linked in Vouchers
        pass
        
    if not ledger:
         raise HTTPException(status_code=404, detail="Ledger not found")

    # Linked via Vouchers: Ledger -> vouchers -> InventoryEntries -> StockItems
    # Query:
    # Select StockItem.name, Sum(InventoryEntry.billed_qty), Sum(InventoryEntry.amount), Max(Voucher.date)
    # Join Voucher, InventoryEntry, StockItem
    # Where Voucher.party_name == ledger.name
    
    results = db.query(
        StockItem.name,
        func.sum(InventoryEntry.billed_qty).label("total_qty"),
        func.sum(InventoryEntry.amount).label("total_amount"),
        func.max(Voucher.date).label("last_date"), 
        func.avg(InventoryEntry.rate).label("avg_rate"), # Simple Avg
        # To get Last Rate, we need a subquery or join-fu, simplified for now.
    )\
    .join(InventoryEntry, InventoryEntry.item_id == StockItem.id)\
    .join(Voucher, Voucher.id == InventoryEntry.voucher_id)\
    .filter(Voucher.party_name == ledger.name)\
    .group_by(StockItem.name)\
    .order_by(func.max(Voucher.date).desc())\
    .limit(limit)\
    .all()
    
    items = []
    for r in results:
        items.append({
            "item_name": r.name,
            "total_qty": r.total_qty,
            "total_amount": r.total_amount,
            "last_date": r.last_date,
            "avg_rate": r.avg_rate
        })
        
    return {"items": items, "count": len(items)}
