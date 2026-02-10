"""
K24 Indian Compliance - Validation Rules
=========================================
21+ India-specific tax and regulatory validation rules for SMBs.
"""

from typing import Tuple, Optional, Dict, Any
from datetime import date, datetime, timedelta
from backend.database import SessionLocal, Voucher, Ledger
import logging

logger = logging.getLogger(__name__)

# Severity levels
SEVERITY_BLOCK = "BLOCK"
SEVERITY_WARN = "WARN"
SEVERITY_INFO = "INFO"

# GST thresholds (2025)
GST_THRESHOLD_GOODS = 40_00_000  # ₹40 lakhs
GST_THRESHOLD_SERVICES = 20_00_000  # ₹20 lakhs
GST_THRESHOLD_SPECIAL_STATES = 20_00_000  # ₹20 lakhs for NE states

# Valid GST rates in India
VALID_GST_RATES = [0.0, 5.0, 12.0, 18.0, 28.0]

def rule_gst_registration_required(turnover: float, business_type: str = "GOODS") -> Tuple[bool, str, str, str]:
    """
    RULE 1: Check if GST registration is required based on turnover threshold.
    
    Args:
        turnover: Annual turnover in INR
        business_type: "GOODS" or "SERVICES"
        
    Returns:
        (is_valid, severity, message, action)
    """
    threshold = GST_THRESHOLD_GOODS if business_type == "GOODS" else GST_THRESHOLD_SERVICES
    
    if turnover > threshold:
        return (
            False,
            SEVERITY_WARN,
            f"Your turnover (₹{turnover/100000:.1f}L) exceeds ₹{threshold/100000:.0f}L threshold. GST registration required.",
            "Register for GST immediately to avoid penalties"
        )
    
    # Close to threshold (80%)
    if turnover > threshold * 0.8:
        return (
            True,
            SEVERITY_INFO,
            f"Your turnover (₹{turnover/100000:.1f}L) is approaching ₹{threshold/100000:.0f}L GST threshold.",
            "Plan for GST registration soon"
        )
    
    return (True, SEVERITY_INFO, "GST registration not yet required", "")

def rule_gst_rate_validity_india(gst_rate: float, item_type: Optional[str] = None) -> Tuple[bool, str, str, str]:
    """
    RULE 2: Validate GST rate is a valid Indian GST slab.
    
    Args:
        gst_rate: GST rate percentage
        item_type: Type of item (FOOD, MEDICINE, SERVICE, LUXURY)
        
    Returns:
        (is_valid, severity, message, action)
    """
    if gst_rate not in VALID_GST_RATES:
        return (
            False,
            SEVERITY_BLOCK,
            f"Invalid GST rate {gst_rate}%. Valid rates: 0%, 5%, 12%, 18%, 28%",
            "Use a valid GST slab"
        )
    
    # Check item-specific rates
    if item_type:
        item_type = item_type.upper()
        if item_type == "MEDICINE" and gst_rate != 0.0:
            return (False, SEVERITY_WARN, "Medicines are typically 0% GST", "Verify rate with CA")
        if item_type == "FOOD" and gst_rate > 5.0:
            return (False, SEVERITY_WARN, "Food items are typically 0% or 5% GST", "Verify rate")
        if item_type == "LUXURY" and gst_rate != 28.0:
            return (False, SEVERITY_WARN, "Luxury items are typically 28% GST", "Verify rate")
    
    return (True, SEVERITY_INFO, f"Valid GST rate: {gst_rate}%", "")

