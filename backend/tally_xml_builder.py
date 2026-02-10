from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Sequence
from xml.sax.saxutils import escape as xml_escape

import xml.etree.ElementTree as ET

logger = logging.getLogger("tally_xml_builder")
logging.basicConfig(level=logging.INFO)


class TallyXMLValidationError(ValueError):
    """Raised when payloads cannot be mapped to Tally's XML schema."""


def parse_xml_safely(xml_text: str) -> Optional[ET.Element]:
    """
    Safely parse XML and return the root element, or None if parsing fails.
    """
    try:
        return ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.error("XML ParseError: %s; raw: %s", exc, xml_text[:2000])
        return None


def _escape(value: Any) -> str:
    return xml_escape(str(value), entities={"'": "&apos;", '"': "&quot;"})


def _format_bool(value: Any) -> str:
    return "Yes" if bool(value) else "No"


def _format_decimal(value: Any) -> str:
    try:
        return str(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise TallyXMLValidationError(f"Invalid decimal value: {value!r}") from exc


def _coerce_list(value: Any, field_name: str) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]
    cleaned = []
    for item in items:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        cleaned.append(text)
    if not cleaned:
        raise TallyXMLValidationError(f"{field_name} list cannot be empty")
    return cleaned


LEDGER_FIELD_SPEC: Dict[str, Dict[str, Any]] = {
    "NAME": {"type": "string"},
    "PARENT": {"type": "string"},
    "GSTIN": {"type": "string"},
    "PAN": {"type": "string"},
    "GSTREGISTRATIONTYPE": {"type": "string"},
    "COUNTRYNAME": {"type": "string"},
    "STATENAME": {"type": "string"},
    "PINCODE": {"type": "string"},
    "EMAIL": {"type": "string"},
    "MOBILENUMBER": {"type": "string"},
    "PHONENUMBER": {"type": "string"},
    "LEDSTATENAME": {"type": "string"},
    "INCOMETAXNUMBER": {"type": "string"},
    "MAILNAMES": {
        "type": "string_list",
        "list_tag": "MAILINGNAME.LIST",
        "item_tag": "MAILINGNAME",
    },
    "ADDRESS": {
        "type": "string_list",
        "list_tag": "ADDRESS.LIST",
        "item_tag": "ADDRESS",
    },
    "ISBILLWISEON": {"type": "bool"},
    "OPENINGBALANCE": {"type": "decimal"},
    "CREDITLIMIT": {"type": "decimal"},
}

LEDGER_ALLOWED_FIELDS = set(LEDGER_FIELD_SPEC)


def _render_string_list(list_tag: str, item_tag: str, values: Sequence[str], indent: str) -> str:
    body = "\n".join(
        f"{indent}    <{item_tag}>{_escape(value)}</{item_tag}>"
        for value in values
    )
    return (
        f"{indent}<{list_tag} TYPE=\"String\">\n"
        f"{body}\n"
        f"{indent}</{list_tag}>"
    )


def _render_ledger_fields(fields: Dict[str, Any], indent: str = "        ") -> str:
    rendered: List[str] = []
    for original_key, value in fields.items():
        key = original_key.upper()
        spec = LEDGER_FIELD_SPEC[key]
        ftype = spec["type"]
        if ftype == "string":
            rendered.append(f"{indent}<{key}>{_escape(value)}</{key}>")
        elif ftype == "bool":
            rendered.append(f"{indent}<{key}>{_format_bool(value)}</{key}>")
        elif ftype == "decimal":
            rendered.append(f"{indent}<{key}>{_format_decimal(value)}</{key}>")
        elif ftype == "string_list":
            values = _coerce_list(value, key)
            rendered.append(
                _render_string_list(
                    spec["list_tag"],
                    spec["item_tag"],
                    values,
                    indent,
                )
            )
        else:
            raise TallyXMLValidationError(f"Unsupported field type '{ftype}' for {key}")
    return "\n".join(rendered)


