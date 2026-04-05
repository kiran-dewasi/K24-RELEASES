import os
import io
import logging
import calendar
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from database import Voucher, Ledger, StockItem, StockMovement, Bill
from utils.pdf_generator import generate_report_pdf
from utils.excel_generator import generate_report_excel
from utils.report_template import generate_gst_summary_excel as _tmpl_gst_excel

logger = logging.getLogger("CanonicalExportEngine")

def get_exports_dir() -> Path:
    base_dir = Path(os.environ.get("K24_DATA_DIR", os.path.dirname(os.path.dirname(__file__))))
    exports_dir = base_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    return exports_dir

def _parse_date(date_str: Optional[str]) -> Optional[date]:
    if isinstance(date_str, datetime):
        return date_str.date()
    if isinstance(date_str, date):
        return date_str
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        try:
            return datetime.strptime(date_str.replace("-",""), "%Y%m%d").date()
        except ValueError:
            return None

def _default_fy_dates() -> tuple[date, date]:
    now = datetime.now()
    fy_start_year = now.year if now.month >= 4 else now.year - 1
    return date(fy_start_year, 4, 1), date(fy_start_year + 1, 3, 31)

def _build_voucher_filters(db_query, date_from: Optional[str], date_to: Optional[str], voucher_types: List[str], party_name: Optional[str], tenant_id: str):
    db_query = db_query.filter(
        Voucher.tenant_id == tenant_id,
        Voucher.is_deleted == False
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

    session = db_query.session

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

_REPORT_TITLES = {
    "sales-register":    "Sales Register",
    "purchase-register": "Purchase Register",
    "cash-flow":         "Cash Flow Statement",
    "balance-sheet":     "Balance Sheet",
    "profit-loss":       "Profit & Loss Account",
    "receipt-register":  "Receipt Register",
    "payment-register":  "Payment Register",
    "journal-register":  "Journal Register",
    "gst-summary":       "GST Summary",
    "receivables":       "Outstanding Receivables",
    "payables":          "Outstanding Payables",
    "stock":             "Stock Report",
    "invoice":           "Tax Invoice",
    "statement":         "Outstanding Statement"
}

class CanonicalExportEngine:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def fetch_report_data(self, slug: str, filters: dict) -> dict:
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        voucher_types = filters.get("voucher_types")
        party_name = filters.get("party_name")

        data = {}
        if slug in ("sales-register", "purchase-register", "receipt-register", "payment-register", "journal-register"):
            default_types = {
                "sales-register":    ["Sales", "Credit Note"],
                "purchase-register": ["Purchase", "Debit Note"],
                "receipt-register":  ["Receipt"],
                "payment-register":  ["Payment"],
                "journal-register":  ["Journal"],
            }[slug]
            vtype_list = [v.strip() for v in voucher_types.split(",")] if voucher_types else default_types
            q = _build_voucher_filters(self.db.query(Voucher), date_from, date_to, vtype_list, party_name, self.tenant_id)
            vouchers = q.order_by(Voucher.date.desc()).all()
            total = sum(v.amount or 0 for v in vouchers)
            data = {
                "total_amount": total,
                "total_count": len(vouchers),
                "tax_estimate": total * 0.18,
                "vouchers": [_voucher_to_dict(v) for v in vouchers],
            }

        elif slug == "cash-flow":
            inflows = _build_voucher_filters(self.db.query(Voucher), date_from, date_to, ["Receipt", "Sales"], None, self.tenant_id).order_by(Voucher.date.desc()).all()
            outflows = _build_voucher_filters(self.db.query(Voucher), date_from, date_to, ["Payment", "Purchase"], None, self.tenant_id).order_by(Voucher.date.desc()).all()
            ti = sum(v.amount or 0 for v in inflows)
            to = sum(v.amount or 0 for v in outflows)
            combined = [{**_voucher_to_dict(v), "direction": "inflow"} for v in inflows] + \
                       [{**_voucher_to_dict(v), "direction": "outflow"} for v in outflows]
            combined.sort(key=lambda x: x.get("date_iso", ""), reverse=True)
            data = {"total_inflow": ti, "total_outflow": to, "net_flow": ti - to, "vouchers": combined}

        elif slug == "balance-sheet":
            ledgers = self.db.query(Ledger).filter(Ledger.tenant_id == self.tenant_id).all()
            assets, liabilities = [], []
            ta, tl = 0.0, 0.0
            for l in ledgers:
                parent = (l.parent or "").lower()
                amount = l.closing_balance or 0.0
                if any(k in parent for k in ["asset", "cash", "bank", "debtor", "receivable"]):
                    assets.append({"name": l.name, "amount": abs(amount), "group": l.parent or "Other Assets"})
                    ta += abs(amount)
                elif any(k in parent for k in ["liabilit", "capital", "loan", "creditor", "payable"]):
                    liabilities.append({"name": l.name, "amount": abs(amount), "group": l.parent or "Other Liabilities"})
                    tl += abs(amount)
                else:
                    if amount >= 0:
                        assets.append({"name": l.name, "amount": amount, "group": "Other Assets"})
                        ta += amount
                    else:
                        liabilities.append({"name": l.name, "amount": abs(amount), "group": "Other Liabilities"})
                        tl += abs(amount)
            data = {"assets": sorted(assets, key=lambda x: x["amount"], reverse=True),
                    "liabilities": sorted(liabilities, key=lambda x: x["amount"], reverse=True),
                    "total_assets": ta, "total_liabilities": tl, "net_difference": ta - tl}

        elif slug == "profit-loss":
            sales_v = _build_voucher_filters(self.db.query(Voucher), date_from, date_to, ["Sales"], None, self.tenant_id).all()
            purchase_v = _build_voucher_filters(self.db.query(Voucher), date_from, date_to, ["Purchase"], None, self.tenant_id).all()
            ts = sum(v.amount or 0 for v in sales_v)
            tp = sum(v.amount or 0 for v in purchase_v)
            data = {"income": {"Sales Accounts": ts, "Direct Income": 0.0},
                    "expenses": {"Purchase Accounts": tp, "Direct Expenses": 0.0},
                    "total_income": ts, "total_expenses": tp, "net_profit": ts - tp}

        elif slug == "gst-summary":
            # gst-summary is basically empty if coming through here and handles properly in the template
            data = {"b2b": [], "b2c_large": [], "b2c_small": []}

        return data

    def generate_export_bytes(self, report_type: str, format: str, filters: dict, context: dict = None) -> dict:
        """
        Generates report bytes.
        Returns {"bytes": bytes, "filename": str, "mime_type": str}
        """
        title = _REPORT_TITLES.get(report_type, report_type.replace("-", " ").title())
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        d_from = _parse_date(date_from)
        d_to = _parse_date(date_to)
        if not d_from or not d_to:
            d_from, d_to = _default_fy_dates()
        period = f"{d_from.strftime('%d %b %Y')} \u2013 {d_to.strftime('%d %b %Y')}"
        date_str = datetime.now().strftime("%Y%m%d")

        # 1. Fetch data
        if report_type in ("invoice", "statement", "receivables", "payables", "stock"):
            # These slugs are delegated to ExportService legacy code wrapped in this engine
            from services.export_service import PDFGenerator, ExcelGenerator
            if format == "pdf" and report_type == "invoice":
                pdf_gen = PDFGenerator(self.db, self.tenant_id)
                voucher_id = filters.get("voucher_id")
                filepath, filename = pdf_gen.generate_invoice_pdf(voucher_id)
                with open(filepath, "rb") as f:
                    file_bytes = f.read()
                return {"bytes": file_bytes, "filename": filename, "mime_type": "application/pdf"}
            
            if format == "pdf" and report_type == "statement":
                pdf_gen = PDFGenerator(self.db, self.tenant_id)
                party_name = filters.get("party_name")
                filepath, filename = pdf_gen.generate_outstanding_statement(party_name)
                with open(filepath, "rb") as f:
                    file_bytes = f.read()
                return {"bytes": file_bytes, "filename": filename, "mime_type": "application/pdf"}
                
            if format == "excel" and report_type in ("receivables", "payables"):
                xl_gen = ExcelGenerator(self.db, self.tenant_id)
                t = "receivable" if report_type == "receivables" else "payable"
                filepath, filename = xl_gen.generate_outstanding_report(t)
                with open(filepath, "rb") as f:
                    file_bytes = f.read()
                return {"bytes": file_bytes, "filename": filename, "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
                
            if format == "excel" and report_type == "stock":
                xl_gen = ExcelGenerator(self.db, self.tenant_id)
                filepath, filename = xl_gen.generate_stock_report()
                with open(filepath, "rb") as f:
                    file_bytes = f.read()
                return {"bytes": file_bytes, "filename": filename, "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
        
        # 2. Standard canonical data fetch for others
        data = self.fetch_report_data(report_type, filters)
        
        if format == "pdf":
            filters_parts = []
            if filters.get("party_name"): filters_parts.append(f"Party: {filters.get('party_name')}")
            if filters.get("voucher_types"): filters_parts.append(f"Types: {filters.get('voucher_types')}")
            filters_desc = ", ".join(filters_parts) if filters_parts else "All records"

            pdf_bytes = generate_report_pdf(
                slug=report_type,
                report_title=title,
                data=data,
                period=period,
                date_from=date_from or "",
                date_to=date_to or "",
                filters_desc=filters_desc
            )
            filename = f"k24_{report_type.replace('-','_')}_{date_str}.pdf"
            return {"bytes": pdf_bytes, "filename": filename, "mime_type": "application/pdf"}
            
        elif format == "excel":
            if report_type == "gst-summary":
                _ci = {"name": "Your Company", "gstin": "", "pan": ""}
                excel_bytes = _tmpl_gst_excel(data, _ci, date_from or "", date_to or "")
            else:
                excel_bytes = generate_report_excel(report_type, title, data, period)
            filename = f"k24_{report_type.replace('-','_')}_{date_str}.xlsx"
            return {"bytes": excel_bytes, "filename": filename, "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
            
        raise ValueError(f"Unsupported format '{format}' for report '{report_type}'")

    def generate_export_file(self, report_type: str, format: str, filters: dict, context: dict = None) -> dict:
        """
        Generates report bytes and saves them to disk.
        Returns {"file_path": str, "filename": str, "mime_type": str}
        """
        result = self.generate_export_bytes(report_type, format, filters, context)
        exports_dir = get_exports_dir()
        file_path = exports_dir / result["filename"]
        
        with open(file_path, "wb") as f:
            f.write(result["bytes"])
            
        return {
            "file_path": str(file_path),
            "filename": result["filename"],
            "mime_type": result["mime_type"]
        }