def rule_reverse_charge_applicable(amount: float, supplier_gstin: Optional[str]) -> Tuple[bool, str, str, str]:
    """
    RULE 3: Check if Reverse Charge Mechanism (RCM) applies.
    
    Args:
        amount: Transaction amount
        supplier_gstin: Supplier's GSTIN (None if unregistered)
        
    Returns:
        (is_valid, severity, message, action)
    """
    # RCM applies if buying from unregistered supplier and amount > ₹5,000 in a day
    if supplier_gstin is None and amount > 5000:
        rcm_gst = amount * 0.18  # Assuming 18% standard rate
        return (
            True,
            SEVERITY_WARN,
            f"Reverse Charge applies. You must pay ₹{rcm_gst:,.0f} GST (18% RCM) on ₹{amount:,.0f} purchase.",
            "Pay GST to government (not supplier) and claim ITC"
        )
    
    return (True, SEVERITY_INFO, "Reverse charge not applicable", "")

def rule_tds_contractor_payment(amount: float, payment_type: str, aggregate_annual: float = 0) -> Tuple[bool, str, str, str]:
    """
    RULE 4: Check if TDS is applicable on contractor/professional payments.
    
    Args:
        amount: Payment amount
        payment_type: "CONTRACTOR" or "PROFESSIONAL"
        aggregate_annual: Aggregate annual payment to same party
        
    Returns:
        (is_valid, severity, message, action)
    """
    threshold_single = 30_000
    threshold_annual = 1_00_000
    
    # Check if TDS applicable
    if payment_type == "CONTRACTOR" and (amount > threshold_single or aggregate_annual > threshold_annual):
        tds_amount = amount * 0.01  # 1% for contractors (Section 194C)
        return (
            True,
            SEVERITY_WARN,
            f"TDS applicable: Deduct ₹{tds_amount:,.0f} (1% of ₹{amount:,.0f}) under Section 194C",
            "Deduct TDS and deposit by 7th of next month"
        )
    
    if payment_type == "PROFESSIONAL" and amount > threshold_single:
        tds_amount = amount * 0.10  # 10% for professionals (Section 194J)
        return (
            True,
            SEVERITY_WARN,
            f"TDS applicable: Deduct ₹{tds_amount:,.0f} (10% of ₹{amount:,.0f}) under Section 194J",
            "Deduct TDS and deposit by 7th of next month"
        )
    
    return (True, SEVERITY_INFO, "TDS not applicable", "")

def rule_tds_cash_withdrawal(amount: float, annual_aggregate: float) -> Tuple[bool, str, str, str]:
    """
    RULE 5: Check TDS on cash withdrawals (Section 194N).
    
    Args:
        amount: Withdrawal amount
        annual_aggregate: Total cash withdrawals in FY
        
    Returns:
        (is_valid, severity, message, action)
    """
    if annual_aggregate > 1_00_00_000:  # > ₹1 crore
        tds_rate = 0.05  # 5%
        tds_amount = amount * tds_rate
        return (
            True,
            SEVERITY_WARN,
            f"TDS on cash withdrawal: Aggregate > ₹1Cr. Deduct ₹{tds_amount:,.0f} (5% of ₹{amount:,.0f})",
            "Bank will deduct TDS automatically"
        )
    elif annual_aggregate > 20_00_000:  # > ₹20 lakhs
        tds_rate = 0.02  # 2%
        tds_amount = amount * tds_rate
        return (
            True,
            SEVERITY_WARN,
            f"TDS on cash withdrawal: Aggregate > ₹20L. Deduct ₹{tds_amount:,.0f} (2% of ₹{amount:,.0f})",
            "Bank will deduct TDS automatically"
        )
    
    return (True, SEVERITY_INFO, "No TDS on cash withdrawal", "")

def rule_gstr_filing_deadline_warning(today: date = None) -> Tuple[bool, str, str, str]:
    """
    RULE 6: Warn about approaching GSTR filing deadlines.
    
    Args:
        today: Current date (defaults to today)
        
    Returns:
        (is_valid, severity, message, action)
    """
    if today is None:
        today = date.today()
    
    day = today.day
    
    # GSTR-1 due on 11th
    if day >= 8 and day <= 10:
        days_left = 11 - day
        return (
            True,
            SEVERITY_INFO,
            f"GSTR-1 filing due in {days_left} days (11th). Have you compiled your sales invoices?",
            "Prepare GSTR-1 sales return"
        )
    
    # GSTR-3B due on 20th
    if day >= 17 and day <= 19:
        days_left = 20 - day
        return (
            True,
            SEVERITY_INFO,
            f"GSTR-3B summary due in {days_left} days (20th). Reconcile your books.",
            "File GSTR-3B summary return"
        )
    
    return (True, SEVERITY_INFO, "No immediate GSTR deadlines", "")

