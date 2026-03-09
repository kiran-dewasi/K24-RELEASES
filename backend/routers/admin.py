"""
Admin Router — Internal Admin Portal API
=========================================
Powers the internal admin portal for K24 operators.

All endpoints require the internal API key (X-API-Key header).
These routes MUST NOT be exposed to end-user tenants.

Endpoints:
    GET  /admin/tenants                        — List all tenants with plan + usage summary
    GET  /admin/tenants/{tenant_id}/usage      — Detailed usage + events for one tenant
    GET  /admin/plans                          — List all plans
    GET  /admin/credit-rules                   — List all credit rules
    POST /admin/credit-rules                   — Create a new credit rule
    PUT  /admin/credit-rules/{rule_id}         — Update an existing credit rule
    POST /admin/tenants/{tenant_id}/assign-plan — Assign a plan to a tenant
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from backend.database.supabase_client import supabase
from backend.credit_engine import get_tenant_usage
from backend.credit_engine.rating import invalidate_rule_cache
from backend.dependencies import get_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin Portal"],
    dependencies=[Depends(get_api_key)],
)


# ── Pydantic Schemas ─────────────────────────────────────────────────────────

class CreditRuleCreate(BaseModel):
    event_type:    str
    event_subtype: str
    credits:       float
    description:   Optional[str] = None
    effective_from: Optional[str] = None   # ISO datetime string
    effective_to:   Optional[str] = None   # ISO datetime string

class CreditRuleUpdate(BaseModel):
    credits:       Optional[float] = None
    description:   Optional[str]  = None
    is_active:     Optional[bool]  = None
    effective_to:  Optional[str]   = None

class AssignPlanRequest(BaseModel):
    plan_id:       str
    status:        str = "active"         # trial | active | suspended
    notes:         Optional[str] = None


# ── Helper: fetch from Supabase with error handling ──────────────────────────

def _supabase_get(table: str, query_fn) -> List[Dict[str, Any]]:
    """Run a query builder function and return rows or []."""
    try:
        result = query_fn(supabase.table(table)).execute()
        return result.data or []
    except Exception as exc:
        logger.error(f"[AdminRouter] Supabase fetch from '{table}' failed: {exc}")
        return []


# ── GET /admin/tenants ───────────────────────────────────────────────────────

@router.get("/tenants", summary="List all tenants with plan + usage summary")
async def list_tenants(
    search:  Optional[str] = Query(None, description="Filter by company name (case-insensitive)"),
    plan_id: Optional[str] = Query(None, description="Filter by plan ID"),
    limit:   int           = Query(50, le=200),
):
    """
    Returns a paginated list of all tenants with their:
    - Plan name and status
    - Current billing cycle usage (credits used vs limit + %)
    - Company count
    - Next cycle end date
    """
    # Fetch all tenants
    tenants = _supabase_get("tenants", lambda t: t.select("id,company_name,created_at").limit(limit))

    if not tenants:
        return {"tenants": [], "total": 0}

    # Optionally filter by name
    if search:
        search_lower = search.lower()
        tenants = [t for t in tenants if search_lower in (t.get("company_name") or "").lower()]

    # Fetch tenant plans in one call
    tenant_plan_rows = _supabase_get(
        "tenant_plans",
        lambda t: t.select("tenant_id,plan_id,status,current_period_end,plans(display_name,max_credits_per_cycle,enforcement_mode)").limit(500)
    )
    plan_map: Dict[str, Dict] = {row["tenant_id"]: row for row in tenant_plan_rows}

    # Filter by plan if requested
    if plan_id:
        tenants = [t for t in tenants if plan_map.get(t["id"], {}).get("plan_id") == plan_id]

    # Fetch billing cycle summaries (active cycles only)
    billing_cycles = _supabase_get(
        "billing_cycles",
        lambda t: t.select("id,tenant_id,max_credits").eq("status", "active").limit(500)
    )
    cycle_map: Dict[str, Dict] = {row["tenant_id"]: row for row in billing_cycles}

    # Fetch usage summaries for active cycles
    cycle_ids = [c["id"] for c in billing_cycles]
    usage_summaries: List[Dict] = []
    if cycle_ids:
        # Supabase REST doesn't support IN directly via our HTTP client — fetch all and filter
        all_summaries = _supabase_get(
            "tenant_usage_summary",
            lambda t: t.select("billing_cycle_id,tenant_id,credits_used_total,events_count_total").limit(500)
        )
        # Index by billing_cycle_id
        summary_by_cycle = {row["billing_cycle_id"]: row for row in all_summaries}
    else:
        summary_by_cycle = {}

    # Count companies per tenant
    companies = _supabase_get(
        "companies",
        lambda t: t.select("tenant_id").limit(1000)
    )
    company_count_map: Dict[str, int] = {}
    for comp in companies:
        tid = comp.get("tenant_id", "")
        company_count_map[tid] = company_count_map.get(tid, 0) + 1

    # Assemble response
    result_tenants = []
    for tenant in tenants:
        tid         = tenant["id"]
        plan_row    = plan_map.get(tid, {})
        cycle       = cycle_map.get(tid, {})
        cycle_id    = cycle.get("id")
        summary     = summary_by_cycle.get(cycle_id, {}) if cycle_id else {}
        plan_info   = plan_row.get("plans") or {}

        max_credits  = cycle.get("max_credits") or plan_info.get("max_credits_per_cycle") or 500
        credits_used = float(summary.get("credits_used_total", 0))
        pct          = round(credits_used / max_credits * 100, 1) if max_credits else 0

        result_tenants.append({
            "tenant_id":         tid,
            "company_name":      tenant.get("company_name", "—"),
            "plan_id":           plan_row.get("plan_id", "starter"),
            "plan_name":         plan_info.get("display_name", "Starter"),
            "plan_status":       plan_row.get("status", "trial"),
            "enforcement_mode":  plan_info.get("enforcement_mode", "HARD_CAP"),
            "companies_count":   company_count_map.get(tid, 0),
            "credits_used":      credits_used,
            "max_credits":       max_credits,
            "percent_used":      pct,
            "next_cycle_end":    plan_row.get("current_period_end"),
            "created_at":        tenant.get("created_at"),
        })

    return {"tenants": result_tenants, "total": len(result_tenants)}


# ── GET /admin/tenants/{tenant_id}/usage ─────────────────────────────────────

@router.get("/tenants/{tenant_id}/usage", summary="Detailed usage report for one tenant")
async def get_tenant_detail(
    tenant_id:     str,
    events_limit:  int = Query(20, le=100, description="Number of recent events to return"),
):
    """
    Full usage breakdown for a single tenant including:
    - Plan details and limits
    - Current cycle usage totals + breakdown by category
    - Recent usage_events (with metadata)
    - LLM usage summary (tokens + estimated cost + top workflows)
    """
    # Tenant basics
    tenants = _supabase_get(
        "tenants",
        lambda t: t.select("id,company_name,whatsapp_number,created_at").eq("id", tenant_id).limit(1)
    )
    if not tenants:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_id}' not found.")
    tenant = tenants[0]

    # Plan
    plan_rows = _supabase_get(
        "tenant_plans",
        lambda t: t.select("*,plans(*)").eq("tenant_id", tenant_id).limit(1)
    )
    plan_row  = plan_rows[0] if plan_rows else {}
    plan_info = plan_row.get("plans") or {}

    # Active billing cycle
    cycles = _supabase_get(
        "billing_cycles",
        lambda t: t.select("*").eq("tenant_id", tenant_id).eq("status", "active").limit(1)
    )
    cycle    = cycles[0] if cycles else {}
    cycle_id = cycle.get("id")

    # Usage summary
    summary_rows = _supabase_get(
        "tenant_usage_summary",
        lambda t: t.select("*").eq("billing_cycle_id", cycle_id).limit(1)
    ) if cycle_id else []
    summary = summary_rows[0] if summary_rows else {}

    # Recent usage events
    event_rows = []
    if cycle_id:
        event_rows = _supabase_get(
            "usage_events",
            lambda t: (
                t.select("id,event_type,event_subtype,credits_consumed,source,status,metadata_json,created_at")
                 .eq("billing_cycle_id", cycle_id)
                 .order("created_at", desc=True)
                 .limit(events_limit)
            )
        )

    # LLM usage summary for this cycle (aggregate by workflow)
    llm_summary = _build_llm_summary(tenant_id, cycle.get("cycle_start"), cycle.get("cycle_end"))

    max_credits  = cycle.get("max_credits") or plan_info.get("max_credits_per_cycle") or 500
    credits_used = float(summary.get("credits_used_total", 0))

    return {
        "tenant": {
            "id":               tenant["id"],
            "company_name":     tenant.get("company_name"),
            "whatsapp_number":  tenant.get("whatsapp_number"),
            "created_at":       tenant.get("created_at"),
        },
        "plan": {
            "plan_id":          plan_row.get("plan_id", "—"),
            "plan_name":        plan_info.get("display_name", "—"),
            "status":           plan_row.get("status", "—"),
            "enforcement_mode": plan_info.get("enforcement_mode", "HARD_CAP"),
            "max_credits":      max_credits,
            "max_companies":    plan_info.get("max_companies", 1),
            "features":         plan_info.get("features_json", {}),
            "current_period_end": plan_row.get("current_period_end"),
        },
        "current_cycle": {
            "id":                  cycle_id,
            "cycle_start":         cycle.get("cycle_start"),
            "cycle_end":           cycle.get("cycle_end"),
            "max_credits":         max_credits,
            "credits_used_total":  credits_used,
            "credits_used_voucher":  float(summary.get("credits_used_voucher", 0)),
            "credits_used_document": float(summary.get("credits_used_document", 0)),
            "credits_used_message":  float(summary.get("credits_used_message", 0)),
            "events_count_total":    int(summary.get("events_count_total", 0)),
            "events_count_voucher":  int(summary.get("events_count_voucher", 0)),
            "events_count_document": int(summary.get("events_count_document", 0)),
            "events_count_message":  int(summary.get("events_count_message", 0)),
            "percent_used":          round(credits_used / max_credits * 100, 1) if max_credits else 0,
        },
        "recent_events": event_rows,
        "llm_summary":   llm_summary,
    }


def _build_llm_summary(
    tenant_id: str,
    cycle_start: Optional[str],
    cycle_end: Optional[str],
) -> Dict[str, Any]:
    """Aggregate LLM call data for the current cycle."""
    try:
        q = lambda t: t.select(
            "model,workflow,tokens_input,tokens_output,cost_estimated_usd,duration_ms"
        ).eq("tenant_id", tenant_id).limit(1000)

        llm_rows = _supabase_get("llm_calls", q)

        total_tokens_in  = sum(r.get("tokens_input", 0) for r in llm_rows)
        total_tokens_out = sum(r.get("tokens_output", 0) for r in llm_rows)
        total_cost       = sum(float(r.get("cost_estimated_usd", 0)) for r in llm_rows)
        total_calls      = len(llm_rows)

        # Group by workflow
        workflow_map: Dict[str, Dict] = {}
        for r in llm_rows:
            wf = r.get("workflow") or "unknown"
            if wf not in workflow_map:
                workflow_map[wf] = {"calls": 0, "tokens": 0, "cost_usd": 0.0}
            workflow_map[wf]["calls"]     += 1
            workflow_map[wf]["tokens"]    += (r.get("tokens_input", 0) + r.get("tokens_output", 0))
            workflow_map[wf]["cost_usd"]  += float(r.get("cost_estimated_usd", 0))

        # Sort by token burn desc
        top_workflows = sorted(
            [{"workflow": k, **v} for k, v in workflow_map.items()],
            key=lambda x: x["tokens"],
            reverse=True
        )[:10]

        return {
            "total_calls":       total_calls,
            "total_tokens_in":   total_tokens_in,
            "total_tokens_out":  total_tokens_out,
            "total_tokens":      total_tokens_in + total_tokens_out,
            "total_cost_usd":    round(total_cost, 6),
            "top_workflows":     top_workflows,
        }
    except Exception as exc:
        logger.warning(f"[AdminRouter] LLM summary failed for {tenant_id}: {exc}")
        return {"total_calls": 0, "total_tokens_in": 0, "total_tokens_out": 0, "total_cost_usd": 0}


# ── GET /admin/plans ─────────────────────────────────────────────────────────

@router.get("/plans", summary="List all plans")
async def list_plans():
    """Returns all K24 plans with their limits and feature flags."""
    plans = _supabase_get("plans", lambda t: t.select("*").order("price_monthly_paise"))
    return {"plans": plans}


# ── GET /admin/credit-rules ──────────────────────────────────────────────────

@router.get("/credit-rules", summary="List all credit rules")
async def list_credit_rules():
    """
    Returns all credit rules (active and inactive).
    These control how many credits each event type costs.
    """
    rules = _supabase_get(
        "credit_rules",
        lambda t: t.select("*").order("event_type").order("event_subtype")
    )
    return {"credit_rules": rules, "total": len(rules)}


# ── POST /admin/credit-rules ─────────────────────────────────────────────────

@router.post("/credit-rules", summary="Create a new credit rule")
async def create_credit_rule(req: CreditRuleCreate):
    """
    Add a new credit rule. Use effective_from / effective_to to schedule
    future rule changes without downtime.
    After creation, the in-process rule cache is automatically invalidated.
    """
    try:
        payload = {
            "event_type":    req.event_type,
            "event_subtype": req.event_subtype,
            "credits":       req.credits,
            "description":   req.description,
            "effective_from": req.effective_from or datetime.now(timezone.utc).isoformat(),
            "effective_to":   req.effective_to,
        }
        result = supabase.table("credit_rules").insert(payload).execute()
        invalidate_rule_cache()   # Force reload on next request
        rows = result.data or []
        return {"credit_rule": rows[0] if rows else payload, "cache_invalidated": True}
    except Exception as exc:
        logger.error(f"[AdminRouter] create_credit_rule failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ── PUT /admin/credit-rules/{rule_id} ────────────────────────────────────────

@router.put("/credit-rules/{rule_id}", summary="Update an existing credit rule")
async def update_credit_rule(rule_id: str, req: CreditRuleUpdate):
    """
    Update credits, description, active status, or effective_to for a rule.
    Cache is invalidated so the new value takes effect within seconds.
    """
    try:
        payload = {k: v for k, v in req.dict().items() if v is not None}
        if not payload:
            raise HTTPException(status_code=422, detail="No fields to update.")

        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = (
            supabase.table("credit_rules")
            .update(payload)
            .eq("id", rule_id)
            .execute()
        )
        invalidate_rule_cache()
        rows = result.data or []
        return {"credit_rule": rows[0] if rows else {"id": rule_id}, "cache_invalidated": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[AdminRouter] update_credit_rule failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ── POST /admin/tenants/{tenant_id}/assign-plan ──────────────────────────────

@router.post("/tenants/{tenant_id}/assign-plan", summary="Assign or change a tenant's plan")
async def assign_plan_to_tenant(tenant_id: str, req: AssignPlanRequest):
    """
    Assign a plan to a tenant. If the tenant already has an active plan,
    the old one is marked 'cancelled' and a new row is created.

    This is how you upgrade / downgrade a tenant's plan.
    """
    try:
        # Deactivate existing active/trial plan
        supabase.table("tenant_plans").update({"status": "cancelled"}).eq("tenant_id", tenant_id).execute()

        # Fetch plan details for period calculation
        plan_rows = _supabase_get("plans", lambda t: t.select("*").eq("id", req.plan_id).limit(1))
        if not plan_rows:
            raise HTTPException(status_code=404, detail=f"Plan '{req.plan_id}' not found.")
        plan = plan_rows[0]

        now = datetime.now(timezone.utc)
        period_end = now.replace(month=now.month + 1) if now.month < 12 else now.replace(year=now.year + 1, month=1)

        result = supabase.table("tenant_plans").insert({
            "tenant_id":             tenant_id,
            "plan_id":               req.plan_id,
            "status":                req.status,
            "current_period_start":  now.isoformat(),
            "current_period_end":    period_end.isoformat(),
            "notes":                 req.notes,
        }).execute()

        rows = result.data or []
        logger.info(f"[AdminRouter] Tenant {tenant_id} assigned to plan {req.plan_id}")
        return {
            "success":    True,
            "tenant_id":  tenant_id,
            "plan_id":    req.plan_id,
            "status":     req.status,
            "tenant_plan": rows[0] if rows else {},
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[AdminRouter] assign_plan_to_tenant failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
