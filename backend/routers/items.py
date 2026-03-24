from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Dict, List, Optional, Any
import sqlite3
import logging
from datetime import datetime
import os
import sys

from database import get_db, StockItem
from dependencies import get_api_key

router = APIRouter()
logger = logging.getLogger("items")


# ─────────────────────────────────────────────────────────────────────────────
# ITEM SEARCH  (for autocomplete in voucher creation)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/api/items/search", dependencies=[Depends(get_api_key)])
async def search_items(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    🔍 Item autocomplete search for voucher creation.

    Searches the local `items` table (synced from Tally) by name / alias.
    Returns enough info for the frontend to:
      - display the suggestion list
      - auto-fill Rate from selling_price
      - auto-fill GST rate
    """
    try:
        items = (
            db.query(StockItem)
            .filter(
                StockItem.is_active == True,
                or_(
                    StockItem.name.ilike(f"%{q}%"),
                    StockItem.alias.ilike(f"%{q}%"),
                    StockItem.part_number.ilike(f"%{q}%"),
                    StockItem.hsn_code.ilike(f"%{q}%"),
                ),
            )
            .order_by(
                # Exact-start matches first, then alphabetical
                func.lower(StockItem.name).asc()
            )
            .limit(limit)
            .all()
        )

        return {
            "query": q,
            "count": len(items),
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "alias": item.alias,
                    "unit": item.units or "Nos",
                    "selling_price": item.selling_price or 0.0,
                    "cost_price": item.cost_price or 0.0,
                    "mrp": item.mrp,
                    "gst_rate": item.gst_rate or 0.0,
                    "hsn_code": item.hsn_code,
                    "stock": item.closing_balance or 0.0,
                    "stock_group": item.stock_group or item.parent,
                }
                for item in items
            ],
        }
    except Exception as e:
        logger.error(f"Item search error: {e}")
        # Return empty gracefully — don't crash the voucher form
        return {"query": q, "count": 0, "items": []}

def get_db_path():
    """Returns safe DB path for both Dev and Frozen (Desktop) modes"""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller exe -> %APPDATA%/k24
        # Default to user home if APPDATA missing
        base_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "k24")
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, "k24_shadow.db")
    else:
        # Dev mode -> Local repo file
        return os.path.join(os.path.dirname(__file__), "..", "..", "k24_shadow.db")

DB_PATH = get_db_path()

@router.get("/api/items/{item_id}/360")
async def get_item_360(item_id: str):
    """
    Complete 360° view of an inventory item
    Aggregates: stock, movements, rates, profit, top customers
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # ========================================
        # 1. BASIC ITEM INFO
        # ========================================
        # Adapted for 'items' table schema in backend/database/__init__.py
        cursor.execute("""
            SELECT 
                id, name, part_number as sku, hsn_code, units as unit,
                opening_stock, closing_balance as current_stock, 
                cost_price as purchase_rate, selling_price as sales_rate,
                gst_rate,
                alias as tally_item_name, is_active,
                created_at, updated_at
            FROM items 
            WHERE (CAST(id AS TEXT) = ? OR name = ?)
        """, (item_id, item_id))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")
        
        item_data = dict(row)
        
        real_item_id = item_data["id"]

        # Calculate opening value if not present (assuming opening_stock * purchase_rate)
        # DB doesn't have opening_value column
        item_data["opening_value"] = item_data.get("opening_stock", 0) * item_data.get("purchase_rate", 0)

        # ========================================
        # 2. STOCK SUMMARY
        # ========================================
        # Use stock_movements table
        # Check movement_type (In/Out)
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN lower(movement_type) IN ('in', 'inward', 'purchase', 'receipt') THEN quantity ELSE 0 END) as total_inward,
                SUM(CASE WHEN lower(movement_type) IN ('out', 'outward', 'sales', 'delivery') THEN quantity ELSE 0 END) as total_outward,
                COUNT(*) as total_movements,
                MIN(movement_date) as first_movement,
                MAX(movement_date) as last_movement
            FROM stock_movements
            WHERE item_id = ?
        """, (real_item_id,))
        
        stock_summary_row = cursor.fetchone()
        stock_summary = dict(stock_summary_row) if stock_summary_row else {}
        
        # Ensure Not None
        if stock_summary.get("total_inward") is None: stock_summary["total_inward"] = 0
        if stock_summary.get("total_outward") is None: stock_summary["total_outward"] = 0
        if stock_summary.get("total_movements") is None: stock_summary["total_movements"] = 0

        # ========================================
        # 3. PURCHASE HISTORY (Last 10)
        # ========================================
        # Join vouchers on voucher_id
        cursor.execute("""
            SELECT 
                v.date, v.voucher_number,
                v.party_name as supplier,
                sm.quantity, sm.rate,
                sm.amount
            FROM stock_movements sm
            JOIN vouchers v ON sm.voucher_id = v.id
            WHERE sm.item_id = ?
            AND (lower(v.voucher_type) LIKE '%purchase%' OR lower(sm.movement_type) IN ('in', 'inward'))
            ORDER BY v.date DESC
            LIMIT 10
        """, (real_item_id,))
        
        purchase_history = [dict(r) for r in cursor.fetchall()]
        
        # ========================================
        # 4. SALES HISTORY (Last 10)
        # ========================================
        cursor.execute("""
            SELECT 
                v.date, v.voucher_number,
                v.party_name as customer,
                sm.quantity, sm.rate,
                sm.amount
            FROM stock_movements sm
            JOIN vouchers v ON sm.voucher_id = v.id
            WHERE sm.item_id = ?
            AND (lower(v.voucher_type) LIKE '%sales%' OR lower(sm.movement_type) IN ('out', 'outward'))
            ORDER BY v.date DESC
            LIMIT 10
        """, (real_item_id,))
        
        sales_history = [dict(r) for r in cursor.fetchall()]
        
        # ========================================
        # 5. TOP CUSTOMERS (By Quantity)
        # ========================================
        cursor.execute("""
            SELECT 
                v.party_name as customer_name,
                v.ledger_id as customer_id,
                SUM(sm.quantity) as total_quantity,
                SUM(sm.amount) as total_value,
                COUNT(DISTINCT v.id) as transaction_count,
                AVG(sm.rate) as avg_rate
            FROM stock_movements sm
            JOIN vouchers v ON sm.voucher_id = v.id
            WHERE sm.item_id = ?
            AND (lower(v.voucher_type) LIKE '%sales%' OR lower(sm.movement_type) IN ('out', 'outward'))
            GROUP BY v.party_name
            ORDER BY total_quantity DESC
            LIMIT 10
        """, (real_item_id,))
        
        top_customers = [dict(r) for r in cursor.fetchall()]
        
        # ========================================
        # 6. RATE TRENDS (Last 6 months)
        # ========================================
        cursor.execute("""
            SELECT 
                strftime('%Y-%m', v.date) as month,
                v.voucher_type,
                AVG(sm.rate) as avg_rate,
                MIN(sm.rate) as min_rate,
                MAX(sm.rate) as max_rate,
                SUM(sm.quantity) as quantity
            FROM stock_movements sm
            JOIN vouchers v ON sm.voucher_id = v.id
            WHERE sm.item_id = ?
            AND v.date >= date('now', '-6 months')
            GROUP BY month, v.voucher_type
            ORDER BY month DESC
        """, (real_item_id,))
        
        rate_trends = [dict(r) for r in cursor.fetchall()]
        
        # ========================================
        # 7. PROFIT ANALYSIS
        # ========================================
        avg_purchase_rate = (
            sum(p['rate'] for p in purchase_history) / len(purchase_history)
            if purchase_history else item_data.get('purchase_rate', 0)
        )
        
        avg_sale_rate = (
            sum(s['rate'] for s in sales_history) / len(sales_history)
            if sales_history else item_data.get('sales_rate', 0)
        )
        
        profit_per_unit = avg_sale_rate - avg_purchase_rate
        profit_margin = (
            (profit_per_unit / avg_sale_rate * 100) 
            if avg_sale_rate > 0 else 0
        )
        
        # Stock value
        current_stock = item_data.get('current_stock', 0) or 0
        current_stock_value = (
            current_stock * avg_purchase_rate
        )
        
        profit_analysis = {
            "avg_purchase_rate": round(avg_purchase_rate, 2),
            "avg_sale_rate": round(avg_sale_rate, 2),
            "profit_per_unit": round(profit_per_unit, 2),
            "profit_margin_percent": round(profit_margin, 2),
            "current_stock_value": round(current_stock_value, 2)
        }
        
        # ========================================
        # 8. MOVEMENT INSIGHTS
        # ========================================
        turnover_ratio = (
            (stock_summary['total_outward'] / current_stock)
            if current_stock > 0 else 0
        )
        
        stock_days = 999
        if stock_summary['total_outward'] > 0:
            daily_outward = stock_summary['total_outward'] / 365 # Or based on date range?
            stock_days = current_stock / daily_outward

        insights = {
            "turnover_ratio": turnover_ratio,
            "fast_moving": stock_summary['total_movements'] > 50,
            "reorder_alert": current_stock < (item_data.get('opening_stock', 0) * 0.2),
            "stock_days": stock_days,
            "status": "In Stock" if current_stock > 0 else "Out of Stock"
        }
        
        conn.close()
        
        # ========================================
        # RETURN COMPLETE 360° VIEW
        # ========================================
        return {
            "item": item_data,
            "stock_summary": {
                **stock_summary,
                "current_stock": current_stock,
                "stock_value": current_stock_value,
                "unit": item_data['unit']
            },
            "purchase_history": purchase_history,
            "sales_history": sales_history,
            "top_customers": top_customers,
            "rate_trends": rate_trends,
            "profit_analysis": profit_analysis,
            "insights": insights
        }
    except Exception as e:
        logger.exception(f"Failed to get item 360 for {item_id}")
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/items")
async def get_items_list(
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get paginated list of items with search
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        if search:
            cursor.execute("""
                SELECT id, name, part_number as sku, closing_balance as current_stock, units as unit, selling_price as sales_rate, is_active
                FROM items
                WHERE (name LIKE ? OR part_number LIKE ?)
                AND is_active = 1
                ORDER BY name
                LIMIT ? OFFSET ?
            """, (f'%{search}%', f'%{search}%', limit, offset))
        else:
            cursor.execute("""
                SELECT id, name, part_number as sku, closing_balance as current_stock, units as unit, selling_price as sales_rate, is_active
                FROM items
                WHERE is_active = 1
                ORDER BY name
                LIMIT ? OFFSET ?
            """, (limit, offset))
        
        items = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        cursor.execute("SELECT COUNT(*) as total FROM items WHERE is_active = 1")
        total = cursor.fetchone()['total']
        
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    finally:
        conn.close()
