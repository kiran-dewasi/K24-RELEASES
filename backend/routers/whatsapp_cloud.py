"""
WhatsApp Cloud Incoming Router
==============================

This is the endpoint that the Baileys listener (artistic-healing on Railway)
calls whenever a customer sends a WhatsApp message to the business bot.

KEY DESIGN DECISION:
  - We do NOT care whether the sender is a LID or a real phone number.
    The message goes into the queue regardless. Baileys knows how to send
    a reply back to whatever ID it received the message from.
  - Tenant is resolved strictly from `to_number` (the bot's WhatsApp number),
    NOT from the sender. One bot number = one tenant. Period.
  - If `to_number` is missing or unregistered, we return 400 so Baileys
    knows the message was not accepted (rather than silently dropping it).

Message Queue Flow:
  Baileys → POST /api/whatsapp/cloud/incoming
          → Resolve tenant_id from to_number (Supabase tenant_config)
          → INSERT into Supabase whatsapp_message_queue
          → Desktop WhatsAppPoller polls & processes
          → Reply sent back via Baileys /send-reply
"""

import os
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel

logger = logging.getLogger("whatsapp_cloud")

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp-cloud"])

# ─────────────────────────────────────────────────────────────
# Production defaults — baked in so zero config needed on Railway
# ─────────────────────────────────────────────────────────────
_PROD_SUPABASE_URL         = "https://gxukvnoiyzizienswgni.supabase.co"
_PROD_SUPABASE_SERVICE_KEY = "sb_secret_qJuJk2q0_hO144oQLmSYxA_6WB_qtkRYunw86tZY1LM9TgYvFoqhda8"
_PROD_BAILEYS_SECRET       = "EDkEu8si6PveFOrgRAt32TZcLa1o0tqr1T2LzU3KILg"

SUPABASE_URL         = os.getenv("SUPABASE_URL")         or _PROD_SUPABASE_URL
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or _PROD_SUPABASE_SERVICE_KEY
BAILEYS_SECRET       = os.getenv("BAILEYS_SECRET")       or _PROD_BAILEYS_SECRET


# ─────────────────────────────────────────────────────────────
# Request Model
# ─────────────────────────────────────────────────────────────

class IncomingMessagePayload(BaseModel):
    from_number: str          # Sender — can be LID (185628738236618) or phone (+917XXXXXXXXX)
    to_number:   str          # Bot number — e.g. +919876543210 — used to resolve tenant
    message_text: Optional[str] = ""
    message_type: Optional[str] = "text"   # text | image | audio | document
    media: Optional[dict]    = None        # { type, buffer (base64), mimetype }
    timestamp: Optional[str] = None        # ISO string from Baileys


# ─────────────────────────────────────────────────────────────
# Supabase helpers (sync httpx — fast enough for this hot path)
# ─────────────────────────────────────────────────────────────

def _supa_headers() -> dict:
    return {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }


def _resolve_tenant_from_bot_number(bot_number: str) -> Optional[str]:
    """
    Look up tenant_config table in Supabase:
      SELECT tenant_id FROM tenant_config WHERE whatsapp_number = bot_number LIMIT 1

    This is the SINGLE source of truth for routing — one bot number = one tenant.
    Returns tenant_id string, or None if not registered.
    """
    try:
        # Normalize: strip spaces/dashes, ensure + prefix
        number = bot_number.strip().replace(" ", "").replace("-", "")
        if not number.startswith("+"):
            number = f"+{number}"

        resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/tenant_config",
            headers=_supa_headers(),
            params={
                "whatsapp_number": f"eq.{number}",
                "select": "tenant_id",
                "limit": "1",
            },
            timeout=8,
        )

        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                tid = data[0].get("tenant_id")
                logger.info(f"✅ Tenant resolved: {number} → {tid}")
                return tid

        logger.warning(
            f"⚠️  No tenant found for bot number {number} "
            f"(status={resp.status_code}, body={resp.text[:120]})"
        )
        return None

    except Exception as e:
        logger.error(f"_resolve_tenant_from_bot_number error: {e}")
        return None


