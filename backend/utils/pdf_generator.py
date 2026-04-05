"""
K24 ERP — Tally-Style Report PDF Generator
Inspired by: Indian CA / Tally ERP9 print format
Style: Portrait A4, white background, thin black ruled lines,
       centered title, grid-style company/doc info, hairline table borders,
       italic tax rows, amount-in-words + signature footer.
"""
from __future__ import annotations

import io
import calendar
import random
from datetime import date as Date, datetime
from typing import Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas

W, H = A4   # 595.28 × 841.89 pt

# ─── COLOUR PALETTE (Tally-style: black ink on white) ─────────────────────────
INK     = colors.HexColor("#1A1A1A")   # near-black for all text
SUBTEXT = colors.HexColor("#555555")   # slightly lighter for labels
BORDER  = colors.HexColor("#333333")   # hairline borders
GRID    = colors.HexColor("#888888")   # lighter internal grid lines
ROW_ALT = colors.HexColor("#F8F8F8")   # very subtle alternating row
WHITE   = colors.white
K24TXT  = colors.HexColor("#AAAAAA")   # "Powered by K24" watermark

# ─── LAYOUT ───────────────────────────────────────────────────────────────────
LM        = 12 * mm
RM        = W - 12 * mm
TM        = H - 10 * mm
BM        = 10 * mm
CW        = RM - LM          # content width ≈ 183 pt  (~64.6 mm each third)


# ──────────────────────────────────────────────────────────────────────────────
# PRIMITIVES
# ──────────────────────────────────────────────────────────────────────────────
def _hl(c, x1, y, x2, lw=0.4, color=BORDER):
    c.setStrokeColor(color)
    c.setLineWidth(lw)
    c.line(x1, y, x2, y)

def _vl(c, x, y1, y2, lw=0.4, color=BORDER):
    c.setStrokeColor(color)
    c.setLineWidth(lw)
    c.line(x, y1, x, y2)

def _rect(c, x, y, w, h, lw=0.5, fill=None):
    if fill:
        c.setFillColor(fill)
        c.rect(x, y, w, h, fill=1, stroke=0)
    c.setStrokeColor(BORDER)
    c.setLineWidth(lw)
    c.rect(x, y, w, h, fill=0, stroke=1)

def _t(c, txt, x, y, font="Helvetica", sz=8, color=INK, align="left"):
    c.setFont(font, sz)
    c.setFillColor(color)
    s = str(txt)
    if align == "right":   c.drawRightString(x, y, s)
    elif align == "center": c.drawCentredString(x, y, s)
    else:                   c.drawString(x, y, s)

def _fmt(val) -> str:
    try:
        n = float(val)
        return f"\u20b9 {abs(n):,.2f}" if n >= 0 else f"(\u20b9 {abs(n):,.2f})"
    except (TypeError, ValueError):
        return str(val) if val else "\u2014"


# ──────────────────────────────────────────────────────────────────────────────
# QR PLACEHOLDER (Tally-style: top-right corner)
# ──────────────────────────────────────────────────────────────────────────────
def _qr(c, x, y, size):
    _rect(c, x, y, size, size, lw=0.5)
    cell = size / 10
    random.seed(99)

    # Corner finder squares
    for (cx, cy) in [(0, 7), (7, 7), (0, 0)]:
        # Outer dark
        c.setFillColor(INK)
        c.rect(x + cx*cell, y + cy*cell, 3*cell, 3*cell, fill=1, stroke=0)
        # Inner white
        c.setFillColor(WHITE)
        c.rect(x+(cx+0.5)*cell, y+(cy+0.5)*cell, 2*cell, 2*cell, fill=1, stroke=0)
        # Centre dark
        c.setFillColor(INK)
        c.rect(x+(cx+1)*cell, y+(cy+1)*cell, cell, cell, fill=1, stroke=0)

    # Data dots
    c.setFillColor(INK)
    for i in range(10):
        for j in range(10):
            skip = ((i < 3 and j > 6) or (i > 6 and j > 6) or (i < 3 and j < 3))
            if not skip and random.random() > 0.5:
                c.rect(x + i*cell, y + j*cell, cell*0.75, cell*0.75, fill=1, stroke=0)