def _wrap_envelope(company_name: str, report_name: str, payload: str) -> str:
    return (
        "<ENVELOPE>\n"
        "  <HEADER>\n"
        "    <TALLYREQUEST>Import Data</TALLYREQUEST>\n"
        "  </HEADER>\n"
        "  <BODY>\n"
        "    <IMPORTDATA>\n"
        "      <REQUESTDESC>\n"
        f"        <REPORTNAME>{_escape(report_name)}</REPORTNAME>\n"
        "        <STATICVARIABLES>\n"
        f"          <SVCURRENTCOMPANY>{_escape(company_name)}</SVCURRENTCOMPANY>\n"
        "        </STATICVARIABLES>\n"
        "      </REQUESTDESC>\n"
        "      <REQUESTDATA>\n"
        "        <TALLYMESSAGE xmlns:UDF=\"TallyUDF\">\n"
        f"{payload}\n"
        "        </TALLYMESSAGE>\n"
        "      </REQUESTDATA>\n"
        "    </IMPORTDATA>\n"
        "  </BODY>\n"
        "</ENVELOPE>"
    )


def _validate_ledger_updates(updates: Dict[str, Any]) -> Dict[str, Any]:
    if not updates:
        raise TallyXMLValidationError("Ledger updates cannot be empty")
    normalized: Dict[str, Any] = {}
    for key, value in updates.items():
        key_upper = key.upper()
        if key_upper not in LEDGER_ALLOWED_FIELDS:
            raise TallyXMLValidationError(
                f"Field '{key}' is not allowed for LEDGER updates"
            )
        if value is None:
            continue
        normalized[key_upper] = value
    if not normalized:
        raise TallyXMLValidationError("Ledger updates cannot be empty")
    return normalized


def build_ledger_update_message(ledger_name: str, updates: Dict[str, Any]) -> str:
    normalized_updates = _validate_ledger_updates(updates)
    if "NAME" not in normalized_updates:
        normalized_updates = {"NAME": ledger_name, **normalized_updates}
    body = _render_ledger_fields(normalized_updates)
    ledger_xml = (
        f"          <LEDGER NAME=\"{_escape(ledger_name)}\" ACTION=\"Alter\">\n"
        f"{body}\n"
        "          </LEDGER>"
    )
    return ledger_xml


def build_ledger_update_xml(company_name: str, ledger_name: str, updates: Dict[str, Any]) -> str:
    """
    Build a full Tally XML envelope for altering a ledger master.
    """
    if not company_name:
        raise TallyXMLValidationError("company_name is required")
    if not ledger_name:
        raise TallyXMLValidationError("ledger_name is required")
    ledger_message = build_ledger_update_message(ledger_name, updates)
    return _wrap_envelope(company_name, "All Masters", ledger_message)


VOUCHER_ALLOWED_FIELDS = {
    "DATE": "string",
    "EFFECTIVEDATE": "string",
    "VOUCHERTYPENAME": "string",
    "VOUCHERNUMBER": "string",
    "REFERENCE": "string",
    "PARTYLEDGERNAME": "string",
    "PARTYNAME": "string",
    "NARRATION": "string",
    "ENTEREDBY": "string",
    "GUID": "string",
}

LINE_ITEM_ALLOWED_FIELDS = {
    "LEDGERNAME": "string",
    "ISDEEMEDPOSITIVE": "bool",
    "AMOUNT": "decimal",
    "COSTCENTRENAME": "string",
    "GSTCLASSIFICATIONNAME": "string",
}

BILL_ALLOCATION_ALLOWED_FIELDS = {
    "NAME": "string",
    "BILLTYPE": "string",
    "AMOUNT": "decimal",
    "INTERESTCOLLECTION": "string",
}


