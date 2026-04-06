"""
Tenant Onboarding Service — Phase 1
====================================
Self-contained, zero-side-effect service.
No wiring, no imports in other files.

Usage:
    from cloud-backend.services.tenant_onboarding_service import (
        TenantOnboardingPayload,
        TenantResult,
        get_or_create_tenant,
    )
    result = await get_or_create_tenant(payload, supabase_client)

DB calls use the same httpx pattern as supabase_service.py:
  - GET  : httpx.get(rest_url, headers=service_headers, timeout=10)
  - POST : httpx.post(rest_url, headers=service_headers, json=payload, timeout=10)
  - PATCH: httpx.patch(rest_url?filter, headers=service_headers, json=patch, timeout=10)
"""

import secrets
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Literal, Optional

import httpx
from fastapi import HTTPException
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TenantOnboardingPayload(BaseModel):
    onboarding_source: Literal["web", "whatsapp", "admin", "webhook"]
    tenant_id: Optional[str] = None
    whatsapp_number: Optional[str] = None
    user_email: Optional[str] = None
    company_name: Optional[str] = None
    owner_name: Optional[str] = None
    tally_company_name: Optional[str] = None
    trial_days: int = 9


class TenantResult(BaseModel):
    tenant_id: str
    was_created: bool
    row: Dict[str, Any]


# ---------------------------------------------------------------------------
# Internal helpers — mirror supabase_service.py's HTTP pattern exactly
# ---------------------------------------------------------------------------

def _rest_url(supabase_client: Any, table: str) -> str:
    """Build PostgREST URL from the existing SupabaseHTTPService instance."""
    # supabase_client is a SupabaseHTTPService (or SupabaseService wrapper).
    # Both expose ._http (wrapper) or .url (raw service).
    svc = getattr(supabase_client, "_http", supabase_client)
    base_url = svc.url
    return f"{base_url}/rest/v1/{table}"


def _service_headers(supabase_client: Any) -> Dict[str, str]:
    """Return service-role headers from the existing client instance."""
    svc = getattr(supabase_client, "_http", supabase_client)
    key = svc.service_key or svc.anon_key
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


async def _select_tenant(
    supabase_client: Any,
    tenant_id: str,
) -> Optional[Dict[str, Any]]:
    """SELECT * FROM tenant_config WHERE tenant_id = $1 LIMIT 1."""
    url = f"{_rest_url(supabase_client, 'tenant_config')}?tenant_id=eq.{tenant_id}&limit=1"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_service_headers(supabase_client), timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        return data[0] if data else None
    raise RuntimeError(f"SELECT tenant_config failed: {resp.status_code} {resp.text}")


async def _insert_tenant(
    supabase_client: Any,
    row: Dict[str, Any],
) -> Dict[str, Any]:
    """INSERT INTO tenant_config VALUES (...) RETURNING *."""
    url = _rest_url(supabase_client, "tenant_config")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers=_service_headers(supabase_client),
            json=row,
            timeout=10,
        )
    if resp.status_code in (200, 201):
        data = resp.json()
        return data[0] if isinstance(data, list) and data else row
    raise RuntimeError(f"INSERT tenant_config failed: {resp.status_code} {resp.text}")


async def _patch_tenant(
    supabase_client: Any,
    tenant_id: str,
    patch: Dict[str, Any],
) -> None:
    """PATCH tenant_config SET ... WHERE tenant_id = $1."""
    url = f"{_rest_url(supabase_client, 'tenant_config')}?tenant_id=eq.{tenant_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            url,
            headers=_service_headers(supabase_client),
            json=patch,
            timeout=10,
        )
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"PATCH tenant_config failed: {resp.status_code} {resp.text}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_or_create_tenant(
    payload: TenantOnboardingPayload,
    supabase_client: Any,
) -> TenantResult:
    """
    Idempotent get-or-create for tenant_config.

    Order of operations (strict):
      1. Generate tenant_id if not provided.
      2. SELECT existing row.
      3a. Row exists  → patch only NULL fields (guarded fields never overwritten).
      3b. Row missing → full INSERT with trial window.
      4. Re-SELECT final row and return TenantResult.

    Raises HTTPException(500) on any DB error.
    """

    # ------------------------------------------------------------------
    # 1. Resolve tenant_id
    # ------------------------------------------------------------------
    tenant_id: str = payload.tenant_id or f"TENANT-{secrets.token_hex(4).upper()}"

    # ------------------------------------------------------------------
    # 2. Check for existing row
    # ------------------------------------------------------------------
    try:
        existing = await _select_tenant(supabase_client, tenant_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"tenant_onboarding_failed: {e}")

    was_created: bool

    if existing is not None:
        # ---------------------------------------------------------------
        # 3a. Row exists — patch only NULL fields; honour protected fields
        # ---------------------------------------------------------------
        patch: Dict[str, Any] = {}

        # Patchable optional fields: only overwrite if DB value is None
        patchable_map = {
            "whatsapp_number": payload.whatsapp_number,
            "user_email": payload.user_email,
            "company_name": payload.company_name,
            "owner_name": payload.owner_name,
            "tally_company_name": payload.tally_company_name,
        }
        for col, val in patchable_map.items():
            if val is not None and existing.get(col) is None:
                patch[col] = val

        # Protected fields — never overwrite
        if existing.get("subscription_status") != "active":
            # subscription_status is NOT 'active', so we may set it to trial
            # but only if completely absent — stay conservative: do not patch
            pass  # subscription_status is never patched here

        # trial_ends_at and trial_start_at: never overwrite if already set
        # (already enforced by the NULL check above — they aren't in patchable_map)

        if patch:
            try:
                await _patch_tenant(supabase_client, tenant_id, patch)
                print(f"[TENANT] PATCHED tenant_id={tenant_id} fields_updated={list(patch.keys())}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"tenant_onboarding_failed: {e}")
        else:
            print(f"[TENANT] FOUND EXISTING tenant_id={tenant_id} no changes needed")

        was_created = False

    else:
        # ---------------------------------------------------------------
        # 3b. Row does not exist — full INSERT
        # ---------------------------------------------------------------
        now = datetime.now(timezone.utc)
        trial_ends_at = now + timedelta(days=payload.trial_days)

        row: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "whatsapp_number": payload.whatsapp_number or "",
            "user_email": payload.user_email or "",
            "company_name": payload.company_name,
            "owner_name": payload.owner_name,
            "tally_company_name": payload.tally_company_name,
            "subscription_status": "trial",
            "trial_start_at": now.isoformat(),
            "trial_ends_at": trial_ends_at.isoformat(),
            "trial_credit_limit": 90,
            "trial_credits_used": 0,
            "onboarding_source": payload.onboarding_source,
            # nullable fields not provided default to None (omitted = NULL in Supabase)
            "subscription_ends_at": None,
            "razorpay_customer_id": None,
        }

        try:
            await _insert_tenant(supabase_client, row)
            print(
                f"[TENANT] CREATED tenant_id={tenant_id} "
                f"source={payload.onboarding_source} "
                f"whatsapp={payload.whatsapp_number or ''} "
                f"email={payload.user_email or ''}"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"tenant_onboarding_failed: {e}")

        was_created = True

    # ------------------------------------------------------------------
    # 4. Fetch final row and return
    # ------------------------------------------------------------------
    try:
        final_row = await _select_tenant(supabase_client, tenant_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"tenant_onboarding_failed: {e}")

    if final_row is None:
        raise HTTPException(
            status_code=500,
            detail="tenant_onboarding_failed: row missing after write",
        )

    return TenantResult(tenant_id=tenant_id, was_created=was_created, row=final_row)