# ──────────────────────────────────────────────────────────────────────────────
# WATERMARK — diagonal "K24" stamp on every page
# ──────────────────────────────────────────────────────────────────────────────
def _watermark(c):
    """K24 brand mark — bottom-left corner of every page."""
    c.saveState()
    c.setFillColor(colors.HexColor("#BBBBBB"))
    c.setFillAlpha(0.30)                  # subtle but legible
    c.setFont("Helvetica-Bold", 28)
    c.drawString(LM, BM + 1*mm, "K24")   # sits just above bottom margin
    c.restoreState()


# ──────────────────────────────────────────────────────────────────────────────
# HEADER — Tally style: title centred, e-Invoice tag, QR top-right
# ──────────────────────────────────────────────────────────────────────────────
def _header(c, report_title: str, company: dict, meta: dict) -> float:
    """Returns bottom y of header section."""
    top = TM

    # ── Top border rule ──
    _hl(c, LM, top, RM, lw=0.8)

    # ── Centred title ──
    _t(c, report_title, W / 2, top - 6*mm, "Helvetica-Bold", 11, INK, "center")
    _t(c, "K24 Intelligence ERP", RM, top - 6*mm, "Helvetica", 7.5, SUBTEXT, "right")

    # ── QR code (top right, below title) ──
    qr_size = 20*mm
    qr_x = RM - qr_size
    qr_y = top - 7*mm - qr_size
    _qr(c, qr_x, qr_y, qr_size)
    _t(c, "Scan to verify", qr_x + qr_size/2, qr_y - 3.5*mm, "Helvetica", 5.5, SUBTEXT, "center")

    # ── Company info (left of QR) ──
    cy = top - 13*mm
    _t(c, company.get("name", "Your Company"), LM, cy, "Helvetica-Bold", 9.5, INK)
    cy -= 4.5*mm
    for line in company.get("address_lines", []):
        _t(c, line, LM, cy, "Helvetica", 7.5, SUBTEXT)
        cy -= 3.8*mm
    for lbl, key in [("GSTIN/UIN", "gstin"), ("PAN", "pan")]:
        val = company.get(key, "")
        if val:
            _t(c, f"{lbl} : {val}", LM, cy, "Helvetica", 7.5, SUBTEXT)
            cy -= 3.8*mm

    # ── Meta info grid (centre column — to left of QR) ──
    mx = W / 2
    my = top - 13*mm
    meta_rows = [
        ("Period",     meta.get("period", "")),
        ("Generated",  meta.get("generated", "")),
        ("Filters",    meta.get("filters", "All records")),
        ("Records",    meta.get("records", "")),
    ]
    for lbl, val in meta_rows:
        if val:
            _t(c, lbl, mx, my, "Helvetica", 7.5, SUBTEXT)
            _t(c, val, mx + 22*mm, my, "Helvetica-Bold", 7.5, INK)
            my -= 4*mm

    # ── Horizontal divider under header area ──
    header_bottom = min(cy, my, qr_y - 4*mm) - 3*mm
    _hl(c, LM, header_bottom, RM, lw=0.6)
    return header_bottom


# ──────────────────────────────────────────────────────────────────────────────
# KPI INFO STRIP — like Tally's invoice metadata row
# ──────────────────────────────────────────────────────────────────────────────
def _kpi_strip(c, y: float, kpis: list[tuple[str, str]]) -> float:
    """Horizontal strip with labelled KPI values separated by thin vertical lines."""
    if not kpis:
        return y - 2*mm
    strip_h = 12*mm
    top = y - 2*mm
    box_w = CW / len(kpis)

    # Outer rect
    _rect(c, LM, top - strip_h, CW, strip_h, lw=0.4)

    for i, (lbl, val) in enumerate(kpis):
        bx = LM + i * box_w
        _t(c, lbl, bx + 3*mm, top - 4.5*mm, "Helvetica", 6.5, SUBTEXT)
        _t(c, val, bx + 3*mm, top - 9.5*mm, "Helvetica-Bold", 8.5, INK)
        if i > 0:
            _vl(c, bx, top - strip_h + 1*mm, top - 1*mm, lw=0.4, color=GRID)

    return top - strip_h - 2*mm


