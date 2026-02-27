"""
Dashboard API - Provides KPIs, Charts, and Summary Statistics
DB-ONLY: Reads exclusively from SQLite shadow DB.
Tally sync runs in background — dashboard is always instant.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from datetime import datetime, timedelta
import logging
import os

from backend.database import get_db, Ledger, Voucher, StockItem, Bill, SessionLocal
from backend.dependencies import get_api_key, get_tenant_id

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
logger = logging.getLogger("dashboard")

# ─────────────────────────────────────────────
# /stats  — KPI Cards
# ─────────────────────────────────────────────
@router.get("/stats", dependencies=[Depends(get_api_key)])
def get_dashboard_stats(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    KPI stats — reads from DB only.
    Sales YTD, Total Receivables, Total Payables, Cash+Bank balance.
    """
    now = datetime.now()
    fy_start = datetime(now.year - 1 if now.month < 4 else now.year, 4, 1)

    # Sales YTD
    sales_total = db.query(func.sum(Voucher.amount)).filter(
        Voucher.tenant_id == tenant_id,
        Voucher.voucher_type.ilike("%sales%"),
        Voucher.date >= fy_start
    ).scalar() or 0.0

    # Receivables: positive debtor balances
    receivables = db.query(func.sum(Ledger.closing_balance)).filter(
        Ledger.tenant_id == tenant_id,
        Ledger.parent.ilike("%debtor%"),
        Ledger.closing_balance > 0
    ).scalar() or 0.0

    # Payables: positive creditor balances (stored as positive)
    payables = db.query(func.sum(Ledger.closing_balance)).filter(
        Ledger.tenant_id == tenant_id,
        Ledger.parent.ilike("%creditor%"),
        Ledger.closing_balance > 0
    ).scalar() or 0.0

    # Cash + Bank (abs stored by sync_engine fix)
    cash = db.query(func.sum(Ledger.closing_balance)).filter(
        Ledger.tenant_id == tenant_id,
        or_(
            Ledger.parent.ilike("%cash%"),
            Ledger.parent.ilike("%bank%")
        )
    ).scalar() or 0.0

    return {
        "sales": round(sales_total, 2),
        "sales_change": 0,
        "receivables": round(receivables, 2),
        "receivables_change": 0,
        "payables": round(payables, 2),
        "payables_change": 0,
        "cash": round(cash, 2),
        "last_updated": datetime.now().isoformat(),
        "source": "database"
    }


# ─────────────────────────────────────────────
# /receivables  — Top debtors bar chart
# ─────────────────────────────────────────────
@router.get("/receivables", dependencies=[Depends(get_api_key)])
def get_top_receivables(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """Top 5 outstanding receivables for bar chart — DB only."""
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
        {"name": r.name[:20], "amount": round(r.closing_balance, 2)}
        for r in top_debtors
    ]


# ─────────────────────────────────────────────
# /cashflow  — Daily net cashflow chart
# ─────────────────────────────────────────────
@router.get("/cashflow", dependencies=[Depends(get_api_key)])
def get_cashflow(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """Daily net cashflow (Receipts - Payments) for last 90 days — DB only."""
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=90)

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
        daily_map.setdefault(d_key, 0.0)
        v_type = (v.voucher_type or "").lower()
        amt = v.amount or 0
        if "receipt" in v_type:
            daily_map[d_key] += amt
        elif "payment" in v_type:
            daily_map[d_key] -= amt

    result = []
    for k in sorted(daily_map.keys()):
        try:
            dt = datetime.strptime(k, "%Y%m%d")
            result.append({"date": dt.strftime("%b %d"), "value": round(daily_map[k], 2)})
        except Exception:
            pass

    # Ensure chart always has data to render
    if not result:
        result = [
            {"date": (end_dt - timedelta(days=i)).strftime("%b %d"), "value": 0}
            for i in range(7, 0, -1)
        ]

    return result


# ─────────────────────────────────────────────
# /stock-summary  — Inventory KPIs
# ─────────────────────────────────────────────
@router.get("/stock-summary", dependencies=[Depends(get_api_key)])
def get_dashboard_stock(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """Stock summary metrics — DB only (synced by background service)."""
    items = db.query(StockItem).filter(
        StockItem.tenant_id == tenant_id
    ).all()

    total_value = 0.0
    low_stock_count = 0
    detailed_items = []

    for item in items:
        qty  = item.closing_balance or 0
        rate = item.rate or item.cost_price or 0
        val  = qty * rate
        total_value += val

        if qty <= 0:
            status = "Out of Stock"
        elif qty < 10:
            status = "Low Stock"
            low_stock_count += 1
        else:
            status = "In Stock"

        detailed_items.append({
            "name":     item.name or "Unknown",
            "quantity": qty,
            "rate":     rate,
            "value":    round(val, 2),
            "status":   status
        })

    detailed_items.sort(key=lambda x: x["value"], reverse=True)

    return {
        "total_items":    len(items),
        "low_stock_items": low_stock_count,
        "total_value":    round(total_value, 2),
        "items":          detailed_items[:50],
        "source":         "database"
    }


# ─────────────────────────────────────────────
# /gst-summary  — GST placeholder
# ─────────────────────────────────────────────
@router.get("/gst-summary", dependencies=[Depends(get_api_key)])
def get_dashboard_gst(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    GST summary — placeholder until GST ledgers are synced.
    Returns zeros for now; will be populated when GSTLedger sync is active.
    """
    return {
        "cgst_collected": 0,
        "cgst_paid": 0,
        "sgst_collected": 0,
        "sgst_paid": 0,
        "igst_collected": 0,
        "igst_paid": 0,
        "total_liability": 0
    }


# ─────────────────────────────────────────────
# /party-analysis  — Top customers & suppliers
# ─────────────────────────────────────────────
@router.get("/party-analysis", dependencies=[Depends(get_api_key)])
def get_dashboard_party(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """Top customers and suppliers for current FY — DB only."""
    now = datetime.now()
    fy_start = datetime(now.year - 1 if now.month < 4 else now.year, 4, 1)

    top_customers = db.query(
        Voucher.party_name,
        func.sum(Voucher.amount).label("total")
    ).filter(
        Voucher.tenant_id == tenant_id,
        Voucher.voucher_type.ilike("%sales%"),
        Voucher.date >= fy_start,
        Voucher.party_name != None
    ).group_by(Voucher.party_name).order_by(desc("total")).limit(5).all()

    top_suppliers = db.query(
        Voucher.party_name,
        func.sum(Voucher.amount).label("total")
    ).filter(
        Voucher.tenant_id == tenant_id,
        Voucher.voucher_type.ilike("%purchase%"),
        Voucher.date >= fy_start,
        Voucher.party_name != None
    ).group_by(Voucher.party_name).order_by(desc("total")).limit(5).all()

    return {
        "top_customers": [
            {"name": r.party_name, "value": round(r.total or 0, 2)}
            for r in top_customers
        ],
        "top_suppliers": [
            {"name": r.party_name, "value": round(r.total or 0, 2)}
            for r in top_suppliers
        ]
    }
