"""
Usage Router — Internal Event Recording API
============================================
Called by internal flows (WhatsApp, Kittu, Tally sync) when a business
event occurs. This is the HTTP entry point to the credit engine.

Endpoints:
    POST /internal/usage/event       — Record an event, get credit decision
    GET  /internal/usage/tenant/{id} — Fetch current usage for a tenant
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from credit_engine import record_event, get_tenant_usage, CreditDecision
from credit_engine.models import EventType, EventSubtype
from dependencies import get_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/internal/usage",
    tags=["Usage (Internal)"],
)


# ── Request / Response Schemas ───────────────────────────────────────────────

class RecordEventRequest(BaseModel):
    """
    Payload to record a business event and consume credits.
    Called by internal services — NOT exposed to end users.
    """
    tenant_id:     str
    event_type:    str         # VOUCHER | DOCUMENT | MESSAGE
    event_subtype: str         # created | updated | page_processed | action | info_query
    company_id:    Optional[int]          = None
    source:        str                    = "api"
    metadata:      Dict[str, Any]         = {}

    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id":     "TENANT-84F03F7D",
                "event_type":    "VOUCHER",
                "event_subtype": "created",
                "company_id":    1,
                "source":        "whatsapp",
                "metadata": {
                    "voucher_type": "Sales",
                    "tally_guid":   "abc-123",
                    "amount":       15000
                }
            }
        }


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/event",
    response_model=None,
    summary="Record a business event and apply credit accounting",
)
async def record_usage_event(req: RecordEventRequest):
    """
    Record a business event (voucher created, document processed, message action)
    and atomically apply credit accounting for the tenant's current billing cycle.

    Returns a CreditDecision with:
      - status: ALLOWED | NEAR_LIMIT | OVER_LIMIT | BLOCKED
      - credits_consumed: how many credits this event cost
      - usage: full snapshot of the tenant's current billing cycle usage
      - message: human-readable note (for upgrade prompts)

    Callers MUST check the returned status:
      - BLOCKED    → tenant exceeded HARD_CAP limit; abort the action.
      - NEAR_LIMIT → proceed but show an upgrade nudge to the user.
      - OVER_LIMIT → proceed but flag for follow-up (SOFT_CAP plans).
      - ALLOWED    → proceed normally.
    """
    try:
        # Validate event_type and event_subtype
        valid_types    = {e.value for e in EventType}
        valid_subtypes = {e.value for e in EventSubtype}

        if req.event_type not in valid_types:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid event_type '{req.event_type}'. Must be one of: {valid_types}"
            )
        if req.event_subtype not in valid_subtypes:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid event_subtype '{req.event_subtype}'. Must be one of: {valid_subtypes}"
            )

        decision: CreditDecision = record_event(
            tenant_id     = req.tenant_id,
            event_type    = req.event_type,
            event_subtype = req.event_subtype,
            company_id    = req.company_id,
            source        = req.source,
            metadata      = req.metadata,
        )

        return {
            "event_id":         decision.event_id,
            "tenant_id":        decision.tenant_id,
            "credits_consumed": decision.credits_consumed,
            "status":           decision.status.value,
            "message":          decision.message,
            "is_blocked":       decision.is_blocked,
            "should_warn":      decision.should_warn,
            "usage": {
                "credits_used_total":     decision.usage.credits_used_total,
                "credits_used_voucher":   decision.usage.credits_used_voucher,
                "credits_used_document":  decision.usage.credits_used_document,
                "credits_used_message":   decision.usage.credits_used_message,
                "max_credits":            decision.usage.max_credits,
                "percent_used":           decision.usage.percent_used,
                "events_count_total":     decision.usage.events_count_total,
                "plan_id":                decision.usage.plan_id,
                "cycle_start":            str(decision.usage.cycle_start) if decision.usage.cycle_start else None,
                "cycle_end":              str(decision.usage.cycle_end) if decision.usage.cycle_end else None,
            }
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[UsageRouter] record_usage_event error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to record usage event.")


@router.get(
    "/tenant/{tenant_id}",
    summary="Get current usage snapshot for a tenant",
)
async def get_usage_snapshot(tenant_id: str):
    """
    Returns the current billing cycle usage summary for a given tenant.
    Safe to call frequently — reads from the pre-aggregated tenant_usage_summary table.
    """
    try:
        usage = get_tenant_usage(tenant_id)
        return {
            "tenant_id":              usage.tenant_id,
            "plan_id":                usage.plan_id,
            "enforcement_mode":       usage.enforcement_mode,
            "billing_cycle_id":       usage.billing_cycle_id,
            "cycle_start":            str(usage.cycle_start) if usage.cycle_start else None,
            "cycle_end":              str(usage.cycle_end) if usage.cycle_end else None,
            "max_credits":            usage.max_credits,
            "credits_used_total":     usage.credits_used_total,
            "credits_used_voucher":   usage.credits_used_voucher,
            "credits_used_document":  usage.credits_used_document,
            "credits_used_message":   usage.credits_used_message,
            "events_count_total":     usage.events_count_total,
            "percent_used":           usage.percent_used,
        }
    except Exception as exc:
        logger.error(f"[UsageRouter] get_usage_snapshot error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve usage snapshot.")
