from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, date, timedelta
import os
import logging
from sqlalchemy.orm import Session
from backend.tally_reader import TallyReader
from backend.dependencies import get_api_key, get_tenant_id
from backend.database import get_db, StockItem

# Initialize Router
router = APIRouter(tags=["inventory"])
logger = logging.getLogger("inventory")

# Initialize Tally Reader
# We can read URL from env or existing config logic
TALLY_URL = os.getenv("TALLY_URL", "http://localhost:9000")
reader = TallyReader(tally_url=TALLY_URL)

# --- Pydantic Models ---

class InventoryItem(BaseModel):
    name: str # Item Name (Key)
    parent: Optional[str] = ""
    category: Optional[str] = "General" # Derived from Parent or logic
    units: str
    closing_balance: float # Quantity
    value: float # Total Value
    rate: float # Average Rate
    status: str # In Stock, Low Stock, Out of Stock
    reorder_level: float = 0.0 # From local DB or default
    last_updated: Optional[str] = None
    sku: Optional[str] = None

class InventorySummary(BaseModel):
    total_items: int
    total_value: float
    low_stock_count: int
    out_of_stock_count: int
    last_synced: str

class StockMovement(BaseModel):
    date: str
    type: str # In / Out
    quantity: float
    rate: float
    amount: float
    reference: Optional[str] = ""
    party: Optional[str] = ""

class StockMovementResponse(BaseModel):
    movements: List[StockMovement]
    total_in: float
    total_out: float
    opening_balance: float = 0.0 # Hard to calculate without full history, usually just current state
    closing_balance: float

# --- Endpoints ---

