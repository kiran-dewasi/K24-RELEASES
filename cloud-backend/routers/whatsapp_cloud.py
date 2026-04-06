from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Literal
import logging
from datetime import datetime, timezone
import os
import uuid
import re
import secrets
import httpx

from database import get_supabase_client
from services.tenant_onboarding_service import TenantOnboardingPayload, get_or_create_tenant


router = APIRouter(tags=["whatsapp-cloud"])
logger = logging.getLogger(__name__)

SenderType = Literal["known_user", "known_customer", "unknown_lead", "unresolvable"]

@dataclass
class SenderIdentity:
    raw_jid:         str
    resolved_phone:  Optional[str]   # E164 with country code e.g. 917339906200
    tenant_id:       Optional[str]
    user_id:         Optional[str]
    sender_type:     SenderType
    resolution_path: str  # "db_lid" | "direct_phone" | "env_fallback" | "none"

def normalize_phone(raw: str) -> str:
    """
    Strip all non-digits. 
    If 10 digits → prepend 91 (Indian number).
    If already has 91 prefix (12 digits starting with 91) → keep as is.
    If 12 digits but not 91 → keep as is.
    Returns digits-only string.
    """
    digits = ''.join(filter(str.isdigit, raw))
    if len(digits) == 10:
        return '91' + digits
    return digits

def parse_env_lid_map() -> dict:
    """Parse LID_PHONE_MAP env var. Format: 'lid1:phone1,lid2:phone2'"""
    raw = os.getenv("LID_PHONE_MAP", "")
    result = {}
    if not raw:
        return result
    for pair in raw.split(","):
        parts = pair.strip().split(":")
        if len(parts) == 2:
            result[parts[0].strip()] = parts[1].strip()
    return result

async def resolve_sender_identity(raw_jid: str) -> SenderIdentity:
    """
    Single entry point for all inbound sender resolution.
    Takes raw WhatsApp JID (e.g. "185628738236618@lid" or "917339906200@s.whatsapp.net")
    Returns complete SenderIdentity with type classification.
    """
    supabase = get_supabase_client()
    
    is_lid = raw_jid.endswith("@lid")
    bare = raw_jid.split("@")[0]
    
    # --- Step 1: Resolve LID → phone ---
    phone = None
    path = "none"
    
    if is_lid:
        # Level 1: DB lookup
        try:
            row = supabase.table("lid_phone_map") \
                .select("phone") \
                .eq("lid", bare) \
                .limit(1) \
                .execute()
            if row.data:
                phone = row.data[0]["phone"]
                path = "db_lid"
        except Exception as e:
            print(f"[RESOLVE] lid_phone_map lookup failed: {e}")
        
        # Level 2: env fallback (temporary)
        if not phone:
            env_map = parse_env_lid_map()
            if bare in env_map:
                phone = env_map[bare]
                path = "env_fallback"
        
        if not phone:
            print(f"[RESOLVE] Unresolvable LID: {bare}")
            return SenderIdentity(raw_jid, None, None, None, "unresolvable", "none")
    else:
        phone = normalize_phone(bare)
        path = "direct_phone"
    
    # --- Step 2: Phone → tenant via tenant_config ---
    # tenant_config stores phone WITHOUT country code (10 digits)
    # so try both normalized (12 digit) and stripped (10 digit)
    phone_10 = phone[-10:] if len(phone) >= 10 else phone
    
    try:
        result = supabase.table("tenant_config") \
            .select("tenant_id, subscription_status") \
            .in_("whatsapp_number", [phone, phone_10]) \
            .limit(1) \
            .execute()
        
        if result.data:
            row = result.data[0]
            if row["subscription_status"] in ("active", "trial"):
                return SenderIdentity(raw_jid, phone, row["tenant_id"], None, "known_user", path)
    except Exception as e:
        print(f"[RESOLVE] tenant_config lookup failed: {e}")
    
    # --- Step 3: Unknown lead ---
    print(f"[RESOLVE] Unknown lead: phone={phone}, path={path}")
    return SenderIdentity(raw_jid, phone, None, None, "unknown_lead", path)

# Security: Validate incoming requests from Baileys service
def get_baileys_secret() -> str:
    """Get Baileys secret from environment or fallback"""
    return os.getenv("BAILEYS_SECRET", "k24_baileys_secret")

