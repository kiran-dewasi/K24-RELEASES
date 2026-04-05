from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import calendar
import io

from database import get_db, Voucher, Ledger, Bill
from dependencies import get_tenant_id
from utils.pdf_generator import generate_report_pdf
from utils.excel_generator import generate_report_excel
from utils.report_template import generate_gst_summary_excel as _tmpl_gst_excel
import os

router = APIRouter(prefix="/reports", tags=["reports"])


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def _default_fy_dates() -> tuple[date, date]:
    """Return start and end of the current Indian Financial Year (Apr–Mar)."""
    now = datetime.now()
    fy_start_year = now.year if now.month >= 4 else now.year - 1
    return date(fy_start_year, 4, 1), date(fy_start_year + 1, 3, 31)


def _build_voucher_filters(
    db_query,
    date_from: Optional[str],
    date_to: Optional[str],
    voucher_types: List[str],
    party_name: Optional[str],
    tenant_id: str,
):
    """Apply common filter conditions to a Voucher query with deduplication."""
    db_query = db_query.filter(
        Voucher.tenant_id == tenant_id,
        Voucher.is_deleted == False  # ← ENTERPRISE: Exclude soft-deleted vouchers
    )
    d_from = _parse_date(date_from)
    d_to = _parse_date(date_to)

    if not d_from and not d_to:
        d_from, d_to = _default_fy_dates()

    if d_from:
        db_query = db_query.filter(Voucher.date >= datetime.combine(d_from, datetime.min.time()))
    if d_to:
        db_query = db_query.filter(Voucher.date <= datetime.combine(d_to, datetime.max.time()))
    if voucher_types:
        db_query = db_query.filter(Voucher.voucher_type.in_(voucher_types))
    if party_name:
        db_query = db_query.filter(Voucher.party_name.ilike(f"%{party_name}%"))

    # DEDUPLICATION: Ensure unique vouchers by (tenant_id, voucher_number, date, voucher_type)
    session = db_query.session

    # Build filters for subquery
    filters = [
        Voucher.tenant_id == tenant_id,
        Voucher.is_deleted == False
    ]
    if d_from:
        filters.append(Voucher.date >= datetime.combine(d_from, datetime.min.time()))
    if d_to:
        filters.append(Voucher.date <= datetime.combine(d_to, datetime.max.time()))
    if voucher_types:
        filters.append(Voucher.voucher_type.in_(voucher_types))
    if party_name:
        filters.append(Voucher.party_name.ilike(f"%{party_name}%"))

    # Subquery: select MAX(id) per unique voucher identity to pick one representative
    max_id_subq = (
        session.query(func.max(Voucher.id).label('max_id'))
        .filter(and_(*filters))
        .group_by(
            Voucher.tenant_id,
            Voucher.voucher_number,
            Voucher.date,
            Voucher.voucher_type
        )
        .subquery()
    )

    # Return deduplicated query: only vouchers with IDs from subquery
    return session.query(Voucher).filter(
        Voucher.id.in_(session.query(max_id_subq.c.max_id))
    )


def _voucher_to_dict(v: Voucher) -> dict:
    return {
        "id": v.id,
        "date": v.date.strftime("%d-%b-%Y") if v.date else None,
        "date_iso": v.date.date().isoformat() if v.date else None,
        "party_name": v.party_name or "—",
        "voucher_type": v.voucher_type,
        "voucher_no": v.voucher_number or "—",
        "amount": v.amount or 0.0,
        "narration": v.narration,
    }


def _build_monthly_data(vouchers: list, d_from: Optional[date] = None, d_to: Optional[date] = None) -> list:
    """Return monthly chart data across the FULL FY period (Apr→Mar), zero-filling empty months."""
    # Determine the FY span to chart
    if not d_from or not d_to:
        d_from, d_to = _default_fy_dates()

    # Build Indian FY month sequence: Apr(4) → Mar(3)
    fy_start_month = 4  # April
    fy_months: list[int] = []
    m = fy_start_month
    while True:
        fy_months.append(m)
        if len(fy_months) == 12:
            break
        m = m % 12 + 1

    # Aggregate vouchers by month
    monthly: Dict[int, float] = {}
    monthly_count: Dict[int, int] = {}
    for v in vouchers:
        if v.date:
            mo = v.date.month
            monthly[mo] = monthly.get(mo, 0.0) + (v.amount or 0)
            monthly_count[mo] = monthly_count.get(mo, 0) + 1

    # Build result: all 12 FY months in order, zero-fill missing
    result = []
    for mo in fy_months:
        result.append({
            "month_num": mo,
            "month_name": calendar.month_abbr[mo],
            "total_amount": round(monthly.get(mo, 0.0), 2),
            "voucher_count": monthly_count.get(mo, 0),
        })
    return result