@dataclass
class VoucherLineItem:
    ledger_name: str
    amount: Decimal
    is_deemed_positive: bool
    cost_centre: Optional[str] = None
    gst_classification: Optional[str] = None
    bill_allocations: List["BillAllocation"] = field(default_factory=list)

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "VoucherLineItem":
        missing = [field for field in ("ledger_name", "amount", "is_deemed_positive") if field not in payload]
        if missing:
            raise TallyXMLValidationError(
                f"Voucher line item missing required fields: {', '.join(missing)}"
            )
        amount = _format_decimal(payload["amount"])
        is_deemed_positive = _format_bool(payload["is_deemed_positive"])
        bill_allocations = [
            BillAllocation.from_dict(item)
            for item in payload.get("bill_allocations", [])
        ]
        return VoucherLineItem(
            ledger_name=str(payload["ledger_name"]),
            amount=Decimal(amount),
            is_deemed_positive=is_deemed_positive == "Yes",
            cost_centre=payload.get("cost_centre"),
            gst_classification=payload.get("gst_classification"),
            bill_allocations=bill_allocations,
        )

    def render(self, indent: str = "          ") -> str:
        # Amount string must use positive/negative as provided
        amount_str = _format_decimal(self.amount)
        lines = [
            f"{indent}<LEDGERNAME>{_escape(self.ledger_name)}</LEDGERNAME>",
            f"{indent}<ISDEEMEDPOSITIVE>{_format_bool(self.is_deemed_positive)}</ISDEEMEDPOSITIVE>",
            f"{indent}<AMOUNT>{amount_str}</AMOUNT>",
        ]
        if self.cost_centre:
            lines.append(f"{indent}<COSTCENTRENAME>{_escape(self.cost_centre)}</COSTCENTRENAME>")
        if self.gst_classification:
            lines.append(
                f"{indent}<GSTCLASSIFICATIONNAME>{_escape(self.gst_classification)}</GSTCLASSIFICATIONNAME>"
            )
        if self.bill_allocations:
            lines.extend(render_bill_allocations(self.bill_allocations, indent))
        content = "\n".join(lines)
        return (
            f"        <ALLLEDGERENTRIES.LIST>\n"
            f"{content}\n"
            f"        </ALLLEDGERENTRIES.LIST>"
        )


@dataclass
class BillAllocation:
    name: str
    amount: Decimal
    bill_type: str = "New Ref"
    interest_collection: Optional[str] = None

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "BillAllocation":
        missing = [field for field in ("name", "amount") if field not in payload]
        if missing:
            raise TallyXMLValidationError(
                f"Bill allocation missing required fields: {', '.join(missing)}"
            )
        return BillAllocation(
            name=str(payload["name"]),
            amount=Decimal(_format_decimal(payload["amount"])),
            bill_type=str(payload.get("bill_type") or "New Ref"),
            interest_collection=payload.get("interest_collection"),
        )


def render_bill_allocations(allocations: Sequence[BillAllocation], indent: str) -> List[str]:
    rendered: List[str] = []
    inner_indent = indent + "    "
    for allocation in allocations:
        lines = [
            f"{inner_indent}<NAME>{_escape(allocation.name)}</NAME>",
            f"{inner_indent}<BILLTYPE>{_escape(allocation.bill_type)}</BILLTYPE>",
            f"{inner_indent}<AMOUNT>{_format_decimal(allocation.amount)}</AMOUNT>",
        ]
        if allocation.interest_collection:
            lines.append(
                f"{inner_indent}<INTERESTCOLLECTION>{_escape(allocation.interest_collection)}</INTERESTCOLLECTION>"
            )
        rendered.append(
            f"{indent}<BILLALLOCATIONS.LIST>\n"
            f"{'\n'.join(lines)}\n"
            f"{indent}</BILLALLOCATIONS.LIST>"
        )
    return rendered


def _validate_voucher_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key, value in fields.items():
        key_upper = key.upper()
        if key_upper not in VOUCHER_ALLOWED_FIELDS:
            raise TallyXMLValidationError(f"Field '{key}' is not allowed for VOUCHER")
        if value is None:
            continue
        normalized[key_upper] = value
    return normalized