def rule_duplicate_invoice_gst(customer: str, amount: float, gst_amount: float, invoice_date: date) -> Tuple[bool, str, str, str]:
    """
    RULE 7: Check for duplicate invoices (same customer, amount, GST within 1 day).
    
    Args:
        customer: Customer name
        amount: Invoice amount
        gst_amount: GST amount
        invoice_date: Invoice date
        
    Returns:
        (is_valid, severity, message, action)
    """
    db = SessionLocal()
    try:
        # Check for duplicates within 1 day
        existing = db.query(Voucher).filter(
            Voucher.party_name == customer,
            Voucher.amount == amount,
            Voucher.date >= invoice_date - timedelta(days=1),
            Voucher.date <= invoice_date + timedelta(days=1),
            Voucher.voucher_type == "Sales"
        ).first()
        
        if existing:
            return (
                False,
                SEVERITY_BLOCK,
                f"Duplicate invoice detected to {customer} for ₹{amount:,.0f} (within 1 day)",
                "Verify this is not a duplicate entry"
            )
        
        return (True, SEVERITY_INFO, "No duplicate detected", "")
        
    except Exception as e:
        logger.error(f"Duplicate check error: {e}")
        return (True, SEVERITY_INFO, "Could not check for duplicates", "")
    finally:
        db.close()

def rule_msme_form1_compliance(supplier: str, amount_due: float, days_unpaid: int) -> Tuple[bool, str, str, str]:
    """
    RULE 8: Check MSME Form 1 compliance (payments > 45 days).
    
    Args:
        supplier: MSME supplier name
        amount_due: Amount outstanding
        days_unpaid: Days since invoice
        
    Returns:
        (is_valid, severity, message, action)
    """
    if days_unpaid > 45:
        return (
            False,
            SEVERITY_BLOCK,
            f"MSME Form 1 due: You owe {supplier} ₹{amount_due:,.0f} (unpaid {days_unpaid} days). File Form 1.",
            f"File MSME Form 1 immediately. Penalty: ₹20,000 + ₹1,000/day (max ₹3,00,000)"
        )
    
    if days_unpaid > 35:  # Warning before deadline
        days_left = 45 - days_unpaid
        return (
            True,
            SEVERITY_WARN,
            f"MSME payment to {supplier} due in {days_left} days. ₹{amount_due:,.0f} outstanding.",
            "Pay MSME supplier within 45 days to avoid Form 1 filing"
        )
    
    return (True, SEVERITY_INFO, "MSME compliance OK", "")

def rule_e_invoicing_mandatory(turnover: float, invoice_amount: float) -> Tuple[bool, str, str, str]:
    """
    RULE 9: Check if e-invoicing is mandatory.
    
    Args:
        turnover: Annual turnover
        invoice_amount: Current invoice amount
        
    Returns:
        (is_valid, severity, message, action)
    """
    if turnover > 1_00_00_000:  # > ₹1 crore
        return (
            True,
            SEVERITY_WARN,
            "E-invoicing mandatory for businesses with turnover > ₹1Cr. Use GST portal e-invoice system.",
            "Generate e-invoice from GST portal before creating invoice"
        )
    
    return (True, SEVERITY_INFO, "E-invoicing not mandatory", "")

