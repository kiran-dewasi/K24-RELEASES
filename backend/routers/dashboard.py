"""
Dashboard API - Provides KPIs, Charts, and Summary Statistics
Now with database fallback when Tally is offline.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, desc
from datetime import datetime, timedelta
import logging
from typing import Optional

from backend.database import get_db, Ledger, Voucher, StockItem, Bill
from backend.dependencies import get_api_key

# Try to import TallyReader, but don't fail if it doesn't work
try:
    from backend.tally_reader import TallyReader
    TALLY_AVAILABLE = True
except Exception:
    TALLY_AVAILABLE = False

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
logger = logging.getLogger("dashboard")

# Helper to get tenant_id without requiring JWT (uses default for API key auth)
def get_tenant_id_or_default() -> str:
    """Returns default tenant_id for API key authenticated requests."""
    return "default"


def is_tally_online() -> bool:
    """Quick check if Tally is responding"""
    if not TALLY_AVAILABLE:
        return False
    try:
        import requests
        response = requests.post(
            "http://localhost:9000",
            data="<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY></BODY></ENVELOPE>",
            timeout=5  # Increased from 1 to 5 seconds
        )
        return response.status_code == 200
    except:
        return False


# --- KPI Stats ---
@router.get("/stats", dependencies=[Depends(get_api_key)])
def get_dashboard_stats(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_or_default)
):
    """
    Returns KPI stats for the dashboard.
    Tries Tally first, falls back to database.
    """
    # Try Tally first
    if is_tally_online():
        try:
            reader = TallyReader()
            now = datetime.now()
            if now.month < 4:
                start_date = f"{now.year-1}0401"
            else:
                start_date = f"{now.year}0401"
            end_date = now.strftime("%Y%m%d")
            
            sales_data = reader.get_daybook_stats(start_date, end_date) 
            receivables_list = reader.get_receivables() 
            total_receivables = sum(x['amount'] for x in receivables_list)
            payables_list = reader.get_payables()
            total_payables = sum(x['amount'] for x in payables_list)
            cash_bal = reader.get_cash_bank_balance()
            
            return {
                "sales": sales_data.get("total_sales", 0),
                "sales_change": 0, 
                "receivables": total_receivables,
                "receivables_change": 0,
                "payables": total_payables,
                "payables_change": 0,
                "cash": cash_bal,
                "last_updated": datetime.now().isoformat(),
                "source": "tally"
            }
        except Exception as e:
            logger.warning(f"Tally stats failed, using database: {e}")
    
    # Fallback: Use local database
    now = datetime.now()
    if now.month < 4:
        fy_start = datetime(now.year - 1, 4, 1)
    else:
        fy_start = datetime(now.year, 4, 1)
    
    # Sales (YTD) from vouchers
    sales_total = db.query(func.sum(Voucher.amount)).filter(
        Voucher.tenant_id == tenant_id,
        Voucher.voucher_type.ilike("%sales%"),
        Voucher.date >= fy_start
    ).scalar() or 0.0
    
    # Receivables: Sum of positive closing balances for Sundry Debtors
    receivables = db.query(func.sum(Ledger.closing_balance)).filter(
        Ledger.tenant_id == tenant_id,
        Ledger.parent.ilike("%debtor%"),
        Ledger.closing_balance > 0
    ).scalar() or 0.0
    
    # Payables: Sum of positive closing balances for Sundry Creditors (since we store Cr as positive)
    payables = db.query(func.sum(Ledger.closing_balance)).filter(
        Ledger.tenant_id == tenant_id,
        Ledger.parent.ilike("%creditor%"),
        Ledger.closing_balance > 0
    ).scalar() or 0.0
    
    # Cash/Bank: Sum of cash and bank ledger balances
    cash = db.query(func.sum(Ledger.closing_balance)).filter(
        Ledger.tenant_id == tenant_id,
        or_(
            Ledger.parent.ilike("%cash%"),
            Ledger.parent.ilike("%bank%")
        )
    ).scalar() or 0.0
    
    return {
        "sales": sales_total,
        "sales_change": 0, 
        "receivables": receivables,
        "receivables_change": 0,
        "payables": payables,
        "payables_change": 0,
        "cash": cash,
        "last_updated": datetime.now().isoformat(),
        "source": "database"
    }


# --- Top Receivables Chart ---
@router.get("/receivables", dependencies=[Depends(get_api_key)])
def get_top_receivables(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_or_default)
):
    """
    Returns top 5 outstanding receivables for bar chart.
    """
    # Try Tally first
    if is_tally_online():
        try:
            reader = TallyReader()
            data = reader.get_receivables()
            sorted_data = sorted(data, key=lambda x: x['amount'], reverse=True)
            return [
                {"name": x['party_name'][:15], "amount": x['amount']}
                for x in sorted_data[:5]
            ]
        except Exception as e:
            logger.warning(f"Tally receivables failed: {e}")
    
    # Fallback: Database
    top_debtors = db.query(
        Ledger.name,
        Ledger.closing_balance
    ).filter(
        Ledger.tenant_id == tenant_id,
        Ledger.parent.ilike("%debtor%"),
        Ledger.closing_balance > 0
    ).order_by(
        desc(Ledger.closing_balance)
    ).limit(5).all()
    
    return [
        {"name": r.name[:15], "amount": r.closing_balance}
        for r in top_debtors
    ]


# --- Cashflow Chart ---
@router.get("/cashflow", dependencies=[Depends(get_api_key)])
def get_cashflow(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_or_default)
):
    """
    Returns daily net cashflow (Receipts - Payments) for last 90 days.
    """
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=90)
    
    # Try Tally first
    if is_tally_online():
        try:
            reader = TallyReader()
            txns = reader.get_transactions(start_dt.strftime("%Y%m%d"), end_dt.strftime("%Y%m%d"))
            
            daily_map = {}
            for txn in txns:
                d = txn.get("date")
                if not d: continue
                t = txn.get("type", "").lower()
                try:
                    a = float(txn.get("amount", 0))
                except:
                    a = 0.0
                    
                if d not in daily_map:
                    daily_map[d] = 0.0
                    
                if "receipt" in t:
                    daily_map[d] += a
                elif "payment" in t:
                    daily_map[d] -= a
                     
            sorted_keys = sorted(daily_map.keys())
            result = []
            for k in sorted_keys:
                val = daily_map[k]
                try:
                    dt = datetime.strptime(k, "%Y%m%d")
                    result.append({"date": dt.strftime("%b %d"), "value": val})
                except:
                    pass
            return result
        except Exception as e:
            logger.warning(f"Tally cashflow failed: {e}")
    
    # Fallback: Database
    vouchers = db.query(Voucher).filter(
        Voucher.tenant_id == tenant_id,
        Voucher.date >= start_dt,
        Voucher.date <= end_dt,
        or_(
            Voucher.voucher_type.ilike("%receipt%"),
            Voucher.voucher_type.ilike("%payment%")
        )
    ).order_by(Voucher.date.asc()).all()
    
    daily_map = {}
    for v in vouchers:
        if not v.date:
            continue
        d_key = v.date.strftime("%Y%m%d")
        if d_key not in daily_map:
            daily_map[d_key] = 0.0
            
        v_type = (v.voucher_type or "").lower()
        if "receipt" in v_type:
            daily_map[d_key] += v.amount or 0
        elif "payment" in v_type:
            daily_map[d_key] -= v.amount or 0
    
    sorted_keys = sorted(daily_map.keys())
    result = []
    for k in sorted_keys:
        try:
            dt = datetime.strptime(k, "%Y%m%d")
            result.append({"date": dt.strftime("%b %d"), "value": daily_map[k]})
        except:
            pass
    
    # If no data, generate sample dates with 0 values for chart to render
    if not result:
        result = [
            {"date": (end_dt - timedelta(days=i)).strftime("%b %d"), "value": 0}
            for i in range(7, 0, -1)
        ]
    
    return result


# --- Stock Summary ---
@router.get("/stock-summary", dependencies=[Depends(get_api_key)])
def get_dashboard_stock(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_or_default)
):
    """Returns stock summary metrics."""
    # Try Tally first
    if is_tally_online():
        try:
            reader = TallyReader()
            items = reader.get_stock_summary()
            
            total_value = 0.0
            low_stock_count = 0
            detailed_items = []
            
            for i in items:
                try:
                    val = float(i.get("value", 0) or 0)
                    qty = float(i.get("closing_balance", 0) or 0)
                    rate = float(i.get("rate", 0) or 0)
                except:
                    val, qty, rate = 0.0, 0.0, 0.0
                    
                total_value += val
                
                status = "In Stock"
                if qty <= 0:
                    status = "Out of Stock"
                elif qty < 10:
                    status = "Low Stock"
                    low_stock_count += 1
                    
                detailed_items.append({
                    "name": i.get("name", "Unknown"),
                    "quantity": qty,
                    "rate": rate,
                    "value": val,
                    "status": status
                })
                     
            detailed_items.sort(key=lambda x: x["value"], reverse=True)
                     
            return {
                "total_items": len(items),
                "low_stock_items": low_stock_count,
                "total_value": total_value,
                "items": detailed_items[:50]
            }
        except Exception as e:
            logger.warning(f"Tally stock summary failed: {e}")
    
    # Fallback: Database
    items = db.query(StockItem).filter(
        StockItem.tenant_id == tenant_id
    ).all()
    
    total_value = 0.0
    low_stock_count = 0
    detailed_items = []
    
    for item in items:
        qty = item.closing_balance or 0
        rate = item.rate or 0
        val = qty * rate
        
        total_value += val
        
        status = "In Stock"
        if qty <= 0:
            status = "Out of Stock"
        elif qty < 10:
            status = "Low Stock"
            low_stock_count += 1
            
        detailed_items.append({
            "name": item.name or "Unknown",
            "quantity": qty,
            "rate": rate,
            "value": val,
            "status": status
        })
    
    detailed_items.sort(key=lambda x: x["value"], reverse=True)
    
    return {
        "total_items": len(items),
        "low_stock_items": low_stock_count,
        "total_value": total_value,
        "items": detailed_items[:50]
    }


# --- GST Summary ---
@router.get("/gst-summary", dependencies=[Depends(get_api_key)])
def get_dashboard_gst(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_or_default)
):
    """Returns GST tax summary for current month."""
    now = datetime.now()
    start_date = now.replace(day=1)
    
    # Try Tally first
    if is_tally_online():
        try:
            reader = TallyReader()
            return reader.get_tax_summary(
                start_date.strftime("%Y%m%d"), 
                now.strftime("%Y%m%d")
            )
        except Exception as e:
            logger.warning(f"Tally GST summary failed: {e}")
    
    # Fallback: Calculate from vouchers
    # This is a simplified calculation - real GST would need proper tax ledger analysis
    sales_vouchers = db.query(func.sum(Voucher.amount)).filter(
        Voucher.tenant_id == tenant_id,
        Voucher.voucher_type.ilike("%sales%"),
        Voucher.date >= start_date
    ).scalar() or 0.0
    
    purchase_vouchers = db.query(func.sum(Voucher.amount)).filter(
        Voucher.tenant_id == tenant_id,
        Voucher.voucher_type.ilike("%purchase%"),
        Voucher.date >= start_date
    ).scalar() or 0.0
    
    # Estimate GST at 18% (simplified) -> COMMENTED OUT AS PER USER REQUEST
    # est_gst_rate = 0.18
    # output_gst = (sales_vouchers * est_gst_rate) / (1 + est_gst_rate)
    # input_gst = (purchase_vouchers * est_gst_rate) / (1 + est_gst_rate)
    
    # Placeholder
    output_gst = 0.0
    input_gst = 0.0
    
    return {
        "cgst_collected": 0,
        "cgst_paid": 0,
        "sgst_collected": 0,
        "sgst_paid": 0,
        "igst_collected": 0,
        "igst_paid": 0,
        "total_liability": 0
    }


# --- Party Analysis ---
@router.get("/party-analysis", dependencies=[Depends(get_api_key)])
def get_dashboard_party(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_or_default)
):
    """Returns Top Customers and Suppliers for current FY."""
    now = datetime.now()
    if now.month < 4:
        fy_start = datetime(now.year - 1, 4, 1)
    else:
        fy_start = datetime(now.year, 4, 1)
    
    # Try Tally first
    if is_tally_online():
        try:
            reader = TallyReader()
            return reader.get_party_metrics(
                fy_start.strftime("%Y%m%d"), 
                now.strftime("%Y%m%d")
            )
        except Exception as e:
            logger.warning(f"Tally party analysis failed: {e}")
    
    # Fallback: Database - Aggregate from vouchers
    # Top Customers (by Sales)
    top_customers = db.query(
        Voucher.party_name,
        func.sum(Voucher.amount).label("total")
    ).filter(
        Voucher.tenant_id == tenant_id,
        Voucher.voucher_type.ilike("%sales%"),
        Voucher.date >= fy_start,
        Voucher.party_name != None
    ).group_by(
        Voucher.party_name
    ).order_by(
        desc("total")
    ).limit(5).all()
    
    # Top Suppliers (by Purchases)
    top_suppliers = db.query(
        Voucher.party_name,
        func.sum(Voucher.amount).label("total")
    ).filter(
        Voucher.tenant_id == tenant_id,
        Voucher.voucher_type.ilike("%purchase%"),
        Voucher.date >= fy_start,
        Voucher.party_name != None
    ).group_by(
        Voucher.party_name
    ).order_by(
        desc("total")
    ).limit(5).all()
    
    return {
        "top_customers": [
            {"name": r.party_name, "value": r.total or 0}
            for r in top_customers
        ],
        "top_suppliers": [
            {"name": r.party_name, "value": r.total or 0}
            for r in top_suppliers
        ]
    }
