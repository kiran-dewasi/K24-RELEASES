from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timezone
import os
import uuid

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
    Cloud webhook for incoming WhatsApp messages from Baileys service

    Flow:
    1. Baileys listener receives WhatsApp message
    2. Baileys calls this endpoint with message data
    3. This endpoint identifies tenant from phone number
    4. Inserts message into whatsapp_message_queue
    5. Desktop app polls queue and processes message
    """
    try:
        logger.info(f"📨 Incoming WhatsApp message from {message.from_number}")

        # Step 1: Resolve tenant_id and user_id from customer phone
        supabase = get_supabase_client()

        mapping_result = supabase.table("whatsapp_customer_mappings").select(
            "tenant_id, user_id, customer_name"
        ).eq(
            "customer_phone", message.from_number
        ).eq(
            "is_active", True
        ).execute()

        if not mapping_result.data or len(mapping_result.data) == 0:
            logger.warning(f"❌ Unknown customer phone: {message.from_number}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "UNKNOWN_CUSTOMER",
                    "detail": f"Phone number {message.from_number} is not registered with any tenant",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

        # Handle multiple matches (conflict scenario)
        if len(mapping_result.data) > 1:
            logger.warning(
                f"⚠️  Multiple tenants found for {message.from_number}: "
                f"{[m['tenant_id'] for m in mapping_result.data]}"
            )
            # For now, use the first match; in production, may need disambiguation
            # TODO: Implement disambiguation logic if needed

        mapping = mapping_result.data[0]
        tenant_id = mapping["tenant_id"]
        user_id = mapping.get("user_id")
        customer_name = mapping.get("customer_name")

        logger.info(f"✅ Resolved tenant: {tenant_id} for customer {message.from_number}")

        # Step 2: Insert into whatsapp_message_queue
        message_id = str(uuid.uuid4())

        queue_insert = {
            "id": message_id,
            "tenant_id": tenant_id,
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
            raise HTTPException(
                status_code=500,
                detail="Failed to queue message"
            )

        logger.info(f"✅ Message queued: {message_id} for tenant {tenant_id}")

        # Step 3: Return 202 Accepted with message_id
        return {
            "message_id": message_id
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
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

@router.get("/status")
async def whatsapp_service_status():
    """Health check for WhatsApp cloud service"""
    return {
        "status": "operational",
        "service": "whatsapp-cloud-webhook",
        "timestamp": datetime.now().isoformat()
    }