def _enqueue_message(
    tenant_id:    str,
    customer_id:  str,   # whatever from_number is — LID or real phone
    message_text: str,
    message_type: str,
    raw_payload:  dict,
) -> str:
    """
    INSERT a new row into Supabase whatsapp_message_queue.
    Returns the generated job_id (UUID).
    """
    job_id = str(uuid.uuid4())
    body = {
        "id":             job_id,
        "tenant_id":      tenant_id,
        "customer_phone": customer_id,    # stored as-is — LID or phone; Baileys handles routing
        "message_text":   message_text or "",
        "message_type":   message_type or "text",
        "status":         "pending",
        "raw_payload":    raw_payload,
        "created_at":     datetime.now(timezone.utc).isoformat(),
    }

    resp = httpx.post(
        f"{SUPABASE_URL}/rest/v1/whatsapp_message_queue",
        headers={**_supa_headers(), "Prefer": "return=minimal"},
        json=body,
        timeout=8,
    )

    if resp.status_code not in (200, 201, 202, 204):
        raise RuntimeError(
            f"Supabase enqueue failed: {resp.status_code} — {resp.text[:200]}"
        )

    logger.info(f"📥 Enqueued job {job_id} for tenant {tenant_id} (from: {customer_id})")
    return job_id


# ─────────────────────────────────────────────────────────────
# THE Main Endpoint
# ─────────────────────────────────────────────────────────────

@router.post("/cloud/incoming")
async def cloud_incoming(
    payload: IncomingMessagePayload,
    x_baileys_secret: Optional[str] = Header(None, alias="X-Baileys-Secret"),
):
    """
    Entry point for all incoming WhatsApp messages from the Baileys listener.

    Works with ANY sender format:
      • Real phone numbers  (+917XXXXXXXXX)
      • WhatsApp LIDs       (185628738236618 or 185628738236618@lid)
      • Short IDs           (anything Baileys gives us)

    Tenant is resolved ONLY from `to_number` (the bot's registered number).
    The sender's exact ID is stored in the queue so Baileys can route the reply.
    """

    # ── 1. Security: validate Baileys secret ─────────────────
    if x_baileys_secret != BAILEYS_SECRET:
        logger.warning(
            f"❌ Invalid Baileys secret received: '{x_baileys_secret}'"
        )
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Baileys secret")

    from_id    = (payload.from_number or "").strip()
    to_number  = (payload.to_number   or "").strip()
    msg_text   = (payload.message_text or "").strip()

    logger.info(f"📨 Incoming | from={from_id} | to={to_number} | text='{msg_text[:60]}'")

    if not from_id:
        raise HTTPException(status_code=400, detail="from_number is required")
    if not to_number:
        raise HTTPException(status_code=400, detail="to_number is required — cannot resolve tenant without it")

    # ── 2. Resolve tenant from bot number (to_number) ─────────
    tenant_id = _resolve_tenant_from_bot_number(to_number)

    if not tenant_id:
        logger.error(
            f"❌ Unregistered bot number: {to_number}. "
            f"Register it in tenant_config via the desktop settings."
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"Bot number {to_number} is not registered to any tenant. "
                "Please configure it in the desktop app → Settings → WhatsApp."
            ),
        )

    # ── IMPORTANT: Normalize to UPPERCASE to match local desktop DB ──
    tenant_id = tenant_id.upper()


    # ── 3. Enqueue message (LID or phone — we don't care) ─────
    raw_payload = {
        "from_number":  from_id,
        "to_number":    to_number,
        "message_text": msg_text,
        "message_type": payload.message_type,
        "media":        payload.media,
        "timestamp":    payload.timestamp or datetime.now(timezone.utc).isoformat(),
    }

    try:
        job_id = _enqueue_message(
            tenant_id    = tenant_id,
            customer_id  = from_id,        # stored as-is — LID or phone
            message_text = msg_text,
            message_type = payload.message_type or "text",
            raw_payload  = raw_payload,
        )
    except Exception as e:
        logger.error(f"Enqueue error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue message: {str(e)}")

    # ── 4. Respond 202 so Baileys knows the message was accepted
    return {
        "status":    "queued",
        "job_id":    job_id,
        "tenant_id": tenant_id,
        "message":   "Message queued. Desktop app will process it.",
    }
