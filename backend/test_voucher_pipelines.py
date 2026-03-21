"""
test_voucher_pipelines.py
==========================
Direct pipeline test — NO HTTP endpoints, NO WhatsApp, NO UI.

Tests 4 voucher creation paths by calling the builders and Tally directly.

Usage (from repo root):
    python backend/test_voucher_pipelines.py

Usage (from backend/ folder):
    python test_voucher_pipelines.py

NOTE on GST ledger names
------------------------
Set GST_LEDGER_SALES / GST_LEDGER_PURCHASE below to the exact names of your
GST output/input ledgers in Tally (e.g. "Output GST @5%", "Input GST @5%").
Leave as None to skip GST lines — the test still validates the voucher path.
"""

import sys
import os
import io
import datetime
import requests
from decimal import Decimal
from contextlib import redirect_stdout

# ── Path fixup so the script can be run from backend/ or repo root ────────────
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(THIS_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# ══════════════════════════════════════════════════════════════════
# ► CONFIG — edit these to match your Tally setup
# ══════════════════════════════════════════════════════════════════
TALLY_URL      = os.getenv("TALLY_URL", "http://localhost:9000")
TALLY_TIMEOUT  = int(os.getenv("TALLY_TIMEOUT", "15"))

COMPANY        = "Krishasales"
PARTY          = "VINAYAK ENETRPRISES"   # Must exist in Tally as a ledger
ITEM           = "SOUNFF"                 # Must exist in Tally as a stock item
QTY            = 1.0
RATE           = 100.0
GST_PCT        = 5.0

# Set to None to skip GST lines; set to exact Tally ledger names to include them:
GST_LEDGER_SALES    = None   # e.g. "Output GST @5%"
GST_LEDGER_PURCHASE = None   # e.g. "Input GST @5%"

TODAY = datetime.date.today().strftime("%Y%m%d")
REF   = f"PIPE-TEST-{TODAY}"
# ══════════════════════════════════════════════════════════════════


# ── internal helpers ──────────────────────────────────────────────

def _gst_amount() -> float:
    return round(RATE * QTY * GST_PCT / 100, 2)


def _post_xml(xml_payload: str, label: str) -> tuple[bool, str]:
    """
    POST xml_payload to Tally.
    Returns (passed: bool, tally_raw_response: str).
    """
    print(f"  Sending {len(xml_payload):,} bytes to {TALLY_URL} …")
    try:
        resp = requests.post(
            TALLY_URL,
            data=xml_payload.encode("utf-8"),
            headers={"Content-Type": "text/xml;charset=UTF-8"},
            timeout=TALLY_TIMEOUT,
        )
        raw = resp.text
    except requests.exceptions.ConnectionError:
        msg = (f"Cannot connect to Tally at {TALLY_URL}\n"
               "  → Make sure Tally is open and the XML Server is enabled on port 9000.")
        return False, msg
    except Exception as exc:
        return False, f"Network error: {exc}"

    created    = "<CREATED>1</CREATED>"    in raw
    exceptions = ("<EXCEPTIONS>1</EXCEPTIONS>" in raw
                  or "<ERRORS>1</ERRORS>"    in raw
                  or "<LINEERROR>"          in raw)

    if created:
        return True, raw
    elif exceptions:
        return False, raw
    else:
        return False, f"Unknown Tally response:\n{raw}"


# ══════════════════════════════════════════════════════════════════
# TEST 1 — App Pipeline: SALES via GoldenXMLBuilder
# ══════════════════════════════════════════════════════════════════

def test_1_golden_sales() -> tuple[bool, str]:
    from backend.tally_golden_xml import GoldenXMLBuilder, VoucherData, InventoryItem, LedgerEntry

    gst_amt = _gst_amount()
    grand   = RATE * QTY + (gst_amt if GST_LEDGER_SALES else 0)

    ledger_entries = []
    if GST_LEDGER_SALES:
        ledger_entries.append(LedgerEntry(
            ledger_name=GST_LEDGER_SALES, amount=gst_amt,
            is_party=False, is_debit=False,
        ))

    data = VoucherData(
        company=COMPANY, voucher_type="Sales", date=TODAY, party_name=PARTY,
        voucher_number=f"S-TEST-{TODAY}", reference=REF,
        narration="Pipeline test — Sales via GoldenXMLBuilder",
        inventory_items=[InventoryItem(name=ITEM, quantity=QTY, rate=RATE,
                                       unit="Kgs", purchase_ledger="Sales Account")],
        ledger_entries=ledger_entries,
    )
    xml = GoldenXMLBuilder.build_sales_voucher(data)

    buf = io.StringIO()
    buf.write(f"  Item: ₹{RATE*QTY:.2f}  GST: ₹{gst_amt if GST_LEDGER_SALES else 0:.2f}  Total: ₹{grand:.2f}\n")
    if not GST_LEDGER_SALES:
        buf.write("  (GST_LEDGER_SALES not set — item-only voucher)\n")
    buf.write(f"  XML builder : GoldenXMLBuilder.build_sales_voucher()\n")
    buf.write(f"  SVCURRENTCOMPANY injected: {'YES' if 'SVCURRENTCOMPANY' in xml else 'NO — uses active company'}\n")

    passed, raw = _post_xml(xml, "TEST 1")
    buf.write(f"  Raw response snippet: {raw[:300]}\n")
    return passed, buf.getvalue()


# ══════════════════════════════════════════════════════════════════
# TEST 2 — App Pipeline: PURCHASE via GoldenXMLBuilder
# ══════════════════════════════════════════════════════════════════

def test_2_golden_purchase() -> tuple[bool, str]:
    from backend.tally_golden_xml import GoldenXMLBuilder, VoucherData, InventoryItem, LedgerEntry

    gst_amt = _gst_amount()
    grand   = RATE * QTY + (gst_amt if GST_LEDGER_PURCHASE else 0)

    ledger_entries = []
    if GST_LEDGER_PURCHASE:
        ledger_entries.append(LedgerEntry(
            ledger_name=GST_LEDGER_PURCHASE, amount=gst_amt,
            is_party=False, is_debit=True,
        ))

    data = VoucherData(
        company=COMPANY, voucher_type="Purchase", date=TODAY, party_name=PARTY,
        voucher_number=f"P-TEST-{TODAY}", reference=REF,
        narration="Pipeline test — Purchase via GoldenXMLBuilder",
        inventory_items=[InventoryItem(name=ITEM, quantity=QTY, rate=RATE,
                                       unit="Kgs", purchase_ledger="Purchase Account")],
        ledger_entries=ledger_entries,
    )
    xml = GoldenXMLBuilder.build_purchase_voucher(data)

    buf = io.StringIO()
    buf.write(f"  Item: ₹{RATE*QTY:.2f}  GST: ₹{gst_amt if GST_LEDGER_PURCHASE else 0:.2f}  Total: ₹{grand:.2f}\n")
    if not GST_LEDGER_PURCHASE:
        buf.write("  (GST_LEDGER_PURCHASE not set — item-only voucher)\n")
    buf.write(f"  XML builder : GoldenXMLBuilder.build_purchase_voucher()\n")
    buf.write(f"  SVCURRENTCOMPANY injected: {'YES' if 'SVCURRENTCOMPANY' in xml else 'NO — uses active company'}\n")

    passed, raw = _post_xml(xml, "TEST 2")
    buf.write(f"  Raw response snippet: {raw[:300]}\n")
    return passed, buf.getvalue()


# ══════════════════════════════════════════════════════════════════
# TEST 3 — WhatsApp Pipeline: SALES via build_invoice_xml
#
# KNOWN DIFFERENCE vs App pipeline
# ─────────────────────────────────
# tally_xml_builder._wrap_envelope() injects <SVCURRENTCOMPANY> in the XML.
# GoldenXMLBuilder deliberately omits it (lets Tally use the open company).
# Tally rejects the request with:
#   "Could not set 'SVCurrentCompany' to '<name>'"
# if the company is not currently open in Tally under that exact name.
#
# Also: tally_xml_builder.py defines InventoryEntry twice (bug):
#   • Line ~515: @dataclass with __init__
#   • Line ~545: plain class — no __init__ (shadows the dataclass)
# We work around this with _FakeInventoryEntry below.
# ══════════════════════════════════════════════════════════════════

def test_3_whatsapp_sales() -> tuple[bool, str]:
    from backend import tally_xml_builder as _txml

    class _FakeInventoryEntry:
        """Duck-type workaround for the double InventoryEntry definition bug."""
        def __init__(self, stock_item_name, rate, amount, actual_qty, billed_qty, ledger_name):
            self.stock_item_name = stock_item_name
            self.rate   = rate
            self.amount = Decimal(str(amount))
            self.actual_qty  = actual_qty
            self.billed_qty  = billed_qty
            self.ledger_name = ledger_name
            self.discount    = None

        def render(self, is_deemed_positive=False, indent="          "):
            return _txml.InventoryEntry.render(self, is_deemed_positive=is_deemed_positive, indent=indent)

    gst_amt    = _gst_amount()
    item_total = RATE * QTY
    grand      = item_total + (gst_amt if GST_LEDGER_SALES else 0)

    inv_items = [_FakeInventoryEntry(
        stock_item_name=ITEM, rate=f"{RATE:.2f}/Kgs", amount=item_total,
        actual_qty=f" {QTY:.2f} Kgs", billed_qty=f" {QTY:.2f} Kgs",
        ledger_name="Sales Account",
    )]

    vch_fields = {
        "DATE": TODAY, "VOUCHERTYPENAME": "Sales",
        "PARTYLEDGERNAME": PARTY, "PARTYNAME": PARTY,
        "NARRATION": "Pipeline test — Sales via WhatsApp builder",
        "REFERENCE": REF, "VOUCHERNUMBER": f"WA-S-{TODAY}",
    }

    extra_ledgers = []
    if GST_LEDGER_SALES:
        extra_ledgers.append({"ledger": GST_LEDGER_SALES, "amount": gst_amt, "is_debit": False})

    xml = _txml.build_invoice_xml(
        company_name=COMPANY, voucher_fields=vch_fields,
        inventory_items=inv_items, additional_ledgers=extra_ledgers,
    )

    buf = io.StringIO()
    buf.write(f"  Item: ₹{item_total:.2f}  GST: ₹{gst_amt if GST_LEDGER_SALES else 0:.2f}  Total: ₹{grand:.2f}\n")
    if not GST_LEDGER_SALES:
        buf.write("  (GST_LEDGER_SALES not set — item-only voucher)\n")
    buf.write(f"  XML builder : build_invoice_xml() from tally_xml_builder.py\n")

    has_svc = "SVCURRENTCOMPANY" in xml
    buf.write(f"  SVCURRENTCOMPANY injected: {'YES ← known issue' if has_svc else 'NO'}\n")
    if has_svc:
        buf.write(
            "  ⚠️  Pipeline difference: WhatsApp builder sends <SVCURRENTCOMPANY> but Tally\n"
            "     rejects it unless the company is open with that EXACT name.  App pipeline\n"
            "     (GoldenXMLBuilder) omits the tag — that's why TEST 1/2 pass and TEST 3/4 fail.\n"
            f"     Fix: remove SVCURRENTCOMPANY from _wrap_envelope() in tally_xml_builder.py\n"
        )

    passed, raw = _post_xml(xml, "TEST 3")
    buf.write(f"  Raw response snippet: {raw[:400]}\n")
    return passed, buf.getvalue()


# ══════════════════════════════════════════════════════════════════
# TEST 4 — WhatsApp Pipeline: PURCHASE via build_invoice_xml
# ══════════════════════════════════════════════════════════════════

def test_4_whatsapp_purchase() -> tuple[bool, str]:
    from backend import tally_xml_builder as _txml

    class _FakeInventoryEntry:
        def __init__(self, stock_item_name, rate, amount, actual_qty, billed_qty, ledger_name):
            self.stock_item_name = stock_item_name
            self.rate   = rate
            self.amount = Decimal(str(amount))
            self.actual_qty  = actual_qty
            self.billed_qty  = billed_qty
            self.ledger_name = ledger_name
            self.discount    = None

        def render(self, is_deemed_positive=False, indent="          "):
            return _txml.InventoryEntry.render(self, is_deemed_positive=is_deemed_positive, indent=indent)

    gst_amt    = _gst_amount()
    item_total = RATE * QTY
    grand      = item_total + (gst_amt if GST_LEDGER_PURCHASE else 0)

    inv_items = [_FakeInventoryEntry(
        stock_item_name=ITEM, rate=f"{RATE:.2f}/Kgs", amount=item_total,
        actual_qty=f" {QTY:.2f} Kgs", billed_qty=f" {QTY:.2f} Kgs",
        ledger_name="Purchase Account",
    )]

    vch_fields = {
        "DATE": TODAY, "VOUCHERTYPENAME": "Purchase",
        "PARTYLEDGERNAME": PARTY, "PARTYNAME": PARTY,
        "NARRATION": "Pipeline test — Purchase via WhatsApp builder",
        "REFERENCE": REF, "VOUCHERNUMBER": f"WA-P-{TODAY}",
    }

    extra_ledgers = []
    if GST_LEDGER_PURCHASE:
        extra_ledgers.append({"ledger": GST_LEDGER_PURCHASE, "amount": gst_amt, "is_debit": True})

    xml = _txml.build_invoice_xml(
        company_name=COMPANY, voucher_fields=vch_fields,
        inventory_items=inv_items, additional_ledgers=extra_ledgers,
    )

    buf = io.StringIO()
    buf.write(f"  Item: ₹{item_total:.2f}  GST: ₹{gst_amt if GST_LEDGER_PURCHASE else 0:.2f}  Total: ₹{grand:.2f}\n")
    if not GST_LEDGER_PURCHASE:
        buf.write("  (GST_LEDGER_PURCHASE not set — item-only voucher)\n")
    buf.write(f"  XML builder : build_invoice_xml() from tally_xml_builder.py\n")

    has_svc = "SVCURRENTCOMPANY" in xml
    buf.write(f"  SVCURRENTCOMPANY injected: {'YES ← known issue' if has_svc else 'NO'}\n")
    if has_svc:
        buf.write("  ⚠️  Same SVCURRENTCOMPANY issue as TEST 3 — see above.\n")

    passed, raw = _post_xml(xml, "TEST 4")
    buf.write(f"  Raw response snippet: {raw[:400]}\n")
    return passed, buf.getvalue()


# ══════════════════════════════════════════════════════════════════
# Entry point — run tests sequentially, print buffered results
# ══════════════════════════════════════════════════════════════════

TESTS = [
    ("TEST 1 — App Pipeline SALES    (GoldenXMLBuilder)",    test_1_golden_sales),
    ("TEST 2 — App Pipeline PURCHASE (GoldenXMLBuilder)",    test_2_golden_purchase),
    ("TEST 3 — WhatsApp SALES        (build_invoice_xml)",   test_3_whatsapp_sales),
    ("TEST 4 — WhatsApp PURCHASE     (build_invoice_xml)",   test_4_whatsapp_purchase),
]


if __name__ == "__main__":
    SEP = "=" * 66

    print(f"\n{SEP}")
    print("  VOUCHER PIPELINE TEST SUITE")
    print(f"  Tally URL   : {TALLY_URL}")
    print(f"  Company     : {COMPANY}")
    print(f"  Party       : {PARTY}")
    print(f"  Item        : {ITEM}  Qty={QTY}  Rate=₹{RATE}  GST={GST_PCT}%")
    print(f"  Date        : {TODAY}")
    print(f"  GST (Sales) : {GST_LEDGER_SALES or '— skipped'}")
    print(f"  GST (Purch) : {GST_LEDGER_PURCHASE or '— skipped'}")
    print(SEP)

    results: list[tuple[str, bool, str]] = []

    for name, fn in TESTS:
        print(f"\n{'-'*66}")
        print(f"  Running: {name}")
        print(f"{'-'*66}")
        try:
            passed, detail = fn()
        except Exception:
            import traceback
            tb = traceback.format_exc()
            passed, detail = False, f"Python exception:\n{tb}"
        results.append((name, passed, detail))
        icon = "✅ PASS" if passed else "❌ FAIL"
        print(f"\n  {icon}")
        print(detail)

    # ── Final summary ─────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  SUMMARY")
    print(SEP)
    passed_count = 0
    for name, ok, _ in results:
        icon = "✅" if ok else "❌"
        print(f"  {icon}  {name}")
        if ok:
            passed_count += 1
    print(f"\n  {passed_count}/{len(results)} tests passed.")

    if passed_count < len(results):
        print("\n  Known root-causes for failures:")
        print("  1. GST ledger names don't exist → set GST_LEDGER_SALES / GST_LEDGER_PURCHASE in the script")
        print("  2. WhatsApp pipeline (TEST 3/4) sends <SVCURRENTCOMPANY> → Tally rejects it")
        print("     Fix: remove SVCURRENTCOMPANY from _wrap_envelope() in tally_xml_builder.py")
        print("  3. InventoryEntry defined twice in tally_xml_builder.py (bug) → handled via _FakeInventoryEntry")

    print(SEP + "\n")