def rule_e_way_bill_required(amount: float, is_goods_movement: bool = True) -> Tuple[bool, str, str, str]:
    """
    RULE 10: Check if e-way bill is required for goods movement.
    
    Args:
        amount: Invoice amount
        is_goods_movement: Whether goods are being transported
        
    Returns:
        (is_valid, severity, message, action)
    """
    if is_goods_movement and amount > 50_000:
        return (
            True,
            SEVERITY_WARN,
            f"E-way bill required for goods movement > ₹50,000 (Invoice: ₹{amount:,.0f})",
            "Generate e-way bill from GST portal before dispatch"
        )
    
    return (True, SEVERITY_INFO, "E-way bill not required", "")

def rule_credit_limit_msme_45_days(is_msme: bool, days_due: int) -> Tuple[bool, str, str, str]:
    """
    RULE 11: Check MSME credit limit (45 days mandate).
    """
    if is_msme and days_due > 45:
        return (
            True,
            SEVERITY_INFO,
            f"Legal mandate: Pay MSME suppliers within 45 days. Payment is {days_due} days old.",
            "Prioritize this payment to avoid interest penalties"
        )
    return (True, SEVERITY_INFO, "Within MSME credit limits", "")

def rule_input_tax_credit_eligibility(has_valid_gstin: bool, gst_charged: bool, days_old: int) -> Tuple[bool, str, str, str]:
    """
    RULE 12: Check Input Tax Credit (ITC) eligibility.
    """
    if has_valid_gstin and gst_charged:
        if days_old > 365:
             return (
                False,
                SEVERITY_WARN,
                "ITC might be time-barred (invoice > 1 year old).",
                "Consult CA before claiming ITC"
            )
        return (
            True,
            SEVERITY_INFO,
            "ITC eligible. Ensure supplier files GSTR-1 for reflection in GSTR-2B.",
            "File in GSTR-3B"
        )
    return (True, SEVERITY_INFO, "ITC check skipped", "")

def rule_composition_scheme_itc_restriction(is_composition: bool, claiming_itc: bool) -> Tuple[bool, str, str, str]:
    """
    RULE 13: Check ITC restriction for Composition Scheme.
    """
    if is_composition and claiming_itc:
        return (
            False,
            SEVERITY_BLOCK,
            "Under Composition scheme, ITC cannot be claimed. GST is final 1% on turnover.",
            "Do not claim Input Tax Credit"
        )
    return (True, SEVERITY_INFO, "Composition scheme check OK", "")

def rule_state_specific_tax_variations(state: str) -> Tuple[bool, str, str, str]:
    """
    RULE 14: Check state-specific tax variations.
    """
    special_states = ["JK", "AS", "HP", "UK"] # J&K, Assam, Himachal, Uttarakhand
    if state in special_states:
        return (
            True,
            SEVERITY_WARN,
            f"Verify GST rate for {state}. Special concessional rates may apply.",
            "Contact CA for state-specific rules"
        )
    return (True, SEVERITY_INFO, "Standard state tax rules apply", "")

def rule_annual_gstr9_due_date(turnover: float, today: date = None) -> Tuple[bool, str, str, str]:
    """
    RULE 15: Check Annual GSTR-9 due date.
    """
    if today is None:
        today = date.today()
    
    if turnover > 1_00_00_000 and today.month == 12:
        return (
            True,
            SEVERITY_INFO,
            "Annual GSTR-9 due 31st December. Reconcile your books now.",
            "Prepare GSTR-9 annual return"
        )
    return (True, SEVERITY_INFO, "GSTR-9 not immediately due", "")

def rule_tds_deposit_deadline(today: date = None) -> Tuple[bool, str, str, str]:
    """
    RULE 16: Check TDS deposit deadline (7th of next month).
    """
    if today is None:
        today = date.today()
        
    if today.day <= 7:
        return (
            True,
            SEVERITY_INFO,
            f"TDS deposit deadline is 7th {today.strftime('%B')}.",
            "Ensure TDS deducted last month is deposited"
        )
    return (True, SEVERITY_INFO, "TDS deposit window open", "")