# ──────────────────────────────────────────────────────────────────────────────
# DATA TABLE — Tally style: hairline borders, no dark fills, bold header row
# ──────────────────────────────────────────────────────────────────────────────
def _table(c, y: float, columns: list[dict], rows: list[list]) -> float:
    """
    Tally-style table: thin outer border, column dividers,
    bold header row (no fill), alternating very-light-gray rows.
    Returns bottom y.
    """
    top   = y - 2*mm
    hdr_h = 8.5*mm
    row_h = 7.5*mm

    # x positions
    xs = [LM]
    for col in columns:
        xs.append(xs[-1] + col["width_mm"] * mm)

    # ── Header row ──
    # Light gray fill for header only
    c.setFillColor(colors.HexColor("#EFEFEF"))
    c.rect(LM, top - hdr_h, CW, hdr_h, fill=1, stroke=0)
    _hl(c, LM, top, RM, lw=0.5)
    _hl(c, LM, top - hdr_h, RM, lw=0.5)

    for i, col in enumerate(columns):
        cx, nxt = xs[i], xs[i+1]
        cw = nxt - cx
        mid = cx + cw / 2
        lbl = col["label"]
        fn = "Helvetica-Bold"
        sz = 7
        if col["align"] == "right":
            _t(c, lbl, nxt - 2*mm, top - 6*mm, fn, sz, INK, "right")
        elif col["align"] == "center":
            _t(c, lbl, mid, top - 6*mm, fn, sz, INK, "center")
        else:
            _t(c, lbl, cx + 2*mm, top - 6*mm, fn, sz, INK)

    cur_y = top - hdr_h

    # ── Data rows ──
    for ri, row in enumerate(rows):
        # thin alternating row
        if ri % 2 == 1:
            c.setFillColor(ROW_ALT)
            c.rect(LM, cur_y - row_h, CW, row_h, fill=1, stroke=0)

        _hl(c, LM, cur_y - row_h, RM, lw=0.3, color=GRID)

        for ci, col in enumerate(columns):
            cx, nxt = xs[ci], xs[ci+1]
            cw = nxt - cx
            val = str(row[ci]) if ci < len(row) else ""
            ty  = cur_y - 5.2*mm
            # Bold for 2nd column (description/party name)
            fn = "Helvetica-Bold" if ci == 1 else "Helvetica"
            sz = 7.5
            if col["align"] == "right":
                _t(c, val, nxt - 2*mm, ty, fn, sz, INK, "right")
            elif col["align"] == "center":
                _t(c, val, cx + cw/2, ty, fn, sz, INK, "center")
            else:
                _t(c, val, cx + 2*mm, ty, fn, sz, INK)

        cur_y -= row_h

    # ── Outer border + column dividers ──
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.rect(LM, cur_y, CW, top - cur_y, fill=0, stroke=1)
    for xi in xs[1:-1]:
        _vl(c, xi, cur_y, top, lw=0.3, color=GRID)

    return cur_y


# ──────────────────────────────────────────────────────────────────────────────
# TOTALS — Tally style: right-aligned italic summary rows below table
# ──────────────────────────────────────────────────────────────────────────────
def _totals(c, y: float, totals: list[tuple[str, str, bool]]) -> float:
    """
    Tally-style totals: slim rows right-aligned, italic labels,
    grand total in bold with a heavier rule above.
    """
    if not totals:
        return y
    row_h  = 5*mm
    box_w  = CW * 0.38
    box_x  = RM - box_w
    cur_y  = y

    # Light outer rect
    _rect(c, box_x, cur_y - row_h * len(totals) - 1*mm, box_w, row_h * len(totals) + 1*mm, lw=0.4)

    for lbl, val, is_grand in totals:
        if is_grand:
            # Heavy rule before grand total
            _hl(c, box_x, cur_y, RM, lw=0.7, color=BORDER)
            # Light fill
            c.setFillColor(colors.HexColor("#EFEFEF"))
            c.rect(box_x, cur_y - row_h, box_w, row_h, fill=1, stroke=0)
            _t(c, lbl, box_x + 3*mm, cur_y - 3.6*mm, "Helvetica-Bold", 8.5, INK)
            _t(c, val, RM - 3*mm, cur_y - 3.6*mm, "Helvetica-Bold", 8.5, INK, "right")
        else:
            _hl(c, box_x, cur_y - row_h, RM, lw=0.3, color=GRID)
            _t(c, lbl, box_x + 3*mm, cur_y - 3.8*mm, "Helvetica-Oblique", 7, SUBTEXT)
            _t(c, val, RM - 3*mm, cur_y - 3.8*mm, "Helvetica-Bold", 7.5, INK, "right")
        cur_y -= row_h

    return cur_y - 3*mm


