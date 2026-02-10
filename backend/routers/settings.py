from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sqlite3
from typing import Optional

from backend.auth import get_current_user
from backend.database.encryption import encryptor

router = APIRouter(tags=["settings"])

class WhatsAppSettingsModel(BaseModel):
    whatsapp_number: str
    auto_respond: bool = True
    auto_post_to_tally: bool = False

@router.get("/api/settings/whatsapp")
async def get_whatsapp_settings(current_user: dict = Depends(get_current_user)):
    """
    Get user's WhatsApp settings and connection status
    """
    user_id = current_user.id
    
    conn = sqlite3.connect("k24_shadow.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            tenant_id,
            whatsapp_number,
            whatsapp_connected,
            whatsapp_qr_code
        FROM users
        WHERE id = ?
    """, (user_id,))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "tenant_id": user['tenant_id'],
        "whatsapp_number": encryptor.decrypt(user['whatsapp_number']),
        "connected": bool(user['whatsapp_connected']),
        "qr_code": user['whatsapp_qr_code'],
        "auto_respond": True,  # Get from settings table if exists
        "auto_post_to_tally": False
    }


@router.put("/api/settings/whatsapp")
async def update_whatsapp_settings(
    settings: WhatsAppSettingsModel,
    current_user: dict = Depends(get_current_user)
):
    """
    Update WhatsApp settings for user
    """
    user_id = current_user.id
    
    # Validate phone format
    phone = settings.whatsapp_number.strip()
    if not phone.startswith('+'):
        phone = f"+91{phone}"
    
    conn = sqlite3.connect("k24_shadow.db")
    cursor = conn.cursor()
    
    # Update user's WhatsApp number
    cursor.execute("""
        UPDATE users
        SET whatsapp_number = ?,
            updated_at = datetime('now')
        WHERE id = ?
    """, (encryptor.encrypt(phone), user_id))
    
    conn.commit()
    conn.close()
    
    return {
        "message": "WhatsApp settings updated",
        "whatsapp_number": phone
    }


@router.post("/api/whatsapp/generate-code")
async def generate_whatsapp_code(current_user: dict = Depends(get_current_user)):
    """
    Generate a unique connection code for WhatsApp binding
    Used when user wants to connect their WhatsApp to K24
    """
    import random
    import string
    
    user_id = str(current_user.id)
    
    # Generate 6-digit code
    code = ''.join(random.choices(string.digits, k=6))
    
    # Store in database with expiry (15 minutes)
    conn = sqlite3.connect("k24_shadow.db")
    cursor = conn.cursor()
    
    # Create temp codes table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_binding_codes (
            code TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT DEFAULT (datetime('now', '+15 minutes')),
            used INTEGER DEFAULT 0
        )
    """)
    
    # Get tenant_id
    cursor.execute("SELECT tenant_id FROM users WHERE id = ?", (user_id,))
    tenant = cursor.fetchone()
    tenant_id = tenant[0] if tenant else None
    
    # Insert code
    cursor.execute("""
        INSERT INTO whatsapp_binding_codes (code, user_id, tenant_id)
        VALUES (?, ?, ?)
    """, (code, user_id, tenant_id))
    
    conn.commit()
    conn.close()
    
    return {
        "code": code,
        "tenant_id": tenant_id,
        "expires_in_minutes": 15,
        "instructions": f"Send this code to K24's WhatsApp number to connect: {code}"
    }


@router.post("/api/whatsapp/verify-code")
async def verify_whatsapp_code(code: str, phone: str):
    """
    Verify WhatsApp binding code sent by user
    Called by Baileys listener when user sends code
    """
    conn = sqlite3.connect("k24_shadow.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Find valid code
    cursor.execute("""
        SELECT * FROM whatsapp_binding_codes
        WHERE code = ?
        AND used = 0
        AND datetime('now') < expires_at
    """, (code,))
    
    binding = cursor.fetchone()
    
    if not binding:
        conn.close()
        return {
            "valid": False,
            "message": "Invalid or expired code"
        }
    
    # Mark code as used
    cursor.execute("""
        UPDATE whatsapp_binding_codes
        SET used = 1
        WHERE code = ?
    """, (code,))
    
    # Update user's WhatsApp number
    cursor.execute("""
        UPDATE users
        SET whatsapp_number = ?,
            whatsapp_connected = 1,
            updated_at = datetime('now')
        WHERE id = ?
    """, (encryptor.encrypt(phone), binding['user_id']))
    
    conn.commit()
    conn.close()
    

# ==============================================================================
# API KEY MANAGEMENT (Secured with Encryption)
# ==============================================================================

from backend.database import get_db, UserSettings as UserSettingsDB
from sqlalchemy.orm import Session

class ApiKeyRequest(BaseModel):
    api_key: str

@router.post("/api/ai/verify-key")
async def verify_gemini_key(data: ApiKeyRequest):
    """Test if Gemini API key is valid"""
    try:
        # Use simple HTTP request to avoid heavy import if possible, 
        # or minimal genai check
        import google.generativeai as genai
        genai.configure(api_key=data.api_key)
        
        # Simple generation to test auth
        model = genai.GenerativeModel('gemini-pro')
        # We set stream=True and break immediately to save tokens/time
        response = model.generate_content("test", stream=True)
        for chunk in response:
            break
            
        return {"valid": True}
    except Exception as e:
        return {"valid": False, "error": str(e)}

@router.post("/api/settings/save-api-key")
async def save_api_key(
    data: ApiKeyRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save encrypted API key"""
    user_id = current_user.id
    
    # Encrypt the key
    encrypted_key = encryptor.encrypt(data.api_key)
    
    # Check if settings exist
    settings = db.query(UserSettingsDB).filter(UserSettingsDB.user_id == user_id).first()
    
    if not settings:
        settings = UserSettingsDB(
            user_id=user_id,
            google_api_key=encrypted_key  # Storing encrypted key here
        )
        db.add(settings)
    else:
        settings.google_api_key = encrypted_key
    
    db.commit()
    
    return {"success": True, "message": "API key encrypted and saved"}

@router.get("/api/settings/has-api-key")
async def has_api_key(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user configured API key"""
    user_id = current_user.id
    settings = db.query(UserSettingsDB).filter(UserSettingsDB.user_id == user_id).first()
    
    has_key = bool(settings and settings.google_api_key)
    return {"has_key": has_key}