def rule_suspicious_invoice_pattern(customer: str, amount: float, days: int = 7) -> Tuple[bool, str, str, str]:
    """
    RULE 17: Check for suspicious high-value invoice patterns.
    """
    # This would typically query the DB for recent transactions
    # Simplified logic for now
    if amount > 50_00_000: # Single large transaction
         return (
            True,
            SEVERITY_INFO,
            f"High value transaction: ₹{amount:,.0f} to {customer}. Verify authenticity.",
            "Review invoice details"
        )
    return (True, SEVERITY_INFO, "Transaction pattern normal", "")

def rule_inter_state_gst_variation(state_from: str, state_to: str, tax_type: str) -> Tuple[bool, str, str, str]:
    """
    RULE 18: Check IGST vs CGST+SGST application.
    """
    if state_from != state_to:
        if tax_type != "IGST":
             return (
                False,
                SEVERITY_WARN,
                "Inter-state supply detected. Use IGST instead of CGST+SGST.",
                "Change tax type to IGST"
            )
    else:
        if tax_type == "IGST":
             return (
                False,
                SEVERITY_WARN,
                "Intra-state supply detected. Use CGST+SGST instead of IGST.",
                "Change tax type to CGST+SGST"
            )
    return (True, SEVERITY_INFO, "Tax type correct for state", "")

def rule_invoice_series_continuity(last_invoice_no: str, current_invoice_no: str) -> Tuple[bool, str, str, str]:
    """
    RULE 19: Check invoice series continuity.
    """
    # Simplified check assuming numeric suffix
    try:
        # Extract numbers
        import re
        last_num = int(re.search(r'\d+$', last_invoice_no).group())
        curr_num = int(re.search(r'\d+$', current_invoice_no).group())
        
        if curr_num != last_num + 1:
             return (
                True,
                SEVERITY_WARN,
                f"Invoice series gap detected: {current_invoice_no} follows {last_invoice_no} (Gap: {curr_num - last_num - 1}).",
                "Verify missing invoices"
            )
    except:
        pass
    return (True, SEVERITY_INFO, "Invoice series continuous", "")

def rule_amendment_credit_debit_note(intent: str, amount_change: float) -> Tuple[bool, str, str, str]:
    """
    RULE 20: Check usage of Credit/Debit notes for amendments.
    """
    if intent == "UPDATE_INVOICE_AMOUNT":
        if amount_change < 0:
             return (
                True,
                SEVERITY_WARN,
                "Reducing invoice amount? Use Credit Note instead of editing invoice.",
                "Create Credit Note"
            )
        elif amount_change > 0:
             return (
                True,
                SEVERITY_WARN,
                "Increasing invoice amount? Use Debit Note instead of editing invoice.",
                "Create Debit Note"
            )
    return (True, SEVERITY_INFO, "Amendment check OK", "")

def rule_annual_turnover_limit_check(ytd_turnover: float, months_elapsed: int) -> Tuple[bool, str, str, str]:
    """
    RULE 21: Check if projected annual turnover approaches thresholds.
    
    Args:
        ytd_turnover: Year-to-date turnover
        months_elapsed: Months completed in FY
        
    Returns:
        (is_valid, severity, message, action)
    """
    projected_turnover = ytd_turnover * (12 / months_elapsed) if months_elapsed > 0 else ytd_turnover
    
    # Check against key thresholds
    if projected_turnover > 38_00_000 and projected_turnover < GST_THRESHOLD_GOODS:
        return (
            True,
            SEVERITY_INFO,
            f"Projected turnover: ₹{projected_turnover/100000:.1f}L. Close to ₹40L GST threshold.",
            "Plan for GST registration"
        )
    
    if projected_turnover > 95_00_000 and projected_turnover < 1_00_00_000:
        return (
            True,
            SEVERITY_INFO,
            f"Projected turnover: ₹{projected_turnover/100000:.1f}L. Close to ₹1Cr audit threshold.",
            "Prepare for book audit requirement"
        )
    
    return (True, SEVERITY_INFO, "Turnover within limits", "")