# ──────────────────────────────────────────────────────────────────────────────
# FOOTER — Tally: "This is a Computer Generated Report" + page
# ──────────────────────────────────────────────────────────────────────────────
def _footer(c, page: int = 1, total_pages: int = 1):
    fy = BM + 9*mm
    _hl(c, LM, fy, RM, lw=0.6)
    _t(c, "This is a Computer Generated Report",
       W/2, fy - 4*mm, "Helvetica", 7, SUBTEXT, "center")
    _t(c, f"Page {page} of {total_pages}",
       RM, fy - 4*mm, "Helvetica", 7, SUBTEXT, "right")
    _t(c, "Powered by K24  \u00b7  k24.ai",
       LM, fy - 4*mm, "Helvetica", 7, K24TXT)


# ──────────────────────────────────────────────────────────────────────────────
# REPORT COLUMN CONFIGS  (portrait, total CW ≈ 171 mm = 484 pt)
# ──────────────────────────────────────────────────────────────────────────────
# CW = W - 24mm = 595.28 - 68 ≈ 527 pt → / mm = ~186 mm
# Using 186 mm as content width

REPORT_COLUMN_CONFIGS: dict[str, list[dict]] = {
    "sales-register": [
        {"label": "Sl\nNo.", "width_mm": 8,  "align": "center"},
        {"label": "Party Name",    "width_mm": 54, "align": "left"},
        {"label": "Date",          "width_mm": 20, "align": "center"},
        {"label": "Voucher Type",  "width_mm": 24, "align": "left"},
        {"label": "Ref. No.",      "width_mm": 22, "align": "center"},
        {"label": "Narration",     "width_mm": 34, "align": "left"},
        {"label": "Amount",        "width_mm": 24, "align": "right"},
    ],  # 8+54+20+24+22+34+24 = 186

    "purchase-register": [
        {"label": "Sl\nNo.", "width_mm": 8,  "align": "center"},
        {"label": "Party Name",    "width_mm": 54, "align": "left"},
        {"label": "Date",          "width_mm": 20, "align": "center"},
        {"label": "Voucher Type",  "width_mm": 24, "align": "left"},
        {"label": "Ref. No.",      "width_mm": 22, "align": "center"},
        {"label": "Narration",     "width_mm": 34, "align": "left"},
        {"label": "Amount",        "width_mm": 24, "align": "right"},
    ],  # 186

    "receipt-register": [
        {"label": "Sl\nNo.", "width_mm": 8,  "align": "center"},
        {"label": "Party Name",    "width_mm": 60, "align": "left"},
        {"label": "Date",          "width_mm": 20, "align": "center"},
        {"label": "Ref. No.",      "width_mm": 24, "align": "center"},
        {"label": "Narration",     "width_mm": 50, "align": "left"},
        {"label": "Amount",        "width_mm": 24, "align": "right"},
    ],  # 8+60+20+24+50+24 = 186

    "payment-register": [
        {"label": "Sl\nNo.", "width_mm": 8,  "align": "center"},
        {"label": "Party Name",    "width_mm": 60, "align": "left"},
        {"label": "Date",          "width_mm": 20, "align": "center"},
        {"label": "Ref. No.",      "width_mm": 24, "align": "center"},
        {"label": "Narration",     "width_mm": 50, "align": "left"},
        {"label": "Amount",        "width_mm": 24, "align": "right"},
    ],  # 186

    "journal-register": [
        {"label": "Sl\nNo.", "width_mm": 8,  "align": "center"},
        {"label": "Party Name",   "width_mm": 52, "align": "left"},
        {"label": "Date",         "width_mm": 20, "align": "center"},
        {"label": "Ref. No.",     "width_mm": 22, "align": "center"},
        {"label": "Debit (₹)",    "width_mm": 28, "align": "right"},
        {"label": "Credit (₹)",   "width_mm": 28, "align": "right"},
        {"label": "Narration",    "width_mm": 28, "align": "left"},
    ],  # 8+52+20+22+28+28+28 = 186

    "cash-flow": [
        {"label": "Sl\nNo.", "width_mm": 8,  "align": "center"},
        {"label": "Party Name",   "width_mm": 50, "align": "left"},
        {"label": "Date",         "width_mm": 20, "align": "center"},
        {"label": "Voucher Type", "width_mm": 24, "align": "left"},
        {"label": "Ref. No.",     "width_mm": 22, "align": "center"},
        {"label": "Direction",    "width_mm": 20, "align": "center"},
        {"label": "Narration",    "width_mm": 18, "align": "left"},
        {"label": "Amount",       "width_mm": 24, "align": "right"},
    ],  # 8+50+20+24+22+20+18+24 = 186

    "balance-sheet": [
        {"label": "Sl\nNo.", "width_mm": 8,  "align": "center"},
        {"label": "Ledger Name",  "width_mm": 80, "align": "left"},
        {"label": "Group",        "width_mm": 58, "align": "left"},
        {"label": "Category",     "width_mm": 22, "align": "center"},
        {"label": "Amount",       "width_mm": 18, "align": "right"},
    ],  # 8+80+58+22+18 = 186

    "profit-loss": [
        {"label": "Sl\nNo.", "width_mm": 8,  "align": "center"},
        {"label": "Account Head", "width_mm": 104, "align": "left"},
        {"label": "Category",     "width_mm":  40, "align": "center"},
        {"label": "Amount",       "width_mm":  34, "align": "right"},
    ],  # 8+104+40+34 = 186
}

