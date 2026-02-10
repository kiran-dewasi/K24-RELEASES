from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from datetime import datetime

router = APIRouter(tags=["whatsapp-cloud"])
logger = logging.getLogger(__name__)

# Security: Validate incoming requests from Baileys service
BAILEYS_SECRET = "k24_baileys_secret"  # TODO: Move to environment variable

def verify_baileys_secret(x_baileys_secret: str = Header(None)):
    """Verify that the request comes from authenticated Baileys service"""
    if x_baileys_secret != BAILEYS_SECRET:
        raise HTTPException(status_code=403, detail="Invalid Baileys secret")
    return True

# Request Models
class IncomingWhatsAppMessage(BaseModel):
    """Incoming WhatsApp message from Baileys service"""
    from_number: str  # Sender phone (customer)
    to_number: Optional[str] = None  # Business WhatsApp number
    message_type: str  # text, image, document
    text: Optional[str] = None
    media: Optional[str] = None  # Base64 or file path
    raw_payload: Optional[Dict[str, Any]] = None

@router.post("/incoming")
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
        
        # TODO Phase 2: Implement tenant routing
        # 1. Call identify_user_by_phone to get tenant_id
        # 2. Insert into whatsapp_message_queue table
        # 3. Return 202 Accepted
        
        # For now, return acknowledgment
        return {
            "status": "received",
            "message_id": f"msg_{datetime.now().timestamp()}",
            "from": message.from_number,
            "queued": False  # Will be True after Phase 2 implementation
        }
        
    except Exception as e:
        logger.error(f"Error processing incoming message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def whatsapp_service_status():
    """Health check for WhatsApp cloud service"""
    return {
        "status": "operational",
        "service": "whatsapp-cloud-webhook",
        "timestamp": datetime.now().isoformat()
    }
