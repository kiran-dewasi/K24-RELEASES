"""
Cloud Billing Router
====================
Internal-only endpoints for credit entitlement checks and event recording.
All endpoints require X-Internal-Key header matching BILLING_INTERNAL_KEY env var.

These are called by:
  - cloud-backend own services (e.g. whatsapp_cloud.py)
  - desktop local backend (future — Phase N)

CREDIT ENGINE NOTE:
  The desktop credit engine (backend/credit_engine/) cannot be imported here
  (separate deployment).  This module reimplements the same DB logic against
  the same Supabase tables, keeping identical semantics.
  The single source of truth is the DB schema / Postgres functions.
"""

import logging
import os
import uuid
import calendar
import httpx
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database.supabase_client import get_supabase_client
from deps import require_internal_key

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Billing (internal)"])

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CheckEntitlementRequest(BaseModel):
    tenant_id: str
    event_type: Literal["VOUCHER", "DOCUMENT", "MESSAGE"]
    event_subtype: str


class CheckEntitlementResponse(BaseModel):
    allowed: bool
    reason: Literal["OK", "TRIAL_EXPIRED", "CREDIT_LIMIT", "SUBSCRIPTION_EXPIRED", "UNKNOWN_TENANT"]
    credits_used: float
    credits_limit: Optional[float]
    subscription_status: Optional[str]


class RecordEventRequest(BaseModel):
    tenant_id: str
    event_type: Literal["VOUCHER", "DOCUMENT", "MESSAGE"]
    event_subtype: str
    company_id: Optional[int] = None
    source: str = "cloud"
    metadata: Optional[Dict[str, Any]] = None


class RecordEventResponse(BaseModel):
    event_id: str
    status: str            # "ALLOWED" | "NEAR_LIMIT" | "OVER_LIMIT" | "BLOCKED"
    credits_consumed: float
    credits_used: float
    credits_limit: float
    message: str


# ---------------------------------------------------------------------------
# Internal credit engine helpers (cloud-side reimplementation)
# ---------------------------------------------------------------------------

NEAR_LIMIT_THRESHOLD = 0.80

# -- Rule cache (keyed by "EVENT_TYPE::event_subtype") ----------------------
_RULE_CACHE: Dict[str, float] = {}
_CACHE_LOADED_AT: Optional[datetime] = None
_CACHE_TTL_SECONDS: int = 300


def _is_cache_stale() -> bool:
    if _CACHE_LOADED_AT is None:
        return True
    return (datetime.now(timezone.utc) - _CACHE_LOADED_AT).total_seconds() > _CACHE_TTL_SECONDS


def _load_rules() -> None:
    global _RULE_CACHE, _CACHE_LOADED_AT
    try:
        sb = get_supabase_client()
        result = sb.table("credit_rules").select("event_type,event_subtype,credits").eq("is_active", True).execute()
        now_str = datetime.now(timezone.utc).isoformat()
        cache: Dict[str, float] = {}
        for row in result.data or []:
            eff_from = row.get("effective_from") or ""
            eff_to = row.get("effective_to")
            if eff_from and eff_from > now_str:
                continue
            if eff_to and eff_to < now_str:
                continue
            cache[f"{row['event_type']}::{row['event_subtype']}"] = float(row["credits"])
        _RULE_CACHE = cache
        _CACHE_LOADED_AT = datetime.now(timezone.utc)
        logger.info(f"[Billing] Loaded {len(_RULE_CACHE)} credit rules")
    except Exception as exc:
        logger.error(f"[Billing] Failed to load credit rules: {exc}")


def _compute_credits(event_type: str, event_subtype: str) -> float:
    if _is_cache_stale():
        _load_rules()
    return _RULE_CACHE.get(f"{event_type}::{event_subtype}", 1.0)


def _month_boundaries(now: datetime):
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day = calendar.monthrange(now.year, now.month)[1]
    end = start.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def _get_active_cycle(tenant_id: str) -> Optional[Dict[str, Any]]:
    try:
        sb = get_supabase_client()
        result = sb.table("billing_cycles").select("*").eq("tenant_id", tenant_id).eq("status", "active").limit(1).execute()
        rows = result.data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.error(f"[Billing] get_active_cycle failed: {exc}")
        return None