_GENERIC_COLS = [
    {"label": "Sl\nNo.", "width_mm": 8,  "align": "center"},
    {"label": "Party Name",  "width_mm": 60, "align": "left"},
    {"label": "Date",        "width_mm": 22, "align": "center"},
    {"label": "Type",        "width_mm": 28, "align": "left"},
    {"label": "Ref. No.",    "width_mm": 24, "align": "center"},
    {"label": "Amount",      "width_mm": 44, "align": "right"},
]  # 8+60+22+28+24+44 = 186


# ──────────────────────────────────────────────────────────────────────────────
# ROW CONVERTERS
# ──────────────────────────────────────────────────────────────────────────────
def _voucher_row(idx: int, v: dict, slug: str) -> list[str]:
    amt   = _fmt(v.get("amount", 0))
    narr  = (v.get("narration") or "")[:32]
    party = v.get("party_name", "\u2014") or "\u2014"
    vno   = v.get("voucher_no", "\u2014") or "\u2014"
    vtype = v.get("voucher_type", "") or ""
    dt    = v.get("date", "") or ""

    if slug in ("receipt-register", "payment-register"):
        return [str(idx), party, dt, vno, narr, amt]

    if slug == "cash-flow":
        direction = "\u2191 In" if v.get("direction") == "inflow" else "\u2193 Out"
        return [str(idx), party, dt, vtype, vno, direction, narr, amt]

    if slug == "journal-register":
        is_dr = v.get("direction") == "debit"
        return [str(idx), party, dt, vno,
                amt if is_dr else "\u2014",
                amt if not is_dr else "\u2014",
                narr]

    # sales, purchase, generic
    return [str(idx), party, dt, vtype, vno, narr, amt]


def _bs_rows(data: dict) -> list[list[str]]:
    rows, i = [], 1
    for item in data.get("assets", []):
        rows.append([str(i), item["name"], item.get("group", ""), "Asset",
                     _fmt(item["amount"])])
        i += 1
    for item in data.get("liabilities", []):
        rows.append([str(i), item["name"], item.get("group", ""), "Liability",
                     _fmt(item["amount"])])
        i += 1
    return rows