def _ensure_required_voucher_fields(fields: Dict[str, Any]) -> None:
    # DATE and VOUCHERTYPENAME are always required
    required = ["DATE", "VOUCHERTYPENAME"]
    
    # PARTYLEDGERNAME is not required for Journal vouchers
    voucher_type = fields.get("VOUCHERTYPENAME", "").upper()
    if voucher_type not in ["JOURNAL"]:
        required.append("PARTYLEDGERNAME")
    
    missing = [field for field in required if field not in fields]
    if missing:
        raise TallyXMLValidationError(
            f"Voucher payload missing required fields: {', '.join(missing)}"
        )


def _render_voucher_body(fields: Dict[str, Any], line_items: Iterable[VoucherLineItem]) -> str:
    rendered_fields = []
    for key, value in fields.items():
        if VOUCHER_ALLOWED_FIELDS[key] == "string":
            rendered_fields.append(f"          <{key}>{_escape(value)}</{key}>")
        else:
            raise TallyXMLValidationError(f"Unsupported voucher field type for '{key}'")
    entries = [item.render() for item in line_items]
    return "\n".join(rendered_fields + entries)


def _build_voucher(
    company_name: str,
    fields: Dict[str, Any],
    line_items_payload: Iterable[Dict[str, Any]],
    action: str,
) -> str:
    if not company_name:
        raise TallyXMLValidationError("company_name is required")
    _ensure_required_voucher_fields(fields)
    normalized_fields = _validate_voucher_fields(fields)
    line_items = [VoucherLineItem.from_dict(item) for item in line_items_payload]
    if not line_items:
        raise TallyXMLValidationError("Voucher must contain at least one line item")
    voucher_body = _render_voucher_body(normalized_fields, line_items)
    voucher_type = normalized_fields["VOUCHERTYPENAME"]
    message = (
        f"          <VOUCHER VCHTYPE=\"{_escape(voucher_type)}\" ACTION=\"{_escape(action)}\">\n"
        f"{voucher_body}\n"
        "          </VOUCHER>"
    )
    return _wrap_envelope(company_name, "Vouchers", message)


def build_ledger_create_xml(company_name: str, ledger_name: str, fields: Dict[str, Any]) -> str:
    """
    Build a full Tally XML envelope for creating a ledger master.
    """
    if not company_name:
        raise TallyXMLValidationError("company_name is required")
    if not ledger_name:
        raise TallyXMLValidationError("ledger_name is required")
    
    # Reuse build_ledger_update_message but change ACTION to Create
    # Since build_ledger_update_message hardcodes "Alter", we need to reimplement or refactor.
    # Refactoring build_ledger_update_message to accept action would be cleaner.
    
    normalized_fields = _validate_ledger_updates(fields)
    if "NAME" not in normalized_fields:
        normalized_fields = {"NAME": ledger_name, **normalized_fields}
    body = _render_ledger_fields(normalized_fields)
    ledger_xml = (
        f"          <LEDGER NAME=\"{_escape(ledger_name)}\" ACTION=\"Create\">\n"
        f"{body}\n"
        "          </LEDGER>"
    )
    return _wrap_envelope(company_name, "All Masters", ledger_xml)


def build_voucher_create_xml(
    company_name: str,
    voucher_fields: Dict[str, Any],
    line_items: Iterable[Dict[str, Any]],
) -> str:
    """
    Construct a voucher creation XML envelope according to Tally schema.
    """
    return _build_voucher(company_name, voucher_fields, line_items, action="Create")


def build_voucher_update_xml(
    company_name: str,
    voucher_fields: Dict[str, Any],
    line_items: Iterable[Dict[str, Any]],
) -> str:
    """
    Construct a voucher alteration XML envelope according to Tally schema.
    """
    return _build_voucher(company_name, voucher_fields, line_items, action="Alter")


# --- Stock Item Support ---

STOCK_ITEM_FIELD_SPEC: Dict[str, Dict[str, Any]] = {
    "NAME": {"type": "string"},
    "PARENT": {"type": "string"},
    "BASEUNITS": {"type": "string"},
    "ADDITIONALUNITS": {"type": "string"},
    "OPENINGBALANCE": {"type": "decimal"},
    "GSTAPPLICABLE": {"type": "string"}, # &#4; Applicable, &#4; Not Applicable
    "GSTCLASS": {"type": "string"},
    "COSTINGMETHOD": {"type": "string"},
    "VALUATIONMETHOD": {"type": "string"},
    "HASMANUFACTURINGDATE": {"type": "bool"},
    "ISEXPIRYDATE": {"type": "bool"},
    "ISBATCHWISEON": {"type": "bool"},
}