def verify_baileys_secret(x_baileys_secret: str = Header(None)):
    """Verify that the request comes from authenticated Baileys service"""
    expected_secret = get_baileys_secret()
    if x_baileys_secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid Baileys secret")
    return True

# Helper Functions
def normalize_whatsapp_number(phone: str) -> str:
    """
    Normalize WhatsApp phone number for consistent lookups.
    
    Removes all non-digit characters and ensures consistent format.
    Example: "+1 (555) 123-4567" -> "15551234567"
    """
    # Remove all non-digit characters
    normalized = re.sub(r'\D', '', phone)
    return normalized

def resolve_tenant_from_business_number(business_number: str, supabase) -> Dict[str, Any]:
    """
    Resolve tenant_id and subscription details from business WhatsApp number.
    
    Args:
        business_number: The business WhatsApp number (to_number from message)
        supabase: Supabase client instance
    
    Returns:
        Dict containing tenant_id, subscription_status, and trial_ends_at
        
    Raises:
        HTTPException: If tenant not found or subscription is not valid
    """
    # Normalize the business number for lookup
    normalized_business_number = normalize_whatsapp_number(business_number)
    
    # Query tenant_config by whatsapp_number
    tenant_result = supabase.table("tenant_config").select(
        "tenant_id, subscription_status, trial_ends_at, whatsapp_number"
    ).eq(
        "whatsapp_number", normalized_business_number
    ).execute()
    
    # If not found with normalized number, try with original
    if not tenant_result.data or len(tenant_result.data) == 0:
        tenant_result = supabase.table("tenant_config").select(
            "tenant_id, subscription_status, trial_ends_at, whatsapp_number"
        ).eq(
            "whatsapp_number", business_number
        ).execute()
    
    if not tenant_result.data or len(tenant_result.data) == 0:
        masked_number = f"****{business_number[-4:]}" if len(business_number) >= 4 else "****"
        logger.error(f"❌ No tenant found for business WhatsApp: {masked_number}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": "TENANT_NOT_FOUND",
                "detail": f"No tenant configured for business WhatsApp number",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    tenant_config = tenant_result.data[0]
    tenant_id = tenant_config["tenant_id"]
    subscription_status = tenant_config.get("subscription_status")
    trial_ends_at = tenant_config.get("trial_ends_at")
    
    # Enforce subscription rules
    now = datetime.now(timezone.utc)
    
    # Block if subscription is explicitly expired or cancelled
    if subscription_status in ["expired", "cancelled"]:
        logger.warning(
            f"🚫 Blocked incoming message: tenant_id={tenant_id[:8] if tenant_id else 'N/A'}..., "
            f"subscription_status={subscription_status}"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "TENANT_SUBSCRIPTION_EXPIRED",
                "detail": f"Tenant subscription is {subscription_status}. Please renew to continue receiving messages.",
                "timestamp": now.isoformat()
            }
        )
    
    # Block if trial and trial_ends_at is in the past
    if subscription_status == "trial" and trial_ends_at:
        try:
            trial_end_dt = datetime.fromisoformat(trial_ends_at.replace('Z', '+00:00'))
            if trial_end_dt < now:
                logger.warning(
                    f"🚫 Blocked incoming message: tenant_id={tenant_id[:8] if tenant_id else 'N/A'}..., "
                    f"trial expired on {trial_ends_at}"
                )
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "TENANT_SUBSCRIPTION_EXPIRED",
                        "detail": "Trial period has expired. Please upgrade to continue receiving messages.",
                        "timestamp": now.isoformat()
                    }
                )
        except (ValueError, AttributeError) as e:
            logger.warning(f"⚠️  Could not parse trial_ends_at: {trial_ends_at}, error: {e}")
            # If we can't parse the date, allow the message through to prevent false negatives
    
    # Allow for 'active' or 'trial' (with future/null trial_ends_at)
    if subscription_status not in ["active", "trial"]:
        # If status is something unexpected, log and block for safety
        logger.warning(
            f"🚫 Blocked incoming message: tenant_id={tenant_id[:8] if tenant_id else 'N/A'}..., "
            f"unexpected subscription_status={subscription_status}"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "TENANT_SUBSCRIPTION_EXPIRED",
                "detail": f"Tenant subscription status is not valid: {subscription_status}",
                "timestamp": now.isoformat()
            }
        )
    
    logger.info(
        f"✅ Tenant access granted: tenant_id={tenant_id[:8] if tenant_id else 'N/A'}..., "
        f"subscription_status={subscription_status}"
    )
    
    return {
        "tenant_id": tenant_id,
        "subscription_status": subscription_status,
        "trial_ends_at": trial_ends_at
    }