def _find_or_create_cycle(tenant_id: str, tenant_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    cycle = _get_active_cycle(tenant_id)
    if cycle:
        return cycle

    # Derive max_credits and plan_id from subscription status
    status = tenant_config.get("subscription_status", "trial")
    trial_limit = int(tenant_config.get("trial_credit_limit") or 90)
    if status == "active":
        plan_id = "grace_active"
        max_credits = 1000
    elif status == "trial":
        plan_id = "trial"
        max_credits = trial_limit
    else:
        return None

    now = datetime.now(timezone.utc)
    cycle_start, cycle_end = _month_boundaries(now)
    try:
        sb = get_supabase_client()
        result = sb.table("billing_cycles").insert({
            "tenant_id":   tenant_id,
            "plan_id":     plan_id,
            "cycle_start": cycle_start.isoformat(),
            "cycle_end":   cycle_end.isoformat(),
            "status":      "active",
            "max_credits": max_credits,
        }).execute()
        rows = result.data or []
        return rows[0] if rows else _get_active_cycle(tenant_id)
    except Exception as exc:
        logger.warning(f"[Billing] create cycle conflict for {tenant_id}: {exc}")
        return _get_active_cycle(tenant_id)


def _get_usage_summary(tenant_id: str, billing_cycle_id: str) -> Optional[Dict[str, Any]]:
    try:
        sb = get_supabase_client()
        result = sb.table("tenant_usage_summary").select("*").eq("billing_cycle_id", billing_cycle_id).limit(1).execute()
        rows = result.data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.error(f"[Billing] _get_usage_summary failed: {exc}")
        return None


def _call_increment_atomic(tenant_id: str, billing_cycle_id: str, event_type: str, credits: float) -> Optional[Dict[str, Any]]:
    try:
        supabase_url = os.getenv("SUPABASE_URL", "")
        service_key = (
            os.getenv("SUPABASE_SERVICE_KEY") or
            os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
            os.getenv("SUPABASE_ANON_KEY", "")
        )
        url = f"{supabase_url}/rest/v1/rpc/increment_usage_atomic"
        headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
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
        logger.error(f"[Billing] increment_usage_atomic HTTP {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as exc:
        logger.error(f"[Billing] increment_usage_atomic exception: {exc}")
        return None


def _compute_status(credits_used: float, max_credits: int) -> str:
    if max_credits <= 0:
        return "ALLOWED"
    ratio = credits_used / max_credits
    if ratio < NEAR_LIMIT_THRESHOLD:
        return "ALLOWED"
    if ratio < 1.0:
        return "NEAR_LIMIT"
    return "BLOCKED"   # Cloud engine always HARD_CAP for now


def _status_message(status: str, credits_used: float, max_credits: int) -> str:
    remaining = max(0, max_credits - credits_used)
    if status == "ALLOWED":
        return f"{remaining} credits remaining this cycle."
    if status == "NEAR_LIMIT":
        return f"Warning: Only {remaining:.0f} credits left ({credits_used}/{max_credits} used)."
    if status in ("BLOCKED", "OVER_LIMIT"):
        return f"Credit limit reached ({credits_used:.0f}/{max_credits}). Please upgrade."
    return ""


def _insert_usage_event(
    tenant_id: str,
    company_id: Optional[int],
    billing_cycle_id: str,
    event_type: str,
    event_subtype: str,
    credits_consumed: float,
    source: str,
    metadata: Dict[str, Any],
    status: str,
) -> str:
    try:
        sb = get_supabase_client()
        result = sb.table("usage_events").insert({
            "tenant_id":        tenant_id,
            "company_id":       company_id,
            "billing_cycle_id": billing_cycle_id,
            "event_type":       event_type,
            "event_subtype":    event_subtype,
            "credits_consumed": credits_consumed,
            "source":           source,
            "metadata_json":    metadata,
            "status":           status,
        }).execute()
        rows = result.data or []
        return rows[0]["id"] if rows else str(uuid.uuid4())
    except Exception as exc:
        logger.error(f"[Billing] insert usage_event failed: {exc}")
        return str(uuid.uuid4())


def _record_event_internal(
    tenant_id: str,
    event_type: str,
    event_subtype: str,
    company_id: Optional[int],
    source: str,
    metadata: Dict[str, Any],
    tenant_config: Dict[str, Any],
) -> RecordEventResponse:
    """
    Core credit recording logic.  Mirrors backend/credit_engine/engine.py:record_event().
    Writes to usage_events and calls increment_usage_atomic.
    """
    credits_consumed = _compute_credits(event_type, event_subtype)
    cycle = _find_or_create_cycle(tenant_id, tenant_config)

    if not cycle:
        # Fallback: no cycle available – allow but log
        logger.error(f"[Billing] No billing cycle for {tenant_id} – allowing (fallback)")
        return RecordEventResponse(
            event_id=str(uuid.uuid4()),
            status="ALLOWED",
            credits_consumed=credits_consumed,
            credits_used=0.0,
            credits_limit=0.0,
            message="Allowed (billing cycle unavailable).",
        )

    billing_cycle_id = cycle["id"]
    max_credits = cycle.get("max_credits", 90)

    # Pre-check: if already BLOCKED, don't write
    current_summary = _get_usage_summary(tenant_id, billing_cycle_id)
    current_used = float((current_summary or {}).get("credits_used_total", 0.0))

    pre_status = _compute_status(current_used + credits_consumed, max_credits)
    if pre_status == "BLOCKED":
        logger.warning(f"[Billing] BLOCKED {event_type}/{event_subtype} for {tenant_id}")
        return RecordEventResponse(
            event_id=str(uuid.uuid4()),
            status="BLOCKED",
            credits_consumed=0.0,
            credits_used=current_used,
            credits_limit=float(max_credits),
            message=_status_message("BLOCKED", current_used, max_credits),
        )

    # Insert audit row
    event_id = _insert_usage_event(
        tenant_id=tenant_id,
        company_id=company_id,
        billing_cycle_id=billing_cycle_id,
        event_type=event_type,
        event_subtype=event_subtype,
        credits_consumed=credits_consumed,
        source=source,
        metadata=metadata,
        status=pre_status,
    )

    # Atomic increment
    updated = _call_increment_atomic(tenant_id, billing_cycle_id, event_type, credits_consumed)
    final_used = float((updated or {}).get("credits_used_total", current_used + credits_consumed))
    final_status = _compute_status(final_used, max_credits)

    logger.info(
        f"[Billing] {event_type}/{event_subtype} | tenant={tenant_id} | "
        f"credits={credits_consumed} | used={final_used}/{max_credits} | {final_status}"
    )

    return RecordEventResponse(
        event_id=event_id,
        status=final_status,
        credits_consumed=credits_consumed,
        credits_used=final_used,
        credits_limit=float(max_credits),
        message=_status_message(final_status, final_used, max_credits),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/check-entitlement", response_model=CheckEntitlementResponse)
async def check_entitlement(
    req: CheckEntitlementRequest,
    _: bool = Depends(require_internal_key),
) -> CheckEntitlementResponse:
    """
    Check whether a tenant is entitled to perform the requested event.
    Does NOT consume credits.  Call record-event separately after work is done.
    """
    try:
        sb = get_supabase_client()
        result = sb.table("tenant_config").select(
            "tenant_id, subscription_status, trial_ends_at, trial_credit_limit"
        ).eq("tenant_id", req.tenant_id).limit(1).execute()

        if not result.data:
            return CheckEntitlementResponse(
                allowed=False,
                reason="UNKNOWN_TENANT",
                credits_used=0.0,
                credits_limit=None,
                subscription_status=None,
            )

        config = result.data[0]
        status = config.get("subscription_status")
        trial_ends_at = config.get("trial_ends_at")
        trial_credit_limit = int(config.get("trial_credit_limit") or 90)
        now = datetime.now(timezone.utc)

        if status in ("expired", "cancelled"):
            return CheckEntitlementResponse(
                allowed=False,
                reason="SUBSCRIPTION_EXPIRED",
                credits_used=0.0,
                credits_limit=None,
                subscription_status=status,
            )

        if status == "trial" and trial_ends_at:
            try:
                trial_end_dt = datetime.fromisoformat(trial_ends_at.replace("Z", "+00:00"))
                if trial_end_dt < now:
                    return CheckEntitlementResponse(
                        allowed=False,
                        reason="TRIAL_EXPIRED",
                        credits_used=0.0,
                        credits_limit=float(trial_credit_limit),
                        subscription_status=status,
                    )
            except (ValueError, AttributeError):
                pass  # Unparseable date → fail open

        # Credit limit check
        credits_used = 0.0
        credits_limit: Optional[float] = None

        cycle_result = sb.table("billing_cycles").select("id, max_credits").eq(
            "tenant_id", req.tenant_id
        ).eq("status", "active").order("created_at", desc=True).limit(1).execute()

        if cycle_result.data:
            cycle = cycle_result.data[0]
            cycle_id = cycle["id"]
            max_credits = cycle.get("max_credits", trial_credit_limit)
            credits_limit = float(max_credits)

            summary_result = sb.table("tenant_usage_summary").select(
                "credits_used_total"
            ).eq("tenant_id", req.tenant_id).eq("billing_cycle_id", cycle_id).limit(1).execute()

            if summary_result.data:
                credits_used = float(summary_result.data[0].get("credits_used_total") or 0)

            if status == "trial" and credits_used >= (credits_limit or trial_credit_limit):
                return CheckEntitlementResponse(
                    allowed=False,
                    reason="CREDIT_LIMIT",
                    credits_used=credits_used,
                    credits_limit=credits_limit,
                    subscription_status=status,
                )

        return CheckEntitlementResponse(
            allowed=True,
            reason="OK",
            credits_used=credits_used,
            credits_limit=credits_limit,
            subscription_status=status,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[Billing] check-entitlement error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Billing check failed")


@router.post("/record-event", response_model=RecordEventResponse)
async def record_event_endpoint(
    req: RecordEventRequest,
    _: bool = Depends(require_internal_key),
) -> RecordEventResponse:
    """
    Record a billing event and atomically update tenant_usage_summary.
    Returns the credit decision (ALLOWED / NEAR_LIMIT / OVER_LIMIT / BLOCKED).
    """
    try:
        sb = get_supabase_client()
        config_result = sb.table("tenant_config").select(
            "tenant_id, subscription_status, trial_credit_limit"
        ).eq("tenant_id", req.tenant_id).limit(1).execute()

        if not config_result.data:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant_config = config_result.data[0]

        return _record_event_internal(
            tenant_id=req.tenant_id,
            event_type=req.event_type,
            event_subtype=req.event_subtype,
            company_id=req.company_id,
            source=req.source,
            metadata=req.metadata or {},
            tenant_config=tenant_config,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[Billing] record-event error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Billing record failed")