STOCK_ITEM_ALLOWED_FIELDS = set(STOCK_ITEM_FIELD_SPEC)

def _render_stock_item_fields(fields: Dict[str, Any], indent: str = "        ") -> str:
    rendered: List[str] = []
    for original_key, value in fields.items():
        key = original_key.upper()
        if key not in STOCK_ITEM_FIELD_SPEC:
            continue
            
        spec = STOCK_ITEM_FIELD_SPEC[key]
        ftype = spec["type"]
        
        if ftype == "string":
            rendered.append(f"{indent}<{key}>{_escape(value)}</{key}>")
        elif ftype == "bool":
            rendered.append(f"{indent}<{key}>{_format_bool(value)}</{key}>")
        elif ftype == "decimal":
            rendered.append(f"{indent}<{key}>{_format_decimal(value)}</{key}>")
            
    return "\n".join(rendered)

def _build_stock_item(
    company_name: str,
    item_name: str,
    fields: Dict[str, Any],
    action: str
) -> str:
    if not company_name:
        raise TallyXMLValidationError("company_name is required")
    if not item_name:
        raise TallyXMLValidationError("item_name is required")
        
    normalized: Dict[str, Any] = {}
    for key, value in fields.items():
        key_upper = key.upper()
        if key_upper in STOCK_ITEM_ALLOWED_FIELDS:
            normalized[key_upper] = value
            
    if "NAME" not in normalized:
        normalized["NAME"] = item_name
        
    body = _render_stock_item_fields(normalized)
    
    item_xml = (
        f"          <STOCKITEM NAME=\"{_escape(item_name)}\" ACTION=\"{_escape(action)}\">\n"
        f"{body}\n"
        "          </STOCKITEM>"
    )
    return _wrap_envelope(company_name, "All Masters", item_xml)

def build_stock_item_create_xml(company_name: str, item_name: str, fields: Dict[str, Any]) -> str:
    return _build_stock_item(company_name, item_name, fields, action="Create")

def build_stock_item_update_xml(company_name: str, item_name: str, fields: Dict[str, Any]) -> str:
    return _build_stock_item(company_name, item_name, fields, action="Alter")


# --- Inventory & Sales Invoice Support ---

@dataclass
class InventoryEntry:
    stock_item_name: str
    rate: str
    amount: Decimal
    actual_qty: str
    billed_qty: str
    ledger_name: str  # Generic name (Sales Account or Purchase Account)
    
    # Optional fields
    discount: Optional[Decimal] = None
    
    # Backward compatibility alias (if needed by old code, though we should update callers)
    # We'll map sales_ledger_name in __init__ if strictly needed, but dataclass makes it hard.
    # We update the caller instead.

def format_tally_amount(amount: float, is_debit: bool) -> tuple[str, str]:
    """
    Helper to enforce Tally XML Rules:
    Debit (Yes/Purchase) -> Negative Amount
    Credit (No/Sales) -> Positive Amount
    """
    abs_amt = abs(amount)
    if is_debit:
        # Debit: ISDEEMEDPOSITIVE="Yes", Amount needs to be NEGATIVE
        return "Yes", _format_decimal(-abs_amt)
    else:
        # Credit: ISDEEMEDPOSITIVE="No", Amount needs to be POSITIVE
        return "No", _format_decimal(abs_amt)

