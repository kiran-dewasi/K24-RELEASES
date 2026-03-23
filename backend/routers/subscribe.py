"""
Public Subscription Router — K24
================================
Handles the full UPI subscription intent lifecycle:
  POST   /public/subscribe/intent          → create intent (no auth)
  PATCH  /public/subscribe/intent/{id}/payment  → submit UPI ref (no auth)

Admin endpoints (API-key protected) are in admin.py.

Design principles:
  - Fully public endpoints (no API key or auth token required)
  - All writes go via Supabase service-role key
  - No sensitive data returned to client
  - Idempotent where possible
"""

import os
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator
import re
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public/subscribe", tags=["Subscribe (Public)"])

# ── Supabase helpers ────────────────────────────────────────────────────────

SUPABASE_URL       = os.getenv("SUPABASE_URL", "")
SERVICE_KEY        = (
    os.getenv("SUPABASE_SERVICE_KEY") or
    os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
    os.getenv("SUPABASE_ANON_KEY") or ""
)

VALID_PLAN_IDS = {"starter", "pro", "enterprise"}

# ──# Annual plan prices in paise (all ex-GST)
# Starter : ₹12,627/year (₹1,052/mo equiv, 19% off monthly rate)
# Pro     : ₹38,870/year (₹3,239/mo equiv, 19% off monthly rate)
# Enterprise: custom — handled via sales contact
PLAN_PRICES = {
    "starter":    1262700,   # ₹12,627/year in paise
    "pro":        3887000,   # ₹38,870/year in paise
    "enterprise": 0,         # custom
}


def _sb_headers() -> dict:
    return {
        "apikey":        SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }


def _sb_post(table: str, data: dict) -> Optional[dict]:
    try:
        r = httpx.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=_sb_headers(),
            json=data,
            timeout=10,
        )
        if r.status_code in (200, 201):
            rows = r.json()
            return rows[0] if rows else {}
        logger.error(f"[Subscribe] INSERT {table} failed {r.status_code}: {r.text[:300]}")
        return None
    except Exception as e:
        logger.error(f"[Subscribe] INSERT {table} exception: {e}")
        return None


def _sb_patch(table: str, filters: str, data: dict) -> bool:
    try:
        r = httpx.patch(
            f"{SUPABASE_URL}/rest/v1/{table}?{filters}",
            headers=_sb_headers(),
            json=data,
            timeout=10,
        )
        return r.status_code in (200, 204)
    except Exception as e:
        logger.error(f"[Subscribe] PATCH {table} exception: {e}")
        return False


def _sb_get(table: str, filters: str) -> Optional[dict]:
    try:
        r = httpx.get(
            f"{SUPABASE_URL}/rest/v1/{table}?{filters}&limit=1",
            headers=_sb_headers(),
            timeout=10,
        )
        if r.status_code == 200 and r.json():
            return r.json()[0]
        return None
    except Exception as e:
        logger.error(f"[Subscribe] GET {table} exception: {e}")
        return None


# ── Request / Response models ────────────────────────────────────────────────

class CreateIntentRequest(BaseModel):
    plan_id:      str
    name:         str
    company_name: str
    email:        str
    phone:        str
    gst_number:   Optional[str] = None
    existing_tenant_id: Optional[str] = None

    @field_validator("plan_id")
    @classmethod
    def valid_plan(cls, v):
        if v not in VALID_PLAN_IDS:
            raise ValueError(f"Invalid plan_id. Must be one of: {VALID_PLAN_IDS}")
        return v

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v):
        digits = re.sub(r"\D", "", v)
        if len(digits) < 10:
            raise ValueError("Phone number must have at least 10 digits")
        return digits

    @field_validator("email")
    @classmethod
    def valid_email(cls, v):
        # Basic email validation
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email address")
        return v.lower().strip()

    @field_validator("name", "company_name")
    @classmethod
    def not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("This field cannot be empty")
        return v


class SubmitPaymentRequest(BaseModel):
    upi_ref:        str
    screenshot_url: Optional[str] = None

    @field_validator("upi_ref")
    @classmethod
    def valid_ref(cls, v):
        v = v.strip()
        if len(v) < 6:
            raise ValueError("UPI reference must be at least 6 characters")
        return v


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/intent", summary="Create subscription intent (public)")
async def create_intent(req: CreateIntentRequest):
    """
    Called when user fills the subscription form and clicks "Pay via UPI".
    Creates a subscription_intent record with status=pending_payment.
    Returns the intent ID for the payment step.
    """
    if not SUPABASE_URL:
        raise HTTPException(503, detail="Service temporarily unavailable")

    amount_paise = PLAN_PRICES.get(req.plan_id, 0)

    # Enterprise is contact-us only — should not come through this flow
    if req.plan_id == "enterprise":
        raise HTTPException(400, detail="Enterprise plan requires direct contact. Please email us.")

    data = {
        "plan_id":      req.plan_id,
        "amount_paise": amount_paise,
        "name":         req.name,
        "company_name": req.company_name,
        "email":        req.email,
        "phone":        req.phone,
        "gst_number":   req.gst_number,
        "existing_tenant_id": req.existing_tenant_id,
        "status":       "pending_payment",
    }

    result = _sb_post("subscription_intents", data)
    if not result:
        logger.error(f"[Subscribe] Failed to create intent for {req.email}")
        raise HTTPException(500, detail="Failed to record your subscription. Please try again.")

    logger.info(f"[Subscribe] Intent created: {result.get('id')} plan={req.plan_id} email={req.email}")

    return {
        "intent_id":    result["id"],
        "plan_id":      req.plan_id,
        "amount_paise": amount_paise,
        "amount_inr":   amount_paise / 100,
        "status":       "pending_payment",
        "message":      "Intent created. Proceed to UPI payment.",
    }


@router.patch("/intent/{intent_id}/payment", summary="Submit UPI payment reference (public)")
async def submit_payment(intent_id: str, req: SubmitPaymentRequest):
    """
    Called after user completes UPI payment.
    Updates the intent with UPI ref and moves status to awaiting_verification.
    """
    if not SUPABASE_URL:
        raise HTTPException(503, detail="Service temporarily unavailable")

    # Validate intent exists and is in correct state
    intent = _sb_get(
        "subscription_intents",
        f"id=eq.{intent_id}&status=eq.pending_payment&select=id,plan_id,email,status"
    )
    if not intent:
        raise HTTPException(404, detail="Intent not found or already processed.")

    success = _sb_patch(
        "subscription_intents",
        f"id=eq.{intent_id}",
        {
            "upi_ref":        req.upi_ref,
            "screenshot_url": req.screenshot_url,
            "status":         "awaiting_verification",
            "updated_at":     datetime.now(timezone.utc).isoformat(),
        }
    )

    if not success:
        raise HTTPException(500, detail="Failed to record payment. Please try again.")

    logger.info(f"[Subscribe] Payment submitted: intent={intent_id} ref={req.upi_ref}")

    return {
        "intent_id": intent_id,
        "status":    "awaiting_verification",
        "message":   "Payment recorded. We'll verify within 4 business hours and send confirmation to your email/WhatsApp.",
    }
