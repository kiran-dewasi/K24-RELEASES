from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timezone
import os
import uuid
import re

from database import get_supabase_client

router = APIRouter(tags=["whatsapp-cloud"])
logger = logging.getLogger(__name__)

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

        # Step 1: Normalize sender phone for consistent lookups
        normalized_from = normalize_whatsapp_number(message.from_number)

        # Step 2: Resolve tenant by looking up the SENDER's phone in customer mappings.
        # This is the correct model: one shared bot number, tenant resolved from sender.
        mapping_result = supabase.table("whatsapp_customer_mappings").select(
            "tenant_id, user_id, customer_name"
        ).eq(
            "customer_phone", normalized_from
        ).eq(
            "is_active", True
        ).execute()

        if not mapping_result.data or len(mapping_result.data) == 0:
            # Retry with original (un-normalized) number
            mapping_result = supabase.table("whatsapp_customer_mappings").select(
                "tenant_id, user_id, customer_name"
            ).eq(
                "customer_phone", message.from_number
            ).eq(
                "is_active", True
            ).execute()

        if not mapping_result.data or len(mapping_result.data) == 0:
            # Unknown sender — not registered with any tenant.
            # This usually means the LID wasn't resolved to a real phone number.
            # Return 202 so the listener doesn't crash — but don't queue.
            logger.warning(
                f"⚠️ Unknown sender {message.from_number} (normalized: {normalized_from}). "
                f"Not in whatsapp_customer_mappings. Skipping queue. "
                f"Check LID resolution in the Baileys listener."
            )
            return {
                "status": "unrouted",
                "detail": "Sender not registered with any tenant. LID may not have resolved."
            }

        # Handle conflict: same phone mapped to multiple tenants
        if len(mapping_result.data) > 1:
            logger.warning(
                f"⚠️ Phone {message.from_number} mapped to {len(mapping_result.data)} tenants. "
                f"Routing to first match."
            )

        mapping = mapping_result.data[0]
        tenant_id = mapping.get("tenant_id")
        user_id = mapping.get("user_id")
        customer_name = mapping.get("customer_name")

        logger.info(
            f"✅ Sender resolved: phone={message.from_number}, "
            f"customer={customer_name}, tenant_id={str(tenant_id)[:8] if tenant_id else 'N/A'}..."
        )

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
        "tenant_id, subscription_status, trial_ends_at"
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