class InventoryEntry:
    # ... previous code ...
    
    def render(self, is_deemed_positive: bool = False, indent: str = "          ") -> str:
        """
        Renders the Inventory Entry.
        is_deemed_positive: 
           - False for Sales (Credit) - Default
           - True for Purchase (Debit)
        """
        # Logically Determine Sign using Helper
        # is_deemed_positive directly maps to is_debit here
        is_debit = is_deemed_positive
        
        pos_str, amt_str = format_tally_amount(self.amount, is_debit)
        
        # Determine signs and flags - Centralized
        stock_item_is_positive_str = pos_str
        allocation_is_positive_str = pos_str
        tally_amount_str = amt_str

        # Accounting Allocation (Sales/Purchase Ledger)
        alloc_indent = indent + "  "
        allocation_xml = (
            f"{indent}<ACCOUNTINGALLOCATIONS.LIST>\n"
            f"{alloc_indent}<LEDGERNAME>{_escape(self.ledger_name)}</LEDGERNAME>\n"
            f"{alloc_indent}<ISDEEMEDPOSITIVE>{allocation_is_positive_str}</ISDEEMEDPOSITIVE>\n"
            f"{alloc_indent}<AMOUNT>{tally_amount_str}</AMOUNT>\n"
            f"{indent}</ACCOUNTINGALLOCATIONS.LIST>"
        )

        lines = [
            f"{indent}<STOCKITEMNAME>{_escape(self.stock_item_name)}</STOCKITEMNAME>",
            f"{indent}<ISDEEMEDPOSITIVE>{stock_item_is_positive_str}</ISDEEMEDPOSITIVE>",
            f"{indent}<RATE>{_escape(self.rate)}</RATE>",
            f"{indent}<AMOUNT>{tally_amount_str}</AMOUNT>",
            f"{indent}<ACTUALQTY>{_escape(self.actual_qty)}</ACTUALQTY>",
            f"{indent}<BILLEDQTY>{_escape(self.billed_qty)}</BILLEDQTY>",
            allocation_xml
        ]
        
        return (
            f"        <ALLINVENTORYENTRIES.LIST>\n"
            f"{'\n'.join(lines)}\n"
            f"        </ALLINVENTORYENTRIES.LIST>"
        )