def _pl_rows(data: dict) -> list[list[str]]:
    rows, i = [], 1
    for k, v in data.get("income", {}).items():
        rows.append([str(i), k, "Income", _fmt(v)]); i += 1
    for k, v in data.get("expenses", {}).items():
        rows.append([str(i), k, "Expense", _fmt(v)]); i += 1
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# KPI + TOTALS per slug
# ──────────────────────────────────────────────────────────────────────────────
def _get_kpis(slug: str, data: dict) -> list[tuple[str, str]]:
    if slug == "sales-register":
        return [
            ("Total Sales",   _fmt(data.get("total_amount", 0))),
            ("Transactions",  str(data.get("total_count", 0))),
            ("Est. GST 18%",  _fmt(data.get("tax_estimate", 0))),
        ]
    if slug == "purchase-register":
        return [
            ("Total Purchases", _fmt(data.get("total_amount", 0))),
            ("Transactions",    str(data.get("total_count", 0))),
        ]
    if slug == "cash-flow":
        return [
            ("Inflow",       _fmt(data.get("total_inflow", 0))),
            ("Outflow",      _fmt(data.get("total_outflow", 0))),
            ("Net Cash Flow",_fmt(data.get("net_flow", 0))),
        ]
    if slug in ("receipt-register", "payment-register"):
        label = "Total Receipts" if slug == "receipt-register" else "Total Payments"
        return [(label, _fmt(data.get("total_amount", 0))),
                ("Transactions", str(data.get("total_count", 0)))]
    if slug == "balance-sheet":
        return [
            ("Total Assets",      _fmt(data.get("total_assets", 0))),
            ("Total Liabilities", _fmt(data.get("total_liabilities", 0))),
            ("Net Difference",    _fmt(data.get("net_difference", 0))),
        ]
    if slug == "profit-loss":
        return [
            ("Total Income",   _fmt(data.get("total_income", 0))),
            ("Total Expenses", _fmt(data.get("total_expenses", 0))),
            ("Net Profit",     _fmt(data.get("net_profit", 0))),
        ]
    return []


def _get_totals(slug: str, data: dict) -> list[tuple[str, str, bool]]:
    if slug == "sales-register":
        return [
            ("Subtotal",       _fmt(data.get("total_amount", 0)), False),
            ("Est. GST @ 18%", _fmt(data.get("tax_estimate", 0)), False),
            ("GRAND TOTAL",    _fmt(data.get("total_amount", 0)), True),
        ]
    if slug == "purchase-register":
        return [
            ("Total Purchases", _fmt(data.get("total_amount", 0)), False),
            ("GRAND TOTAL",     _fmt(data.get("total_amount", 0)), True),
        ]
    if slug == "cash-flow":
        return [
            ("Total Inflow",   _fmt(data.get("total_inflow", 0)),  False),
            ("Total Outflow",  _fmt(data.get("total_outflow", 0)), False),
            ("NET CASH FLOW",  _fmt(data.get("net_flow", 0)),      True),
        ]
    if slug in ("receipt-register", "payment-register"):
        lbl = "TOTAL RECEIPTS" if slug == "receipt-register" else "TOTAL PAYMENTS"
        return [(lbl, _fmt(data.get("total_amount", 0)), True)]
    if slug == "balance-sheet":
        return [
            ("Total Assets",      _fmt(data.get("total_assets", 0)),      False),
            ("Total Liabilities", _fmt(data.get("total_liabilities", 0)), False),
            ("NET DIFFERENCE",    _fmt(data.get("net_difference", 0)),     True),
        ]
    if slug == "profit-loss":
        return [
            ("Total Income",   _fmt(data.get("total_income", 0)),   False),
            ("Total Expenses", _fmt(data.get("total_expenses", 0)), False),
            ("NET PROFIT / LOSS", _fmt(data.get("net_profit", 0)),  True),
        ]
    return []


# ──────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────
_ROWS_PER_PAGE_FIRST  = 26   # fewer on page 1 (header takes space)
_ROWS_PER_PAGE_OTHER  = 33   # more on subsequent pages


