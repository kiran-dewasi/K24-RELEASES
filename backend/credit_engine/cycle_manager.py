"""
Credit Engine â€” Billing Cycle Manager
======================================
Manages `billing_cycles` rows in Supabase.

Responsibilities:
  - Find the currently active billing cycle for a tenant.
  - Create a new cycle if none exists (first usage of the month).
  - Determine cycle start/end from the tenant's plan period or calendar month.

Rule: There is ALWAYS at most one row with status='active' per tenant
      (enforced by a UNIQUE partial index on billing_cycles in Postgres).
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import calendar

from database.supabase_client import supabase

logger = logging.getLogger(__name__)


def _month_boundaries(now: datetime) -> tuple[datetime, datetime]:
    """
    Returns (start_of_month, end_of_month) for the given datetime.
    end_of_month is the first second of the NEXT month (exclusive upper bound).

    Example: March 2026 â†’ (2026-03-01T00:00:00Z, 2026-04-01T00:00:00Z)
    """
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Last day of the month
    last_day = calendar.monthrange(now.year, now.month)[1]
    end = start.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def get_active_cycle(tenant_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns the current active billing_cycles row for the tenant,
    or None if no active cycle exists.
    """
    try:
        result = (
            supabase.table("billing_cycles")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.error(f"[CycleManager] get_active_cycle failed for {tenant_id}: {exc}")
        return None


def get_tenant_plan(tenant_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the active tenant_plans row joined with plans for this tenant.
    Returns None if the tenant has no plan configured.
    """
    try:
        result = (
            supabase.table("tenant_plans")
            .select("*, plans(*)")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.error(f"[CycleManager] get_tenant_plan failed for {tenant_id}: {exc}")
        return None


def create_billing_cycle(
    tenant_id:   str,
    plan_id:     str,
    max_credits: int,
    cycle_start: datetime,
    cycle_end:   datetime,
) -> Optional[Dict[str, Any]]:
    """
    Insert a new billing_cycle row for the tenant.
    The Postgres UNIQUE partial index guarantees at most one 'active' row
    per tenant even under concurrent requests.
    """
    try:
        result = (
            supabase.table("billing_cycles")
            .insert({
                "tenant_id":   tenant_id,
                "plan_id":     plan_id,
                "cycle_start": cycle_start.isoformat(),
                "cycle_end":   cycle_end.isoformat(),
                "status":      "active",
                "max_credits": max_credits,
            })
            .execute()
        )
        rows = result.data or []
        if rows:
            logger.info(
                f"[CycleManager] Created billing cycle for {tenant_id} "
                f"({cycle_start.date()} â†’ {cycle_end.date()}) "
                f"max={max_credits} credits"
            )
            return rows[0]
        return None
    except Exception as exc:
        # Likely a conflict from the UNIQUE index (concurrent request created it first).
        # Fetch the newly created cycle instead.
        logger.warning(f"[CycleManager] create_billing_cycle conflict for {tenant_id}: {exc}")
        return get_active_cycle(tenant_id)


def find_or_create_active_cycle(tenant_id: str) -> Optional[Dict[str, Any]]:
    """
    The primary entry point for cycle management.

    Steps:
      1. Look for an existing active cycle that covers today.
      2. If found â†’ return it.
      3. If not found â†’ look up the tenant's plan, then create a new cycle
         aligned to the current calendar month.
      4. If the tenant has no plan â†’ create a cycle using the 'starter' plan
         as a safe default (prevents credit engine from crashing on unregistered tenants).

    Returns the active billing_cycle row dict, or None only on DB errors.
    """
    # â”€â”€ 1: Existing active cycle? â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    cycle = get_active_cycle(tenant_id)
    if cycle:
        return cycle

    # â”€â”€ 2: No cycle â€” look up tenant's plan â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    tenant_plan = get_tenant_plan(tenant_id)

    if tenant_plan and tenant_plan.get("plans"):
        plan        = tenant_plan["plans"]
        plan_id     = plan["id"]
        max_credits = plan["max_credits_per_cycle"]
    else:
        # Check tenant_config for subscription_status
        config_result = supabase.table("tenant_config").select(
            "subscription_status, trial_credit_limit"
        ).eq("tenant_id", tenant_id).limit(1).execute()

        if config_result.data:
            config = config_result.data[0]
            status = config.get("subscription_status")
            trial_limit = int(config.get("trial_credit_limit") or 90)

            if status == "active":
                plan_id = "grace_active"
                max_credits = 1000
            elif status == "trial":
                plan_id = "trial"
                max_credits = trial_limit
            else:
                return None
        else:
            status = "unknown"
            plan_id = "trial"
            max_credits = 90

        logger.warning(
            f"[CycleManager] No plan found for {tenant_id}, "
            f"using status-based fallback: status={status} max_credits={max_credits}"
        )

    # â”€â”€ 3: Create cycle for current calendar month â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    now                  = datetime.now(timezone.utc)
    cycle_start, cycle_end = _month_boundaries(now)

    return create_billing_cycle(
        tenant_id   = tenant_id,
        plan_id     = plan_id,
        max_credits = max_credits,
        cycle_start = cycle_start,
        cycle_end   = cycle_end,
    )


def close_cycle(cycle_id: str) -> bool:
    """
    Mark a billing cycle as 'closed'. Called at end of billing period.
    (Currently manual / cron-triggered â€” future automation possible.)
    """
    try:
        supabase.table("billing_cycles").update({"status": "closed"}).eq("id", cycle_id).execute()
        logger.info(f"[CycleManager] Closed cycle {cycle_id}")
        return True
    except Exception as exc:
        logger.error(f"[CycleManager] close_cycle failed for {cycle_id}: {exc}")
        return False