def build_invoice_xml(
    company_name: str,
    voucher_fields: Dict[str, Any],
    inventory_items: List[InventoryEntry],
    additional_ledgers: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Constructs a Tally XML for Sales/Purchase Voucher in "Item Invoice Mode".
    Auto-detects context based on VOUCHERTYPENAME.
    """
    if not additional_ledgers:
        additional_ledgers = []

    # 1. Validate Basic Fields
    if not company_name:
        raise TallyXMLValidationError("company_name is required")
    _ensure_required_voucher_fields(voucher_fields)
    normalized_fields = _validate_voucher_fields(voucher_fields)
    
    # 2. Determine Context (Purchase vs Sales)
    voucher_type = normalized_fields.get("VOUCHERTYPENAME", "Sales")
    is_purchase = voucher_type.lower() == "purchase"
    
    # Context Logic:
    # Sales: Party=Debit, Income=Credit, Tax=Credit (Output)
    # Purchase: Party=Credit, Expense=Debit, Tax=Debit (Input)
    
    # Inventory Entries Flag
    inv_is_deemed_positive = True if is_purchase else False
    
    # 3. Calculate Totals
    # Total Value of Items (Absolute)
    total_item_val = sum(abs(item.amount) for item in inventory_items)
    
    # Additional Charges
    # We must handle Debit/Credit carefully.
    # For Sales: Charges usually Credit (Income) or Debit (Expense - rare in invoice?)
    # For Purchase: Charges usually Debit (Expense)
    
    total_other_credits = Decimal(0)
    total_other_debits = Decimal(0)
    additional_entries_xml = []
    indent = "          "
    
    for entry in additional_ledgers:
        lname = entry.get("ledger")
        amount = Decimal(str(entry.get("amount", 0)))
        #Caller specifies is_debit intent explicitly?
        #Or we interpret? Let's rely on caller 'is_debit' flag if present.
        #Default: If Purchase, charges are Debit? If Sales, charges are Credit?
        #Let's trust the flag or default to Context.
        
        if "is_debit" in entry:
            is_debit = bool(entry.get("is_debit"))
        else:
            is_debit = True if is_purchase else False # Default context
            
        if not lname: continue
            
        # Amount Sign Logic
        # Tally convention: Always negative number in XML amount?
        tally_amount = -abs(amount) 
        
        is_positive_str = "Yes" if is_debit else "No"
        
        if is_debit:
            total_other_debits += abs(amount)
        else:
            total_other_credits += abs(amount)
            
        additional_entries_xml.append(
            f"        <LEDGERENTRIES.LIST>\n"
            f"{indent}<LEDGERNAME>{_escape(lname)}</LEDGERNAME>\n"
            f"{indent}<ISDEEMEDPOSITIVE>{is_positive_str}</ISDEEMEDPOSITIVE>\n"
            f"{indent}<AMOUNT>{_format_decimal(tally_amount)}</AMOUNT>\n"
            f"        </LEDGERENTRIES.LIST>"
        )

    # 4. Calculate Party Ledger Amount (Balancing Figure)
    # Debits must equal Credits.
    # Sales: Party(Dr) + Charges(Dr) = Sales(Cr) + Charges(Cr)
    # Purchase: Party(Cr) + Charges(Cr) = Purchase(Dr) + Charges(Dr)
    
    # Total Debits so far (excluding Party)
    current_debits = total_other_debits + (total_item_val if is_purchase else Decimal(0))
    # Total Credits so far (excluding Party)
    current_credits = total_other_credits + (total_item_val if not is_purchase else Decimal(0))
    
    # Balancing
    if is_purchase:
        # Purchase (Dr) > Credits. Party must be Credit.
        # Party Cr = Total Dr - Other Cr
        party_amount = current_debits - total_other_credits
        party_is_debit = False # Credit
        
        # If party_amount < 0, it means Credits > Debits? (e.g. Return?)
        if party_amount < 0:
            party_amount = abs(party_amount)
            party_is_debit = True
    else:
        # Sales (Cr). Party must be Debit.
        # Party Dr = Total Cr - Other Dr
        party_amount = current_credits - total_other_debits
        party_is_debit = True # Debit
        
        if party_amount < 0:
            party_amount = abs(party_amount)
            party_is_debit = False

    party_ledger_name = normalized_fields.get("PARTYLEDGERNAME")
    if not party_ledger_name:
        raise TallyXMLValidationError(f"PARTYLEDGERNAME is required for {voucher_type}")

    # 5. Render
    inventory_xml_list = [item.render(is_deemed_positive=inv_is_deemed_positive) for item in inventory_items]
    inventory_block = "\n".join(inventory_xml_list)
    additional_block = "\n".join(additional_entries_xml)
    
    party_sign_str = "Yes" if party_is_debit else "No"
    party_tally_amount = -abs(party_amount) # Convention
    
    party_entry_xml = (
        f"        <LEDGERENTRIES.LIST>\n"
        f"{indent}<LEDGERNAME>{_escape(party_ledger_name)}</LEDGERNAME>\n"
        f"{indent}<ISDEEMEDPOSITIVE>{party_sign_str}</ISDEEMEDPOSITIVE>\n"
        f"{indent}<AMOUNT>{_format_decimal(party_tally_amount)}</AMOUNT>\n"
        f"        </LEDGERENTRIES.LIST>"
    )
    
    # Header
    header_lines = []
    for key, value in normalized_fields.items():
        if VOUCHER_ALLOWED_FIELDS[key] == "string":
            header_lines.append(f"          <{key}>{_escape(value)}</{key}>")
            
    header_block = "\n".join(header_lines)
    
    # Order: Header, Items, Party, Others.
    voucher_content = (
        f"{header_block}\n"
        f"{inventory_block}\n"
        f"{party_entry_xml}\n"
        f"{additional_block}"
    )
    
    action = "Create"
    message = (
        f"          <VOUCHER VCHTYPE=\"{_escape(voucher_type)}\" ACTION=\"{_escape(action)}\">\n"
        f"{voucher_content}\n"
        f"          </VOUCHER>"
    )
    
    return _wrap_envelope(company_name, "Vouchers", message)

# Alias for backward compatibility
build_sales_voucher_xml = build_invoice_xml
