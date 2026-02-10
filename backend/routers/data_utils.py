from typing import Dict, Any

def normalize_tally_voucher(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Take a single voucher dict from TallyReader and convert it into
    the normalized shape expected by the frontend Daybook list.
    """
    out: Dict[str, Any] = {}

    # Date: from "YYYYMMDD" -> "YYYY-MM-DD"
    raw_date = str(raw.get("date", ""))  # e.g. "20250101"
    if len(raw_date) == 8 and raw_date.isdigit():
        out["date"] = f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
    else:
        out["date"] = raw_date  # fallback

    # Amount: string -> float (Handling mixed types and comma conversion if needed)
    amount = raw.get("amount", 0)
    try:
        # Sometimes Tally sends "1,200.00"
        if isinstance(amount, str):
            amount = amount.replace(",", "")
        out["amount"] = float(amount)
    except (TypeError, ValueError):
        out["amount"] = 0.0

    # Voucher number and party name (rename for frontend)
    out["voucher_number"] = raw.get("number") or raw.get("voucher_number") or ""
    out["party_name"] = raw.get("party") or raw.get("party_name") or ""

    # Other passthrough fields that frontend likely needs:
    out["voucher_type"] = raw.get("type") or raw.get("voucher_type") or ""
    out["reference"] = raw.get("reference") or raw.get("guid") # GUID often used as ref
    out["narration"] = raw.get("narration") or ""

    # Since this came from Tally, consider it fully synced
    out["sync_status"] = "SYNCED"

    # Include original id if present (for future linking)
    if "id" in raw:
        out["id"] = raw["id"]
        
    # Also pass through key items if present (for detailed view)
    if "items" in raw:
        out["items"] = raw["items"]
        
    if "ledgers" in raw:
        out["ledgers"] = raw["ledgers"]
        
    if "tax_breakdown" in raw:
        out["tax_breakdown"] = raw["tax_breakdown"]

    return out