@router.get("/inventory", dependencies=[Depends(get_api_key)])
async def get_inventory_items(
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None, # in_stock, low_stock, out_of_stock
    sort_by: Optional[str] = "name", # name, value, quantity
    page: int = 1,
    limit: int = 50,
    show_zero_stock: bool = False, # New parameter to show/hide zero stock items
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Fetch all inventory items from database.
    Supports search, filtering, and pagination.
    By default, hides items with zero or negative stock.
    """
    try:
        # 1. Fetch from Database (synced by background service)
        query = db.query(StockItem).filter(StockItem.tenant_id == tenant_id)

        # 2. Enrich & Filter
        results = []

        total_value = 0.0
        low_stock_threshold = 10.0 # Placeholder, should be per-item configurable

        items = query.all()

        for item in items:
            name = item.name or "Unknown"
            qty = float(item.closing_balance or 0)
            rate = float(item.rate or item.cost_price or 0)
            val = qty * rate

            # Skip zero/negative stock items unless explicitly requested
            if not show_zero_stock and qty <= 0:
                continue

            # Determine Status
            if qty <= 0:
                s = "Out of Stock"
            elif qty < low_stock_threshold:
                s = "Low Stock"
            else:
                s = "In Stock"

            # Filter: Status
            if status:
                st = status.lower().replace("_", " ") # in_stock -> in stock
                if st not in s.lower():
                    continue

            # Filter: Search
            if search:
                q = search.lower()
                if q not in name.lower():
                    continue

            # Filter: Category (Parent)
            parent = item.parent or ""
            if category and category.lower() != "all" and category.lower() not in parent.lower():
                continue

            results.append({
                "name": name,
                "parent": parent,
                "category": parent or "General", # Map parent to category
                "units": item.units or "nos",
                "closing_balance": qty,
                "value": val,
                "rate": rate,
                "status": s,
                "reorder_level": low_stock_threshold, # TODO: Load from DB
                "last_updated": datetime.now().isoformat()
            })

            total_value += val

        # 3. Sort
        reverse = True if sort_by in ["value", "quantity"] else False
        key_map = {
            "name": lambda x: x["name"],
            "value": lambda x: x["value"],
            "quantity": lambda x: x["closing_balance"]
        }

        if sort_by in key_map:
            results.sort(key=key_map[sort_by], reverse=reverse)

        # 4. Pagination
        total_count = len(results)
        start = (page - 1) * limit
        end = start + limit
        paginated = results[start:end]

        return {
            "items": paginated,
            "total": total_count,
            "page": page,
            "limit": limit,
            "summary": {
                "total_items": total_count,
                "total_value": total_value
            }
        }

    except Exception as e:
        logger.exception("Failed to fetch inventory")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/inventory/summary", dependencies=[Depends(get_api_key)])
async def get_inventory_summary(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """Returns aggregated stats for dashboard cards (excludes zero-stock items)"""
    try:
        items = db.query(StockItem).filter(StockItem.tenant_id == tenant_id).all()

        total_value = 0.0
        low_stock_count = 0
        out_of_stock_count = 0
        active_items_count = 0

        for item in items:
            qty = float(item.closing_balance or 0)

            # Skip zero/negative stock items from counts and value
            if qty <= 0:
                out_of_stock_count += 1
                continue

            active_items_count += 1
            rate = float(item.rate or item.cost_price or 0)
            val = qty * rate
            total_value += val

            if qty < 10:
                low_stock_count += 1

        return {
            "totalItems": active_items_count,  # Only count items with stock > 0
            "totalValue": round(total_value, 2),
            "lowStockCount": low_stock_count,
            "outOfStockCount": out_of_stock_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.exception("Failed to fetch summary")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/inventory/movements/all", dependencies=[Depends(get_api_key)])
async def get_all_movements(
    page: int = 1,
    limit: int = 50,
    days: int = 30
):
    """
    Get global stock movement history across all items.
    """
    try:
        # Date Range
        end_date = datetime.now()
        start_date = end_date.replace(year=end_date.year - 1) if days > 365 else \
                     (end_date - timedelta(days=days))
        
        s_str = start_date.strftime("%Y%m%d")
        e_str = end_date.strftime("%Y%m%d")
        
        # Fetch all transactions
        all_txns = reader.get_transactions(s_str, e_str)
        
        movements = []
        
        for txn in all_txns:
            txn_items = txn.get("items", [])
            for line in txn_items:
                # Add check to ensure it's a valid stock item
                if not line.get("name"): continue
                
                qty = float(line.get("quantity", 0))
                if qty == 0: continue
                
                v_type = txn.get("type", "").lower()
                type_ = "In" if "purchase" in v_type or "receipt" in v_type else "Out"
                if "sales" in v_type: type_ = "Out"
                
                movements.append({
                    "date": txn.get("date"),
                    "type": type_,
                    "quantity": qty,
                    "rate": float(line.get("rate", 0)),
                    "amount": float(line.get("amount", 0)),
                    "reference": txn.get("voucher_number"),
                    "party": txn.get("party_name"),
                    "item_name": line.get("name") # Include item name for global view
                })
        
        # Sort desc date
        movements.sort(key=lambda x: x["date"], reverse=True)
        
        # Pagination
        total = len(movements)
        start = (page - 1) * limit
        end = start + limit
        
        return {
            "movements": movements[start:end],
            "total": total,
            "page": page
        }
        
    except Exception as e:
         logger.exception("Error fetching global movements")
         raise HTTPException(status_code=500, detail=str(e))

@router.get("/inventory/{item_name}", dependencies=[Depends(get_api_key)])
async def get_item_details(
    item_name: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get single item details including stats."""
    try:
        # Check database first for consistency with list view
        db_item = db.query(StockItem).filter(
            StockItem.tenant_id == tenant_id,
            StockItem.name == item_name
        ).first()

        if not db_item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Build response from database
        qty = float(db_item.closing_balance or 0)
        rate = float(db_item.rate or db_item.cost_price or 0)
        val = qty * rate

        # Determine Status
        if qty <= 0:
            status = "Out of Stock"
        elif qty < 10.0:  # low_stock_threshold
            status = "Low Stock"
        else:
            status = "In Stock"

        item = {
            "name": db_item.name,
            "parent": db_item.parent or "",
            "category": db_item.parent or "General",
            "units": db_item.units or "nos",
            "closing_balance": qty,
            "value": val,
            "rate": rate,
            "status": status,
            "hsn_code": db_item.hsn_code,
            "gst_rate": db_item.gst_rate or 0.0,
            "minimum_stock": db_item.minimum_stock,
            "last_updated": db_item.last_synced.isoformat() if db_item.last_synced else None
        }

        return {
            "item": item,
            "stats": {
                "turnover_rate": "High", # Placeholder logic
                "last_sold": "2 days ago" # Placeholder
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching detail for {item_name}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/inventory/{item_name}/movements", dependencies=[Depends(get_api_key)])
async def get_item_movements(
    item_name: str,
    page: int = 1,
    limit: int = 50,
    days: int = 30
):
    """
    Get stock movement history by parsing Vouchers.
    This is heavy - we scan vouchers and filter for the item.
    Ideally, use Tally 'Stock Vouchers' report, but reader.get_transactions is available.
    """
    try:
        # Date Range
        end_date = datetime.now()
        # Default 30 days history
        # Adjust 'days' logic as needed
        start_date = end_date.replace(year=end_date.year - 1) if days > 365 else \
                     (end_date - timedelta(days=days))
        
        s_str = start_date.strftime("%Y%m%d")
        e_str = end_date.strftime("%Y%m%d")
        
        # This fetches ALL transactions. 
        # For optimization, we should implement 'get_stock_vouchers' in reader later.
        all_txns = reader.get_transactions(s_str, e_str)
        
        movements = []
        
        for txn in all_txns:
            # Check items in txn
            txn_items = txn.get("items", [])
            for line in txn_items:
                if line.get("name", "").lower() == item_name.lower():
                    # Found movement
                    qty = float(line.get("quantity", 0))
                    rate = float(line.get("rate", 0))
                    amt = float(line.get("amount", 0))
                    
                    v_type = txn.get("voucher_type", "").lower()
                    
                    # Logic: Purchase = In, Macintosh = In (usually), Sales = Out
                    # Tally signs: Debit (+), Credit (-)? Or check Voucher Type?
                    # get_transactions returns absolute values usually.
                    
                    type_ = "In" if "purchase" in v_type or "receipt" in v_type else "Out"
                    if "sales" in v_type: type_ = "Out"
                    
                    movements.append({
                        "date": txn.get("date"),
                        "type": type_,
                        "quantity": qty,
                        "rate": rate,
                        "amount": amt,
                        "reference": txn.get("voucher_number"),
                        "party": txn.get("party_name")
                    })
        
        # Sort desc date
        movements.sort(key=lambda x: x["date"], reverse=True)
        
        # Pagination
        total = len(movements)
        start = (page - 1) * limit
        end = start + limit
        
        return {
            "movements": movements[start:end],
            "total": total,
            "page": page
        }
        
    except Exception as e:
         logger.exception(f"Error fetching movements for {item_name}")
         raise HTTPException(status_code=500, detail=str(e))
