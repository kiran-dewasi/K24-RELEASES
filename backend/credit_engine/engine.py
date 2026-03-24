"""
Credit Engine â€” Core Engine
============================
The single function all business flows must call: record_event().

Flow inside record_event():
  1. Compute credits via rating.compute_credits()
  2. Get/create billing cycle via cycle_manager.find_or_create_active_cycle()
  3. Insert usage_event row (immutable audit log)
  4. Atomically increment tenant_usage_summary via Postgres function
  5. Evaluate against plan limit â†’ CreditStatus (ALLOWED/NEAR_LIMIT/OVER_LIMIT/BLOCKED)
  6. Return CreditDecision (callers decide how to act based on .status)

CRITICAL: No code outside this module should write to usage_events or
tenant_usage_summary. Always go through record_event().
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from database.supabase_client import supabase
from credit_engine.models import (
    UsageEventIn,
    CreditDecision,
    CreditStatus,
    UsageSummary,
    EventType,
    EventSubtype,
)
from credit_engine.rating import compute_credits
from credit_engine.cycle_manager import find_or_create_active_cycle, get_tenant_plan

logger = logging.getLogger(__name__)

# â”€â”€ Threshold for NEAR_LIMIT warning (80% of plan limit) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
NEAR_LIMIT_THRESHOLD = 0.80


def _insert_usage_event(
    tenant_id:        str,
    company_id:       Optional[int],
    billing_cycle_id: str,
    event_type:       str,
    event_subtype:    str,
    credits_consumed: float,
    source:           str,
    metadata:         Dict[str, Any],
    status:           str,
) -> Optional[str]:
    """
    Insert a row into usage_events and return its UUID.
    This is the immutable audit record.
    """
    try:
        result = (
            supabase.table("usage_events")
            .insert({
                "tenant_id":        tenant_id,
                "company_id":       company_id,
                "billing_cycle_id": billing_cycle_id,
                "event_type":       event_type,
                "event_subtype":    event_subtype,
                "credits_consumed": credits_consumed,
                "source":           source,
                "metadata_json":    metadata,
                "status":           status,
            })
            .execute()
        )
        rows = result.data or []
        return rows[0]["id"] if rows else str(uuid.uuid4())
    except Exception as exc:
        logger.error(f"[CreditEngine] Insert usage_event failed: {exc}")
        return str(uuid.uuid4())  # Return a dummy ID so we don't hard-crash callers


def _call_increment_atomic(
    tenant_id:        str,
    billing_cycle_id: str,
    event_type:       str,
    credits:          float,
) -> Optional[Dict[str, Any]]:
    """
    Call the Postgres increment_usage_atomic() function to atomically
    update tenant_usage_summary. This is the ONLY write path to that table.

    Uses Supabase RPC (REST POST to /rest/v1/rpc/increment_usage_atomic).
    """
    try:
        import httpx
        import os

        supabase_url     = os.getenv("SUPABASE_URL", "")
        # Try service key first, fall back to anon key
        service_key      = (
            os.getenv("SUPABASE_SERVICE_KEY") or
            os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
            os.getenv("SUPABASE_ANON_KEY") or
            os.getenv("SUPABASE_KEY", "")
        )
        url     = f"{supabase_url}/rest/v1/rpc/increment_usage_atomic"
        headers = {
            "apikey":        service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type":  "application/json",
        }
        payload = {
            "p_tenant_id":        tenant_id,
            "p_billing_cycle_id": billing_cycle_id,
            "p_event_type":       event_type,
            "p_credits":          credits,
        }
        resp = httpx.post(url, headers=headers, json=payload, timeout=10)

        if resp.status_code == 200:
            return resp.json()
        else:
            logger.error(
                f"[CreditEngine] increment_usage_atomic failed "
                f"HTTP {resp.status_code}: {resp.text[:200]}"
            )
            return None
    except Exception as exc:
        logger.error(f"[CreditEngine] increment_usage_atomic exception: {exc}")
        return None


def _compute_status(
    credits_used: float,
    max_credits:  int,
    enforcement_mode: str,
) -> CreditStatus:
    """
    Determine the credit decision status based on current usage vs plan limit.

    enforcement_mode:
      HARD_CAP        â†’ BLOCKED when over limit
      SOFT_CAP        â†’ OVER_LIMIT (allowed but flagged) when over limit
      NO_CAP_LOG_ONLY â†’ Always ALLOWED, just track
    """
    if max_credits <= 0:
        return CreditStatus.ALLOWED  # Enterprise / custom plan with no limit

    ratio = credits_used / max_credits

    if ratio < NEAR_LIMIT_THRESHOLD:
        return CreditStatus.ALLOWED

    if ratio < 1.0:
        return CreditStatus.NEAR_LIMIT

    # Over limit â€” enforcement_mode decides the outcome
    if enforcement_mode == "HARD_CAP":
        return CreditStatus.BLOCKED
    elif enforcement_mode == "SOFT_CAP":
        return CreditStatus.OVER_LIMIT
    else:  # NO_CAP_LOG_ONLY
        return CreditStatus.ALLOWED


def _build_status_message(status: CreditStatus, credits_used: float, max_credits: int) -> str:
    """Human-readable message for the credit decision."""
    remaining = max(0, max_credits - credits_used)
    if status == CreditStatus.ALLOWED:
        return f"{remaining} credits remaining this cycle."
    elif status == CreditStatus.NEAR_LIMIT:
        return f"Warning: Only {remaining:.0f} credits left ({credits_used}/{max_credits} used). Consider upgrading."
    elif status == CreditStatus.OVER_LIMIT:
        return f"Credit limit exceeded ({credits_used:.0f}/{max_credits}). This action was allowed but your plan limit is reached."
    elif status == CreditStatus.BLOCKED:
        return f"Credit limit reached ({credits_used:.0f}/{max_credits}). Action blocked. Please upgrade your plan."
    return ""


def record_event(
    tenant_id:     str,
    event_type:    str,       # Use EventType enum values: 'VOUCHER', 'DOCUMENT', 'MESSAGE'
    event_subtype: str,       # Use EventSubtype enum values
    company_id:    Optional[int] = None,
    source:        str            = "api",
    metadata:      Optional[Dict[str, Any]] = None,
) -> CreditDecision:
    """
    Record a business event and apply credit accounting.

    This is the ONLY entry point for all credit-consuming actions in K24.

    Args:
        tenant_id:     The tenant string ID (e.g. 'TENANT-84F03F7D').
        event_type:    'VOUCHER', 'DOCUMENT', or 'MESSAGE'.
        event_subtype: Fine-grained subtype (see EventSubtype enum).
        company_id:    Optional local company integer ID.
        source:        'whatsapp', 'kittu', 'api', 'web', 'tally_sync'.
        metadata:      Dict with context (voucher_id, page_count, etc.).

    Returns:
        CreditDecision with status, usage snapshot, and event_id.
        Always returns a decision â€” never raises (failures are logged).

    Example:
        decision = record_event(
            tenant_id="TENANT-84F03F7D",
            event_type="VOUCHER",
            event_subtype="created",
            source="whatsapp",
            metadata={"voucher_type": "Sales", "tally_guid": "xyz"}
        )
        if decision.is_blocked:
            raise HTTPException(402, "Credit limit reached. Please upgrade.")
    """
    metadata = metadata or {}

    # â”€â”€ Step 1: Rate the event â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    credits_consumed = compute_credits(event_type, event_subtype, metadata)

    # â”€â”€ Step 2: Get/create billing cycle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    cycle = find_or_create_active_cycle(tenant_id)

    if not cycle:
        # Fallback: can't determine cycle â€” allow but log error
        logger.error(f"[CreditEngine] No billing cycle for {tenant_id} â€” allowing event (ALLOWED).")
        return _fallback_decision(tenant_id, credits_consumed, event_type)

    billing_cycle_id = cycle["id"]
    max_credits      = cycle.get("max_credits", 500)

    # â”€â”€ Step 3: Get enforcement mode from plan â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    tenant_plan      = get_tenant_plan(tenant_id)
    enforcement_mode = "HARD_CAP"  # safe default
    plan_id          = cycle.get("plan_id", "starter")
    if tenant_plan and tenant_plan.get("plans"):
        enforcement_mode = tenant_plan["plans"].get("enforcement_mode", "HARD_CAP")

    # â”€â”€ Step 4: Pre-check for BLOCKED (HARD_CAP only, before writing) â”€â”€â”€â”€â”€â”€â”€
    # Fetch current summary to check if already at limit BEFORE consuming credits
    current_summary = _get_current_summary(tenant_id, billing_cycle_id)
    current_used    = current_summary.get("credits_used_total", 0.0) if current_summary else 0.0

    pre_status = _compute_status(current_used + credits_consumed, max_credits, enforcement_mode)

    if pre_status == CreditStatus.BLOCKED:
        # HARD_CAP: Don't write the event, don't consume credits. Just return BLOCKED.
        logger.warning(
            f"[CreditEngine] BLOCKED {event_type}/{event_subtype} for {tenant_id} "
            f"(used={current_used}/{max_credits})"
        )
        usage = _build_usage_summary(
            tenant_id, billing_cycle_id, cycle, current_summary, plan_id, enforcement_mode
        )
        return CreditDecision(
            event_id         = str(uuid.uuid4()),   # Pseudo ID â€” no DB row created
            tenant_id        = tenant_id,
            credits_consumed = 0,
            status           = CreditStatus.BLOCKED,
            usage            = usage,
            message          = _build_status_message(CreditStatus.BLOCKED, current_used, max_credits),
        )

    # â”€â”€ Step 5: Insert usage_event row (audit log) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    event_id = _insert_usage_event(
        tenant_id         = tenant_id,
        company_id        = company_id,
        billing_cycle_id  = billing_cycle_id,
        event_type        = event_type,
        event_subtype     = event_subtype,
        credits_consumed  = credits_consumed,
        source            = source,
        metadata          = metadata,
        status            = pre_status.value,  # Will be updated after atomic increment
    )

    # â”€â”€ Step 6: Atomically increment usage summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    updated_summary_row = _call_increment_atomic(
        tenant_id        = tenant_id,
        billing_cycle_id = billing_cycle_id,
        event_type       = event_type,
        credits          = credits_consumed,
    )

    # â”€â”€ Step 7: Compute final status from updated totals â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    final_used = 0.0
    if updated_summary_row:
        final_used = float(updated_summary_row.get("credits_used_total", current_used + credits_consumed))
    else:
        final_used = current_used + credits_consumed

    final_status = _compute_status(final_used, max_credits, enforcement_mode)
    message      = _build_status_message(final_status, final_used, max_credits)

    usage = _build_usage_summary(
        tenant_id, billing_cycle_id, cycle,
        updated_summary_row or current_summary,
        plan_id, enforcement_mode
    )

    logger.info(
        f"[CreditEngine] {event_type}/{event_subtype} | tenant={tenant_id} | "
        f"credits={credits_consumed} | used={final_used}/{max_credits} | {final_status}"
    )

    return CreditDecision(
        event_id         = event_id,
        tenant_id        = tenant_id,
        credits_consumed = credits_consumed,
        status           = final_status,
        usage            = usage,
        message          = message,
    )


def get_tenant_usage(tenant_id: str) -> UsageSummary:
    """
    Fetch the current billing cycle usage snapshot for a tenant.
    Used by admin and tenant-facing APIs.
    """
    cycle = find_or_create_active_cycle(tenant_id)
    if not cycle:
        return UsageSummary(tenant_id=tenant_id)

    billing_cycle_id = cycle["id"]
    tenant_plan      = get_tenant_plan(tenant_id)
    plan_id          = cycle.get("plan_id", "starter")
    enforcement_mode = "HARD_CAP"
    if tenant_plan and tenant_plan.get("plans"):
        enforcement_mode = tenant_plan["plans"].get("enforcement_mode", "HARD_CAP")

    current_summary = _get_current_summary(tenant_id, billing_cycle_id)
    return _build_usage_summary(
        tenant_id, billing_cycle_id, cycle, current_summary, plan_id, enforcement_mode
    )


# â”€â”€ Private helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _get_current_summary(
    tenant_id: str, billing_cycle_id: str
) -> Optional[Dict[str, Any]]:
    """Fetch the tenant_usage_summary row for this cycle."""
    try:
        result = (
            supabase.table("tenant_usage_summary")
            .select("*")
            .eq("billing_cycle_id", billing_cycle_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.error(f"[CreditEngine] _get_current_summary failed: {exc}")
        return None


def _build_usage_summary(
    tenant_id:        str,
    billing_cycle_id: str,
    cycle:            Dict[str, Any],
    summary_row:      Optional[Dict[str, Any]],
    plan_id:          str,
    enforcement_mode: str,
) -> UsageSummary:
    """Construct a UsageSummary from cycle + summary_row data."""
    max_credits  = cycle.get("max_credits", 500)
    used_total   = float((summary_row or {}).get("credits_used_total", 0))
    percent_used = (used_total / max_credits * 100) if max_credits > 0 else 0.0

    return UsageSummary(
        tenant_id              = tenant_id,
        billing_cycle_id       = billing_cycle_id,
        cycle_start            = cycle.get("cycle_start"),
        cycle_end              = cycle.get("cycle_end"),
        max_credits            = max_credits,
        credits_used_total     = used_total,
        credits_used_voucher   = float((summary_row or {}).get("credits_used_voucher", 0)),
        credits_used_document  = float((summary_row or {}).get("credits_used_document", 0)),
        credits_used_message   = float((summary_row or {}).get("credits_used_message", 0)),
        events_count_total     = int((summary_row or {}).get("events_count_total", 0)),
        percent_used           = round(percent_used, 2),
        plan_id                = plan_id,
        enforcement_mode       = enforcement_mode,
    )


def _fallback_decision(
    tenant_id: str, credits_consumed: float, event_type: str
) -> CreditDecision:
    """Return a safe ALLOWED decision when the cycle cannot be determined."""
    return CreditDecision(
        event_id         = str(uuid.uuid4()),
        tenant_id        = tenant_id,
        credits_consumed = credits_consumed,
        status           = CreditStatus.ALLOWED,
        usage            = UsageSummary(tenant_id=tenant_id),
        message          = "Usage recorded (billing cycle unavailable).",
    )


def check_credits_available(tenant_id: str, event_type: str) -> bool:
    """
    1. Get current billing_cycle for tenant
    2. Check credits_used_total < max_credits
    3. Return True if credits available, False if blocked
    """
    cycle = find_or_create_active_cycle(tenant_id)
    if not cycle:
        return True
        
    billing_cycle_id = cycle["id"]
    max_credits = cycle.get("max_credits", 500)
    
    tenant_plan = get_tenant_plan(tenant_id)
    enforcement_mode = "HARD_CAP"
    if tenant_plan and tenant_plan.get("plans"):
        enforcement_mode = tenant_plan["plans"].get("enforcement_mode", "HARD_CAP")
        
    current_summary = _get_current_summary(tenant_id, billing_cycle_id)
    current_used = current_summary.get("credits_used_total", 0.0) if current_summary else 0.0
    
    status = _compute_status(current_used, max_credits, enforcement_mode)
    return status != CreditStatus.BLOCKED