# ─────────────────────────────────────────────
#  Sales Register
# ─────────────────────────────────────────────
@router.get("/sales-register")
def get_sales_register(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    voucher_types: Optional[str] = Query(None, description="Comma-separated e.g. Sales,Credit Note"),
    party_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    vtype_list = [v.strip() for v in voucher_types.split(",")] if voucher_types else ["Sales", "Credit Note"]

    d_from = _parse_date(date_from)
    d_to = _parse_date(date_to)
    q = _build_voucher_filters(db.query(Voucher), date_from, date_to, vtype_list, party_name, tenant_id)
    vouchers = q.order_by(Voucher.date.desc()).all()

    total_amount = sum(v.amount or 0 for v in vouchers)
    total_count = len(vouchers)
    tax_estimate = total_amount * 0.18

    response = JSONResponse(content={
        "total_amount": total_amount,
        "total_count": total_count,
        "tax_estimate": tax_estimate,
        "monthly_data": _build_monthly_data(vouchers, d_from, d_to),
        "vouchers": [_voucher_to_dict(v) for v in vouchers],
    })
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


# ─────────────────────────────────────────────
#  Purchase Register
# ─────────────────────────────────────────────
@router.get("/purchase-register")
def get_purchase_register(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    voucher_types: Optional[str] = Query(None),
    party_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    vtype_list = [v.strip() for v in voucher_types.split(",")] if voucher_types else ["Purchase", "Debit Note"]
    d_from = _parse_date(date_from)
    d_to = _parse_date(date_to)
    q = _build_voucher_filters(db.query(Voucher), date_from, date_to, vtype_list, party_name, tenant_id)
    vouchers = q.order_by(Voucher.date.desc()).all()

    total_amount = sum(v.amount or 0 for v in vouchers)
    total_count = len(vouchers)

    response = JSONResponse(content={
        "total_amount": total_amount,
        "total_count": total_count,
        "monthly_data": _build_monthly_data(vouchers, d_from, d_to),
        "vouchers": [_voucher_to_dict(v) for v in vouchers],
    })
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


# ─────────────────────────────────────────────
#  Cash Flow  (Receipt + Payment vouchers)
# ─────────────────────────────────────────────
@router.get("/cash-flow")
def get_cash_flow(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    inflow_q = _build_voucher_filters(
        db.query(Voucher), date_from, date_to, ["Receipt", "Sales"], None, tenant_id
    )
    outflow_q = _build_voucher_filters(
        db.query(Voucher), date_from, date_to, ["Payment", "Purchase"], None, tenant_id
    )

    inflows = inflow_q.order_by(Voucher.date.desc()).all()
    outflows = outflow_q.order_by(Voucher.date.desc()).all()

    total_inflow = sum(v.amount or 0 for v in inflows)
    total_outflow = sum(v.amount or 0 for v in outflows)
    net_flow = total_inflow - total_outflow

    # Combine and mark direction
    all_vouchers = []
    for v in inflows:
        d = _voucher_to_dict(v)
        d["direction"] = "inflow"
        all_vouchers.append(d)
    for v in outflows:
        d = _voucher_to_dict(v)
        d["direction"] = "outflow"
        all_vouchers.append(d)

    all_vouchers.sort(key=lambda x: x["date_iso"] or "", reverse=True)

    response = JSONResponse(content={
        "total_inflow": total_inflow,
        "total_outflow": total_outflow,
        "net_flow": net_flow,
        "total_count": len(all_vouchers),
        "monthly_data": _build_monthly_data(inflows),  # chart shows inflows
        "vouchers": all_vouchers,
    })
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


# ─────────────────────────────────────────────
#  Balance Sheet
# ─────────────────────────────────────────────
@router.get("/balance-sheet")
def get_balance_sheet(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    ledgers = db.query(Ledger).filter(Ledger.tenant_id == tenant_id).all()

    assets, liabilities = [], []
    total_assets, total_liabilities = 0.0, 0.0

    for l in ledgers:
        parent = (l.parent or "").lower()
        amount = l.closing_balance or 0.0

        if any(k in parent for k in ["asset", "cash", "bank", "debtor", "receivable"]):
            assets.append({"name": l.name, "amount": abs(amount), "group": l.parent or "Other Assets"})
            total_assets += abs(amount)
        elif any(k in parent for k in ["liabilit", "capital", "loan", "creditor", "payable"]):
            liabilities.append({"name": l.name, "amount": abs(amount), "group": l.parent or "Other Liabilities"})
            total_liabilities += abs(amount)
        else:
            if amount >= 0:
                assets.append({"name": l.name, "amount": amount, "group": "Other Assets"})
                total_assets += amount
            else:
                liabilities.append({"name": l.name, "amount": abs(amount), "group": "Other Liabilities"})
                total_liabilities += abs(amount)

    return {
        "total_count": len(assets) + len(liabilities),
        "assets": sorted(assets, key=lambda x: x["amount"], reverse=True),
        "liabilities": sorted(liabilities, key=lambda x: x["amount"], reverse=True),
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_difference": total_assets - total_liabilities,
    }


# ─────────────────────────────────────────────
#  Profit & Loss
# ─────────────────────────────────────────────
@router.get("/profit-loss")
def get_profit_loss(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    sales_q = _build_voucher_filters(db.query(Voucher), date_from, date_to, ["Sales"], None, tenant_id)
    purchase_q = _build_voucher_filters(db.query(Voucher), date_from, date_to, ["Purchase"], None, tenant_id)

    sales_vouchers = sales_q.all()
    purchase_vouchers = purchase_q.all()

    total_sales = sum(v.amount or 0 for v in sales_vouchers)
    total_purchases = sum(v.amount or 0 for v in purchase_vouchers)
    net_profit = total_sales - total_purchases

    response = JSONResponse(content={
        "total_count": len(sales_vouchers) + len(purchase_vouchers),
        "income": {"Sales Accounts": total_sales, "Direct Income": 0.0, "Indirect Income": 0.0},
        "expenses": {"Purchase Accounts": total_purchases, "Direct Expenses": 0.0, "Indirect Expenses": 0.0},
        "total_income": total_sales,
        "total_expenses": total_purchases,
        "net_profit": net_profit,
        "monthly_data": _build_monthly_data(sales_vouchers),
    })
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


# ─────────────────────────────────────────────
#  Cash Book (legacy – balance only)
# ─────────────────────────────────────────────
@router.get("/cash-book")
def get_cash_book(db: Session = Depends(get_db)):
    cash_ledger = db.query(Ledger).filter(Ledger.name.ilike("Cash")).first()
    if not cash_ledger:
        return {"ledger_name": "Cash", "current_balance": 0.0, "last_synced": None}
    return {
        "ledger_name": cash_ledger.name,
        "current_balance": cash_ledger.closing_balance,
        "last_synced": cash_ledger.last_synced,
    }


# ─────────────────────────────────────────────
#  Universal PDF Export
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
#  Universal PDF / Excel Export
# ─────────────────────────────────────────────



@router.get("/{slug}/export")
def export_report_pdf(
    slug: str,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    voucher_types: Optional[str] = Query(None),
    party_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Universal PDF export for any report slug. Streams a PDF file."""
    from services.canonical_export_engine import CanonicalExportEngine
    engine = CanonicalExportEngine(db, tenant_id)
    
    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "voucher_types": voucher_types,
        "party_name": party_name,
    }
    
    try:
        result = engine.generate_export_bytes(slug, "pdf", filters)
    except Exception as e:
        logger.error(f"Generate PDF error for {slug}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    return StreamingResponse(
        io.BytesIO(result["bytes"]),
        media_type=result["mime_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{result["filename"]}"',
            "Content-Length": str(len(result["bytes"])),
            "Cache-Control": "no-store, no-cache, must-revalidate",
        },
    )




@router.get("/{slug}/export-excel")
def export_report_excel(
    slug: str,
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    voucher_types: Optional[str] = Query(None),
    party_name:    Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Universal Excel export for any report slug. Streams an XLSX file."""
    from services.canonical_export_engine import CanonicalExportEngine
    engine = CanonicalExportEngine(db, tenant_id)
    
    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "voucher_types": voucher_types,
        "party_name": party_name,
    }
    
    try:
        result = engine.generate_export_bytes(slug, "excel", filters)
    except Exception as e:
        logger.error(f"Generate Excel error for {slug}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    return StreamingResponse(
        io.BytesIO(result["bytes"]),
        media_type=result["mime_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{result["filename"]}"',
            "Content-Length": str(len(result["bytes"])),
            "Cache-Control": "no-store, no-cache, must-revalidate",
        },
    )