class LidSyncEntry(BaseModel):
    lid:    str
    phone:  str
    source: Optional[str] = "contacts_event"

@router.post("/sync-lid")
async def sync_lid_mappings(entries: List[LidSyncEntry]):
    """
    Called by Baileys listener whenever contacts events reveal LID→phone pairs.
    Upserts into lid_phone_map. Safe to call repeatedly with same data.
    """
    if not entries:
        return {"synced": 0}
    
    rows = [
        {
            "lid":        e.lid,
            "phone":      e.phone,
            "source":     e.source,
            "updated_at": datetime.utcnow().isoformat()
        }
        for e in entries
    ]
    
    supabase = get_supabase_client()
    supabase.table("lid_phone_map").upsert(rows, on_conflict="lid").execute()
    
    print(f"[LID-SYNC] Upserted {len(rows)} mappings from source={entries[0].source}")
    return {"synced": len(rows)}

BAILEYS_SERVICE_URL = os.getenv("BAILEYS_SERVICE_URL", "http://localhost:3000")

async def handle_onboarding_step(phone: str, message_text: str, state: Dict[str, Any], supabase) -> str:
    """
    State machine for K24 onboarding flow driven by onboarding_states table.
    Returns the reply text to send back to the user.
    """
    text = (message_text or "").strip()
    step = state.get("current_step", "awaiting_business_name")

    # RESTART keyword resets from any step
    if text.upper() == "RESTART":
        supabase.table("onboarding_states").update({
            "current_step": "awaiting_business_name",
            "temp_data": {},
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("phone", phone).execute()
        return (
            "Let's start over! 👋\n"
            "Welcome to K24. What is your *business name*?"
        )

    data: Dict[str, Any] = state.get("temp_data") or {}

    if step == "awaiting_business_name":
        data["business_name"] = text
        supabase.table("onboarding_states").update({
            "current_step": "awaiting_tally_name",
            "temp_data": data,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("phone", phone).execute()
        return (
            f"Great, *{text}*! 🎉\n"
            "Now, what is your *Tally company name*?\n"
            "(This must match exactly as it appears in Tally Prime.)"
        )

    elif step == "awaiting_tally_name":
        if text.upper() in ("YES", "SAME"):
            tally_name = data.get("business_name", text)
        else:
            tally_name = text
        data["tally_name"] = tally_name
        otp = str(secrets.randbelow(900000) + 100000)  # 6-digit OTP
        data["otp"] = otp
        supabase.table("onboarding_states").update({
            "current_step": "awaiting_otp",
            "temp_data": data,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("phone", phone).execute()
        return (
            f"Got it — Tally company: *{tally_name}*\n\n"
            f"Your verification OTP is: *{otp}*\n"
            "Please reply with this OTP to complete setup."
        )

    elif step == "awaiting_otp":
        stored_otp = data.get("otp", "")
        if text == stored_otp:
            tenant_id = f"TENANT-{secrets.token_hex(4).upper()}"
            onboarding_res = await get_or_create_tenant(
                TenantOnboardingPayload(
                    onboarding_source="whatsapp",
                    tenant_id=tenant_id,
                    whatsapp_number=phone,
                    company_name=data.get("business_name"),
                    tally_company_name=data.get("tally_name"),
                    trial_days=9
                ),
                supabase
            )
            tenant_id = onboarding_res.tenant_id

            supabase.table("onboarding_states").update({
                "current_step": "complete",
                "temp_data": {**data, "tenant_id": tenant_id},
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("phone", phone).execute()
            return (
                f"✅ *Welcome to K24!*\n\n"
                f"Your account is live on a *free trial*.\n"
                f"Business: {data.get('business_name')}\n"
                f"Tally company: {data.get('tally_name')}\n\n"
                "Install the K24 desktop app and enter your tenant ID:\n"
                f"`{tenant_id}`"
            )
        else:
            return (
                "❌ Incorrect OTP. Please try again, or type *RESTART* to begin over."
            )

    elif step == "complete":
        return "Your K24 account is already active. Type *RESTART* if you need to re-register."

    # Fallback — unknown step
    return "Something went wrong. Type *RESTART* to begin fresh."


# Request Models
class IncomingWhatsAppMessage(BaseModel):
    """Incoming WhatsApp message from Baileys service"""
    from_number: str  # Sender phone (customer)
    to_number: Optional[str] = None  # Business WhatsApp number
    message_type: str  # text, image, document
    text: Optional[str] = None
    media_url: Optional[str] = None  # Media URL or path
    raw_payload: Optional[Dict[str, Any]] = None

@router.post("/incoming", status_code=202)
async def receive_whatsapp_message(
    message: IncomingWhatsAppMessage,
    authenticated: bool = Depends(verify_baileys_secret)
):
    """
    Cloud webhook for incoming WhatsApp messages from Baileys service.

    Architecture: ONE shared bot number (+917851074499) for ALL tenants.
    Tenant is resolved by looking up the SENDER's phone in whatsapp_customer_mappings.
    
    Flow:
    1. Baileys receives WhatsApp message on the shared master number
    2. Calls this endpoint with from_number = customer's phone
    3. Look up from_number in whatsapp_customer_mappings (cross-tenant) to find tenant
    4. Validate that tenant's subscription
    5. Insert message into whatsapp_message_queue for that tenant
    6. Desktop app polls queue, processes via Tally, sends reply
    """
    try:
        logger.info(f"📨 Incoming WhatsApp message from {message.from_number}")

        supabase = get_supabase_client()

        # --- Resolve sender identity ---
        identity = await resolve_sender_identity(message.from_number)
        
        print(f"[INBOUND] jid={message.from_number} type={identity.sender_type} "
              f"phone={identity.resolved_phone} tenant={identity.tenant_id} "
              f"path={identity.resolution_path}")
        
        if identity.sender_type == "unresolvable":
            return {"status": "unresolvable", "reason": "could not resolve JID to phone"}

        # --- Step: Route known customer (not a K24 user, but belongs to a tenant) ---
        if identity.sender_type == "unknown_lead":
            try:
                cm = supabase.table("whatsapp_customer_mappings") \
                    .select("tenant_id, user_id") \
                    .in_("customer_phone", [identity.resolved_phone, identity.resolved_phone[-10:]]) \
                    .eq("is_active", True) \
                    .not_.like("customer_phone", "%@%") \
                    .limit(1) \
                    .execute()

                if cm.data:
                    identity.tenant_id   = cm.data[0]["tenant_id"]
                    identity.user_id     = str(cm.data[0]["user_id"]) if cm.data[0].get("user_id") else None
                    identity.sender_type = "known_customer"
            except Exception as e:
                print(f"[INBOUND] whatsapp_customer_mappings lookup failed: {e}")

        # Now handle each type
        if identity.sender_type == "unresolvable":
            return {"status": "unresolvable"}

        if identity.sender_type == "unknown_lead":
            phone = identity.resolved_phone

            # Fetch or create onboarding state
            ob_row = supabase.table("onboarding_states") \
                .select("*") \
                .eq("phone", phone) \
                .limit(1) \
                .execute()

            if ob_row.data:
                ob_state = ob_row.data[0]
            else:
                supabase.table("onboarding_states").insert({
                    "phone": phone,
                    "current_step": "awaiting_business_name",
                    "temp_data": {},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).execute()
                ob_state = {"phone": phone, "current_step": "awaiting_business_name", "temp_data": {}}

            current_step = ob_state.get("current_step", "awaiting_business_name")
            reply_text = await handle_onboarding_step(phone, message.text or "", ob_state, supabase)

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(
                        f"{BAILEYS_SERVICE_URL}/send-message",
                        json={"phone": phone, "message": reply_text}
                    )
            except Exception as send_err:
                logger.warning(f"[ONBOARDING] Reply send failed: {send_err}")

            return {"status": "onboarding", "step": current_step}

        # known_user OR known_customer → both go into the queue pipeline
        # known_customer messages get routed to their tenant's queue
        # the existing subscription check and queue insert runs for both
        tenant_id = identity.tenant_id
        user_id   = identity.user_id

        # Step 3: Validate the resolved tenant's subscription
        tenant_info = validate_tenant_subscription(str(tenant_id), supabase)
        subscription_status = tenant_info["subscription_status"]

        # Step 4: Insert into whatsapp_message_queue
        message_id = str(uuid.uuid4())

        queue_insert = {
            "id": message_id,
            "tenant_id": str(tenant_id),
            "user_id": str(user_id) if user_id else None,
            "customer_phone": message.from_number,
            "message_type": message.message_type,
            "message_text": message.text,
            "media_url": message.media_url,
            "status": "pending",
            "raw_payload": message.raw_payload or {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        insert_result = supabase.table("whatsapp_message_queue").insert(
            queue_insert
        ).execute()

        if not insert_result.data:
            logger.error(f"❌ Failed to insert message into queue")
            raise HTTPException(status_code=500, detail="Failed to queue message")

        logger.info(
            f"✅ Message queued: message_id={message_id}, "
            f"tenant_id={str(tenant_id)[:8] if tenant_id else 'N/A'}..., "
            f"subscription_status={subscription_status}"
        )

        return {"message_id": message_id, "status": "queued"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing incoming message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "detail": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

def validate_tenant_subscription(tenant_id: str, supabase) -> Dict[str, Any]:
    """
    Validate tenant exists and has an active subscription.
    
    Args:
        tenant_id: The tenant ID to validate
        supabase: Supabase client instance
    
    Returns:
        Dict containing tenant_id and subscription_status
        
    Raises:
        HTTPException: If tenant not found or subscription is not valid
    """
    # Query tenant_config by tenant_id
    tenant_result = supabase.table("tenant_config").select(
        "tenant_id, subscription_status, trial_ends_at, trial_credit_limit"
    ).eq(
        "tenant_id", tenant_id
    ).execute()
    
    if not tenant_result.data or len(tenant_result.data) == 0:
        masked_tenant_id = f"{tenant_id[:8]}..." if len(tenant_id) > 8 else "****"
        logger.error(f"❌ Tenant not found: {masked_tenant_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": "TENANT_NOT_FOUND",
                "detail": "Tenant does not exist",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    tenant_config = tenant_result.data[0]
    subscription_status = tenant_config.get("subscription_status")
    trial_ends_at = tenant_config.get("trial_ends_at")
    
    # Enforce subscription rules (same logic as incoming webhook)
    now = datetime.now(timezone.utc)
    
    # Block if subscription is explicitly expired or cancelled
    if subscription_status in ["expired", "cancelled"]:
        masked_tenant_id = f"{tenant_id[:8]}..." if len(tenant_id) > 8 else "****"
        logger.warning(
            f"🚫 Polling blocked: tenant_id={masked_tenant_id}, "
            f"subscription_status={subscription_status}"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "TENANT_SUBSCRIPTION_EXPIRED",
                "detail": f"Tenant subscription is {subscription_status}. Please renew to continue.",
                "timestamp": now.isoformat()
            }
        )
    
    # Block if trial and trial_ends_at is in the past
    if subscription_status == "trial" and trial_ends_at:
        try:
            trial_end_dt = datetime.fromisoformat(trial_ends_at.replace('Z', '+00:00'))
            if trial_end_dt < now:
                masked_tenant_id = f"{tenant_id[:8]}..." if len(tenant_id) > 8 else "****"
                logger.warning(
                    f"🚫 Polling blocked: tenant_id={masked_tenant_id}, "
                    f"trial expired on {trial_ends_at}"
                )
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "TENANT_SUBSCRIPTION_EXPIRED",
                        "detail": "Trial period has expired. Please upgrade to continue.",
                        "timestamp": now.isoformat()
                    }
                )
        except (ValueError, AttributeError) as e:
            logger.warning(f"⚠️  Could not parse trial_ends_at: {trial_ends_at}, error: {e}")
            # If we can't parse the date, allow to prevent false negatives
    
    # Check trial credit limit
    if subscription_status == "trial":
        try:
            # Get trial_credit_limit from tenant_config
            trial_credit_limit = int(tenant_config.get("trial_credit_limit") or 90)

            # Get current credits used from tenant_usage_summary
            # Find the active billing cycle for this tenant first
            cycle_result = supabase.table("billing_cycles").select(
                "id, credits_used_total"
            ).eq("tenant_id", tenant_id).eq("status", "active").order(
                "created_at", desc=True
            ).limit(1).execute()

            credits_used = 0.0
            if cycle_result.data:
                # Get usage summary for this cycle
                cycle_id = cycle_result.data[0]["id"]
                summary_result = supabase.table("tenant_usage_summary").select(
                    "credits_used_total"
                ).eq("tenant_id", tenant_id).eq(
                    "billing_cycle_id", cycle_id
                ).limit(1).execute()

                if summary_result.data:
                    credits_used = float(
                        summary_result.data[0].get("credits_used_total") or 0
                    )

            if credits_used >= trial_credit_limit:
                masked = f"{tenant_id[:8]}..." if len(tenant_id) > 8 else "****"
                logger.warning(
                    f"🚫 Trial credit limit reached: tenant={masked} "
                    f"used={credits_used}/{trial_credit_limit}"
                )
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "TRIAL_CREDIT_LIMIT_REACHED",
                        "detail": f"Trial credit limit of {trial_credit_limit} reached. "
                                  f"Please upgrade to continue.",
                        "credits_used": credits_used,
                        "credits_limit": trial_credit_limit,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
        except HTTPException:
            raise
        except Exception as _ce:
            logger.warning(f"⚠️ Credit limit check failed (allowing): {_ce}")
    
    # Allow for 'active' or 'trial' (with future/null trial_ends_at)
    if subscription_status not in ["active", "trial"]:
        masked_tenant_id = f"{tenant_id[:8]}..." if len(tenant_id) > 8 else "****"
        logger.warning(
            f"🚫 Polling blocked: tenant_id={masked_tenant_id}, "
            f"unexpected subscription_status={subscription_status}"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "TENANT_SUBSCRIPTION_EXPIRED",
                "detail": f"Tenant subscription status is not valid: {subscription_status}",
                "timestamp": now.isoformat()
            }
        )
    
    masked_tenant_id = f"{tenant_id[:8]}..." if len(tenant_id) > 8 else "****"
    logger.info(
        f"✅ Tenant polling access granted: tenant_id={masked_tenant_id}, "
        f"subscription_status={subscription_status}"
    )
    
    return {
        "tenant_id": tenant_id,
        "subscription_status": subscription_status,
        "trial_ends_at": trial_ends_at
    }


def verify_desktop_api_key(x_api_key: str = Header(None)):
    """Verify that the request comes from authenticated desktop app"""
    expected_key = os.getenv("DESKTOP_API_KEY")
    if not expected_key:
        logger.error("DESKTOP_API_KEY not configured in environment")
        raise HTTPException(status_code=500, detail="Server configuration error")
    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True

@router.get("/jobs/{tenant_id}")
async def poll_whatsapp_jobs(
    tenant_id: str,
    limit: int = 10,
    authenticated: bool = Depends(verify_desktop_api_key)
):
    """
    Poll pending WhatsApp messages for a specific tenant.
    Desktop app uses this to fetch messages from the queue.
    
    **Security**: Requires X-API-Key header matching DESKTOP_API_KEY env var.
    **Tenant Isolation**: Validates tenant exists and has active subscription.
    
    Flow:
    1. Desktop app calls GET /api/whatsapp/cloud/jobs/{tenant_id} with X-API-Key header
    2. Validates tenant exists and subscription is active/trial
    3. Fetches pending messages filtered by tenant_id
    4. Atomically updates status to 'processing'
    5. Returns messages to desktop for processing
    6. Desktop processes and calls completion endpoint
    
    Args:
        tenant_id: Tenant ID (from desktop token storage)
        limit: Max messages to fetch (default: 10)
        authenticated: API key validation (dependency)
    
    Returns:
        List of pending messages with details
        
    Raises:
        404: TENANT_NOT_FOUND - Tenant does not exist
        403: TENANT_SUBSCRIPTION_EXPIRED - Subscription expired or cancelled
        500: POLLING_ERROR - Internal server error
    """
    try:
        masked_tenant_id = f"{tenant_id[:8]}..." if len(tenant_id) > 8 else "****"
        logger.info(f"📥 Polling jobs for tenant: {masked_tenant_id}")
        
        supabase = get_supabase_client()
        
        # Step 1: Validate tenant exists and has active subscription
        tenant_info = validate_tenant_subscription(tenant_id, supabase)
        subscription_status = tenant_info["subscription_status"]
        
        # Step 2: Fetch pending messages for this tenant
        # Note: In production, use a database RPC function with SELECT ... FOR UPDATE SKIP LOCKED
        # For now, we use a simple SELECT + UPDATE pattern
        
        pending_result = supabase.table("whatsapp_message_queue").select(
            "id, tenant_id, user_id, customer_phone, message_type, message_text, media_url, raw_payload, created_at"
        ).eq(
            "tenant_id", tenant_id
        ).eq(
            "status", "pending"
        ).order(
            "created_at", desc=False
        ).limit(
            limit
        ).execute()
        
        if not pending_result.data or len(pending_result.data) == 0:
            logger.info(
                f"✅ No pending jobs for tenant {masked_tenant_id} "
                f"(subscription_status={subscription_status})"
            )
            return {
                "messages": [],
                "count": 0
            }
        
        # Step 3: Atomically update fetched messages to 'processing'
        message_ids = [msg["id"] for msg in pending_result.data]
        
        update_result = supabase.table("whatsapp_message_queue").update({
            "status": "processing",
            "processing_started_at": datetime.now(timezone.utc).isoformat()
        }).in_(
            "id", message_ids
        ).execute()
        
        # Step 4: Format response for desktop app
        messages = []
        for msg in pending_result.data:
            messages.append({
                "id": msg["id"],
                "tenant_id": msg["tenant_id"],
                "customer_phone": msg["customer_phone"],
                "message_type": msg["message_type"],
                "message_text": msg.get("message_text"),
                "media_url": msg.get("media_url"),
                "raw_payload": msg.get("raw_payload", {}),
                "created_at": msg["created_at"]
            })
        
        logger.info(
            f"✅ Returned {len(messages)} messages for tenant {masked_tenant_id} "
            f"(subscription_status={subscription_status})"
        )
        
        return {
            "messages": messages,
            "count": len(messages)
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error polling jobs for tenant {tenant_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "POLLING_ERROR",
                "detail": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


class JobCompletion(BaseModel):
    """Job completion request from desktop app"""
    status: str  # "delivered" or "failed"
    error_message: Optional[str] = None
    result_summary: Optional[str] = None

@router.post("/jobs/{message_id}/complete")
async def complete_whatsapp_job(
    message_id: str,
    completion: JobCompletion,
    authenticated: bool = Depends(verify_desktop_api_key)
):
    """
    Mark a WhatsApp message job as completed (delivered or failed).
    Desktop app calls this after processing a message from the queue.
    
    **Security**: Requires X-API-Key header matching DESKTOP_API_KEY env var.
    
    Flow:
    1. Desktop processes message from queue
    2. Calls this endpoint with message_id and completion status
    3. Updates queue status to 'delivered' or 'failed'
    4. Records error message if failed
    
    Args:
        message_id: Message ID from the queue
        completion: Completion status and optional error/summary
        authenticated: API key validation (dependency)
    
    Returns:
        Success confirmation with message_id
    """
    try:
        # Validate status
        if completion.status not in ["delivered", "failed"]:
            raise HTTPException(
                status_code=400,
                detail="Status must be 'delivered' or 'failed'"
            )
        
        # Validate error_message for failed status
        if completion.status == "failed" and not completion.error_message:
            raise HTTPException(
                status_code=400,
                detail="error_message is required when status is 'failed'"
            )
        
        logger.info(f"📝 Completing job {message_id} with status: {completion.status}")
        
        supabase = get_supabase_client()
        
        # Update message status atomically
        update_data = {
            "status": completion.status,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "error_message": completion.error_message
        }
        
        result = supabase.table("whatsapp_message_queue").update(
            update_data
        ).eq(
            "id", message_id
        ).execute()
        
        # Check if message was found
        if not result.data or len(result.data) == 0:
            logger.warning(f"❌ Message not found: {message_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Message {message_id} not found"
            )
        
        logger.info(f"✅ Job {message_id} marked as {completion.status}")
        
        return {
            "success": True,
            "message_id": message_id,
            "status": completion.status,
            "processed_at": update_data["processed_at"]
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error completing job {message_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "COMPLETION_ERROR",
                "detail": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


@router.get("/status")
async def whatsapp_service_status():
    """Health check for WhatsApp cloud service"""
    return {
        "status": "operational",
        "service": "whatsapp-cloud-webhook",
        "timestamp": datetime.now().isoformat()
    }
