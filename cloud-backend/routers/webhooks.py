"""
Webhooks Router

Handles incoming webhooks from external services including:
- Supabase Database Webhooks for tenant sync
"""
from fastapi import APIRouter, HTTPException, Header, Request, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal
import logging
from datetime import datetime, timezone, timedelta
import os

from database import get_supabase_client

router = APIRouter(tags=["webhooks"])
logger = logging.getLogger(__name__)


# Security: Validate incoming webhook requests
def verify_webhook_secret(x_webhook_secret: str = Header(None)):
    """Verify that the webhook request has the correct secret"""
    expected_secret = os.getenv("TENANT_SYNC_WEBHOOK_SECRET")
    if not expected_secret:
        logger.error("TENANT_SYNC_WEBHOOK_SECRET not configured in environment")
        raise HTTPException(status_code=500, detail="Server configuration error")
    if not x_webhook_secret or x_webhook_secret != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid or missing webhook secret")
    return True


# Webhook Models (matching Supabase Database Webhook format)
class SupabaseWebhookPayload(BaseModel):
    """Supabase Database Webhook payload structure"""
    type: Literal["INSERT", "UPDATE", "DELETE"]
    table: str
    schema: str
    record: Optional[Dict[str, Any]] = None
    old_record: Optional[Dict[str, Any]] = None


@router.post("/tenant-sync", status_code=200)
async def sync_tenant_from_prelaunch(
    payload: SupabaseWebhookPayload,
    request: Request,
    authenticated: bool = Depends(verify_webhook_secret)
):
    """
    Tenant Sync Webhook (Step 2)
    
    Receives webhooks from k24-prelaunch Supabase Database Webhooks
    and upserts tenant configuration into k24-main.
    
    **Security**: Requires X-Webhook-Secret header matching TENANT_SYNC_WEBHOOK_SECRET env var.
    
    Flow:
    1. k24-prelaunch triggers webhook on presale_orders INSERT/UPDATE
    2. This endpoint receives the webhook payload
    3. Extracts tenant_id (from record.id) and whatsapp_number
    4. Upserts into k24-main tenant_config table
    5. Preserves existing subscription_status/trial_ends_at for paid users
    
    Source table: public.presale_orders
    - id -> tenant_id
    - whatsapp_number -> whatsapp_number
    - email -> user_email
    
    Destination table: tenant_config
    - tenant_id (PK)
    - whatsapp_number
    - user_email
    - subscription_status (default: 'trial', preserve if exists)
    - trial_ends_at (default: now + 3 days, preserve if exists)
    """
    try:
        logger.info(f"📥 Tenant sync webhook: type={payload.type}, table={payload.table}")
        
        # Only handle INSERT and UPDATE events
        if payload.type not in ["INSERT", "UPDATE"]:
            logger.info(f"✅ Ignoring {payload.type} event")
            return {
                "status": "ignored",
                "reason": "event_type_not_handled",
                "type": payload.type
            }
        
        # Validate we're processing the expected table
        if payload.table != "presale_orders":
            logger.warning(f"⚠️  Unexpected table: {payload.table}")
            return {
                "status": "ignored",
                "reason": "unexpected_table",
                "table": payload.table
            }
        
        # Extract record data
        if not payload.record:
            logger.error("❌ Missing record in payload")
            raise HTTPException(status_code=400, detail="Missing record in payload")
        
        record = payload.record
        
        # Extract tenant_id and normalize to string (may be int from Supabase bigint)
        raw_tenant_id = record.get("id")
        if not raw_tenant_id:
            logger.error("❌ Missing id (tenant_id) in record")
            raise HTTPException(status_code=400, detail="Missing tenant_id in record")
        tenant_id = str(raw_tenant_id)
        
        # Extract whatsapp_number
        whatsapp_number = record.get("whatsapp_number")
        if not whatsapp_number or whatsapp_number.strip() == "":
            # Log with masked tenant_id for privacy
            logger.info(
                "✅ Ignoring record with missing whatsapp_number: tenant_id=%s...",
                tenant_id[:8]
            )
            return {
                "status": "ignored",
                "reason": "missing_whatsapp_number",
                "tenant_id": tenant_id
            }
        
        # Extract user_email
        user_email = record.get("email")
        
        # Mask WhatsApp number for logging (show only last 4 digits)
        masked_whatsapp = f"****{whatsapp_number[-4:]}" if len(whatsapp_number) >= 4 else "****"
        logger.info(
            "📝 Processing tenant sync: tenant_id=%s..., whatsapp=%s",
            tenant_id[:8],
            masked_whatsapp
        )
        
        # Connect to k24-main Supabase
        k24_main_url = os.getenv("K24_MAIN_SUPABASE_URL")
        k24_main_key = os.getenv("K24_MAIN_SUPABASE_SERVICE_ROLE_KEY")
        
        if not k24_main_url or not k24_main_key:
            logger.error("❌ K24_MAIN_SUPABASE_URL or K24_MAIN_SUPABASE_SERVICE_ROLE_KEY not configured")
            raise HTTPException(
                status_code=500,
                detail="K24 main database configuration missing"
            )
        
        # Create separate Supabase client for k24-main
        from supabase import create_client
        k24_main_supabase = create_client(k24_main_url, k24_main_key)
        
        # Step 1: Check if tenant_config row exists
        existing_result = k24_main_supabase.table("tenant_config").select(
            "tenant_id, subscription_status, trial_ends_at"
        ).eq(
            "tenant_id", tenant_id
        ).execute()
        
        # Prepare upsert data
        now = datetime.now(timezone.utc)
        trial_expires = now + timedelta(days=3)
        
        upsert_data = {
            "tenant_id": tenant_id,
            "whatsapp_number": whatsapp_number,
            "user_email": user_email,
        }
        
        # Step 2: Only set defaults if creating new row OR existing fields are null
        if not existing_result.data or len(existing_result.data) == 0:
            # New row - set defaults
            upsert_data["subscription_status"] = "trial"
            upsert_data["trial_ends_at"] = trial_expires.isoformat()
            logger.info(f"✅ Creating new tenant_config with trial defaults")
        else:
            # Existing row - preserve non-null values
            existing = existing_result.data[0]
            if not existing.get("subscription_status"):
                upsert_data["subscription_status"] = "trial"
            if not existing.get("trial_ends_at"):
                upsert_data["trial_ends_at"] = trial_expires.isoformat()
            logger.info(f"✅ Updating existing tenant_config (preserving subscription data)")
        
        # Step 3: Upsert into tenant_config
        upsert_result = k24_main_supabase.table("tenant_config").upsert(
            upsert_data,
            on_conflict="tenant_id"
        ).execute()
        
        if not upsert_result.data:
            logger.error("❌ Failed to upsert tenant_config")
            raise HTTPException(status_code=500, detail="Failed to sync tenant")
        
        logger.info(
            "✅ Tenant synced successfully: tenant_id=%s..., whatsapp=%s",
            tenant_id[:8],
            masked_whatsapp
        )
        
        return {
            "status": "synced",
            "tenant_id": tenant_id,
            "whatsapp_number": masked_whatsapp,  # Return masked number
            "timestamp": now.isoformat()
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ Error processing tenant sync webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "WEBHOOK_PROCESSING_ERROR",
                "detail": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


@router.get("/status")
async def webhooks_status():
    """Health check for webhooks service"""
    return {
        "status": "operational",
        "service": "webhooks",
        "timestamp": datetime.now().isoformat()
    }