def generate_report_pdf(
    slug: str,
    report_title: str,
    data: dict,
    period: str,
    company: Optional[dict] = None,
    date_from: str = "",
    date_to: str = "",
    filters_desc: str = "All records",
) -> bytes:
    """Generate a Tally-style report PDF. Returns raw bytes."""
    if company is None:
        company = {"name": "Your Company", "address_lines": [], "gstin": "", "pan": ""}

    # ── Delegate to world-class templates where available ──────────────────────
    _TEMPLATE_SLUGS = {"balance-sheet", "profit-loss", "gst-summary",
                       "ledger-statement", "aging"}
    if slug in _TEMPLATE_SLUGS:
        from utils.report_template import (
            generate_balance_sheet_pdf   as _tmpl_bs,
            generate_profit_loss_pdf     as _tmpl_pl,
            generate_gst_summary_pdf     as _tmpl_gst,
            generate_ledger_pdf          as _tmpl_ledger,
            generate_aging_pdf           as _tmpl_aging,
        )
        _ci = {
            "name":    company.get("name", "Your Company"),
            "address": "\n".join(company.get("address_lines", [])),
            "gstin":   company.get("gstin", ""),
            "pan":     company.get("pan", ""),
        }
        # Resolve date_from / date_to from period string when not supplied
        _df = date_from
        _dt = date_to
        if not _df and "\u2013" in period:
            parts = period.split("\u2013")
            _df, _dt = parts[0].strip(), parts[-1].strip()
        elif not _df and "\u2014" in period:
            parts = period.split("\u2014")
            _df, _dt = parts[0].strip(), parts[-1].strip()

        if slug == "balance-sheet":
            return _tmpl_bs(data, _ci, _df, _dt)
        if slug == "profit-loss":
            return _tmpl_pl(data, _ci, _df, _dt)
        if slug == "gst-summary":
            return _tmpl_gst(data, _ci, _df, _dt)
        if slug == "ledger-statement":
            return _tmpl_ledger(data, _ci, _df, _dt)
        if slug == "aging":
            return _tmpl_aging(data, _ci, _df, _dt)
    # ─────────────────────────────────────────────────────────────────────────

    # ── Build all rows ──
    columns = REPORT_COLUMN_CONFIGS.get(slug, _GENERIC_COLS)

    if slug in ("sales-register", "purchase-register", "cash-flow",
                "receipt-register", "payment-register", "journal-register"):
        vouchers = data.get("vouchers", [])
        all_rows = [_voucher_row(i + 1, v, slug) for i, v in enumerate(vouchers)]
    elif slug == "balance-sheet":
        all_rows = _bs_rows(data)
    elif slug == "profit-loss":
        all_rows = _pl_rows(data)
    else:
        vouchers = data.get("vouchers", [])
        all_rows = [_voucher_row(i + 1, v, slug) for i, v in enumerate(vouchers)]

    # Paginate
    pages: list[list] = []
    remaining = list(all_rows)
    first_chunk = remaining[:_ROWS_PER_PAGE_FIRST]
    remaining   = remaining[_ROWS_PER_PAGE_FIRST:]
    pages.append(first_chunk)
    while remaining:
        pages.append(remaining[:_ROWS_PER_PAGE_OTHER])
        remaining = remaining[_ROWS_PER_PAGE_OTHER:]
    if not pages:
        pages = [[]]

    total_pages = len(pages)
    kpis   = _get_kpis(slug, data)
    totals = _get_totals(slug, data)
    now    = datetime.now().strftime("%d-%b-%Y %I:%M %p")

    buf = io.BytesIO()
    c   = rl_canvas.Canvas(buf, pagesize=A4)

    for page_num, page_rows in enumerate(pages, 1):
        meta = {
            "period":    period,
            "generated": now,
            "filters":   filters_desc,
            "records":   f"{len(all_rows)} entries",
        }
        y = _header(c, report_title, company, meta)

        if page_num == 1:
            y = _kpi_strip(c, y, kpis)
        else:
            y -= 3*mm   # small gap before table on inner pages

        y = _table(c, y, columns, page_rows)

        if page_num == total_pages:
            _totals(c, y, totals)

        _watermark(c)
        _footer(c, page_num, total_pages)

        if page_num < total_pages:
            c.showPage()

    c.save()
    buf.seek(0)
    return buf.read()
