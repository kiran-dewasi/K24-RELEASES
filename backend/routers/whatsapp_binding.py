from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import secrets
from datetime import datetime, timezone
import os
import logging

from backend.database import get_db, User
from backend.auth import get_current_active_user

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp-binding"])
logger = logging.getLogger("whatsapp-binding")

class GenerateCodeResponse(BaseModel):
    code: str
    instructions: str

class VerifyWebhookRequest(BaseModel):
    sender_number: str
    code: str

@router.post("/generate-code", response_model=GenerateCodeResponse)
def generate_whatsapp_code(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a 6-digit code for the user to verify their WhatsApp number.
    Using secrets for secure random generation.
    """
    # 1. Generate 6-digit secure code
    verification_code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    
    # 2. Store in DB
    current_user.whatsapp_verification_code = verification_code
    # Optionally: Set expiry logic in future, for now simple string match
    db.commit()
    db.refresh(current_user)
    
    return {
        "code": verification_code,
        "instructions": f"Open WhatsApp and send this message to our bot: VERIFY {verification_code}"
    }

@router.post("/verify-webhook")
def verify_whatsapp_webhook(
    payload: VerifyWebhookRequest,
    x_baileys_secret: str = Header(None, alias="X-Baileys-Secret"),
    db: Session = Depends(get_db)
):
    """
    Called by Baileys Listener when it receives a 'VERIFY <CODE>' message.
    Phase 3: Now includes tenant_id linking for multi-tenant routing.
    """
    # 1. Security Check
    expected_secret = os.getenv('BAILEYS_SECRET', 'k24_baileys_secret')
    if x_baileys_secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid Secret")

    code = payload.code.strip()
    sender = payload.sender_number.strip()
    
    # 2. Check if user exists with this code
    user = db.query(User).filter(User.whatsapp_verification_code == code).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Invalid or expired verification code")
    
    # 3. Phase 3 Security: Check if WhatsApp number is already bound to ANOTHER tenant
    from backend.database import Tenant
    
    existing_binding = db.query(User).filter(
        User.whatsapp_number == sender,
        User.id != user.id,  # Not the same user
        User.is_whatsapp_verified == True
    ).first()
    
    if existing_binding:
        logger.warning(f"[SECURITY] WhatsApp {sender} already bound to user {existing_binding.id}")
        raise HTTPException(
            status_code=409,
            detail="This WhatsApp number is already linked to another account. Please contact support."
        )
    
    # 4. Bind Number (with row locking for race condition prevention)
    # SQLite doesn't support FOR UPDATE, but we commit quickly to minimize race window
    user.whatsapp_number = sender
    user.is_whatsapp_verified = True
    user.whatsapp_verification_code = None  # Clear code after use
    user.whatsapp_linked_at = datetime.now(timezone.utc)
    
    # 5. Also update tenant's WhatsApp number if tenant exists
    tenant_id = getattr(user, 'tenant_id', None)
    if tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant:
            # Check tenant-level conflict
            existing_tenant = db.query(Tenant).filter(
                Tenant.whatsapp_number == sender,
                Tenant.id != tenant_id
            ).first()
            
            if existing_tenant:
                logger.warning(f"[SECURITY] WhatsApp {sender} already bound to tenant {existing_tenant.id}")
                raise HTTPException(
                    status_code=409,
                    detail="This WhatsApp number is already linked to another business."
                )
            
            tenant.whatsapp_number = sender
            logger.info(f"[TENANT] Linked WhatsApp {sender} to tenant {tenant_id}")
    
    db.commit()
    
    logger.info(f"Successfully linked WhatsApp {sender} to user {user.username} (tenant: {tenant_id})")
    
    return {
        "status": "success",
        "user_name": user.full_name,
        "tenant_id": tenant_id,  # <-- NEW: Include for routing!
        "message": "WhatsApp number linked successfully"
    }
