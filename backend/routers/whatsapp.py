from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import sqlite3
import uuid
from datetime import datetime

from database import get_db, Tenant, WhatsAppMapping, Ledger
from dependencies import get_api_key
from auth import get_current_tenant_id, get_current_user

router = APIRouter(tags=["whatsapp"])

# ============================================
# EXISTING TENANT / MAPPING ENDPOINTS
# ============================================

# --- Models ---
class WhatsAppWebhook(BaseModel):
    # Simplified payload structure matching hypothetical WA Provider
    from_number: str # The sender (customer)
    to_number: str   # The recipient (business)
    message: str

# --- Routes ---

@router.get("/tenants/by-whatsapp/{wa_number}")
async def get_tenant_by_whatsapp(wa_number: str, db: Session = Depends(get_db)):
    """
    Public Endpoint: Resolve Tenant ID from Business WhatsApp Number.
    Used by the WhatsApp Gateway to route incoming messages.
    """
    tenant = db.query(Tenant).filter(
        Tenant.whatsapp_number == wa_number
    ).first()

    if not tenant:
        # Fallback or error?
        raise HTTPException(status_code=404, detail="Tenant not found for this number")

    return {
        "tenant_id": tenant.id,
        "company_name": tenant.company_name,
        "tally_company_name": tenant.tally_company_name
    }

@router.get("/contacts/by-whatsapp/{wa_number}", dependencies=[Depends(get_api_key)])
async def get_contact_by_whatsapp(
    wa_number: str, 
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Identify which Contact (Ledger) owns this phone number.
    Checks 'ledgers.phone' first, then 'whatsapp_mappings'.
    """
    # 1. Direct Match on Ledger Phone
    contact = db.query(Ledger).filter(
        Ledger.tenant_id == tenant_id,
        Ledger.phone == wa_number
    ).first()

    if contact:
        return {
            "id": contact.id,
            "name": contact.name,
            "group": contact.parent,
            "phone": contact.phone,
            "source": "ledger"
        }
        
    # 2. Check Mapping Table
    mapping = db.query(WhatsAppMapping).filter(
        WhatsAppMapping.tenant_id == tenant_id,
        WhatsAppMapping.whatsapp_number == wa_number
    ).first()
    
    if mapping and mapping.contact_id:
        contact = db.query(Ledger).filter(Ledger.id == mapping.contact_id).first()
        if contact:
             return {
                "id": contact.id,
                "name": contact.name,
                "group": contact.parent,
                "phone": contact.phone,
                "source": "mapping"
            }

    raise HTTPException(status_code=404, detail="Contact not identified")

# ============================================================================
# DEPRECATED: Meta WhatsApp API Integration
# Status: Commented out (keeping for future production upgrade)
# Reason: Switched to Baileys for faster MVP (Phase E)
# Plan: Migrate back to this when Meta approval is complete
# ============================================================================
# COMMENTED OUT - Meta API Webhook Handler
# @router.post("/webhooks/whatsapp")
# async def whatsapp_webhook(payload: dict, db: Session = Depends(get_db)):
#     """
#     Handle incoming WhatsApp Message.
#     1. Identify Tenant (via 'to' number)
#     2. Identify Contact (via 'from' number)
#     3. Log/Store Mapping (if new)
#     """
#     # Defensive parsing
#     # Payload structure depends on provider (Twilio/Meta/WIB). Assuming simple dict wrapper for MVP.
#     # In real world, this needs parsing specific JSON structure.
#     
#     # Example Payload: { "from": "+91999...", "to": "+91888...", "message": "Hi" }
#     # from_number = payload.get("from") or payload.get("sender")
#     # to_number = payload.get("to") or payload.get("recipient")
#     # message_text = payload.get("message") or payload.get("text")
#     
#     # if not from_number or not to_number:
#     #      raise HTTPException(status_code=400, detail="Invalid Payload")
# 
#     # 1. Tenant lookup
#     # tenant = db.query(Tenant).filter(Tenant.whatsapp_number == to_number).first()
#     # if not tenant:
#     #     print(f"⚠️  Unknown Business Number: {to_number}")
#     #     return {"status": "ignored", "reason": "unknown_business"}
#     
#     # 2. Contact lookup
#     # Check Ledger first
#     # contact = db.query(Ledger).filter(
#     #     Ledger.tenant_id == tenant.id,
#     #     Ledger.phone == from_number
#     # ).first()
#     
#     # contact_id = contact.id if contact else None
#     
#     # 3. Store in WhatsAppMapping (Upsert logic ideally, or just insert if not exists)
#     # Check if mapping exists
#     # existing_map = db.query(WhatsAppMapping).filter(
#     #     WhatsAppMapping.tenant_id == tenant.id,
#     #     WhatsAppMapping.whatsapp_number == from_number
#     # ).first()
#     
#     # if not existing_map:
#     #     new_map = WhatsAppMapping(
#     #         tenant_id=tenant.id,
#     #         whatsapp_number=from_number,
#     #         contact_id=contact_id
#     #     )
#     #     db.add(new_map)
#     #     db.commit()
#     #     print(f"✅ New WhatsApp Identity Mapped: {from_number} -> Tenant {tenant.id}")
#     # elif contact_id and not existing_map.contact_id:
#     #     # Update mapping if we now know the contact
#     #     existing_map.contact_id = contact_id
#     #     db.commit()
#     #     print(f"🔄 Updated WhatsApp Identity: {from_number} linked to {contact.name}")
# 
#     # TODO: Trigger Agent Workflow (LangGraph)
#     
#     # return {"status": "ok", "tenant": tenant.id, "contact": contact.name if contact else "Unknown"}

# --- Admin Routes ---
class TenantUpdate(BaseModel):
    whatsapp_number: str

@router.get("/settings/whatsapp", dependencies=[Depends(get_api_key)])
async def get_whatsapp_settings(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Get the Tenant's WhatsApp Settings.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant or not tenant.whatsapp_number:
        return {
            "whatsapp_number": None,
            "connected": False
        }
    
    return {
        "whatsapp_number": tenant.whatsapp_number,
        "connected": True
    }

@router.put("/settings/whatsapp", dependencies=[Depends(get_api_key)])
async def update_whatsapp_settings(
    settings: TenantUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Update the Business WhatsApp Number for this Tenant.
    """
    # Upsert Tenant record
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        # Auto-create if missing (Self-healing)
        # In real app, Tenant should exist on registration.
        from database import Company
        # Try to find company name
        # This is a bit disjointed due to MVP schema evolution.
        # Ideally fetch name from User's company.
        tenant = Tenant(
            id=tenant_id,
            company_name="My Company", # Placeholder
            whatsapp_number=settings.whatsapp_number
        )
        db.add(tenant)
    else:
        tenant.whatsapp_number = settings.whatsapp_number
        
    db.commit()
    return {"status": "success", "number": settings.whatsapp_number}

# ============================================
# CUSTOMER MAPPING SYSTEM (NEW)
# ============================================

# ============================================
# REQUEST MODELS
# ============================================

class CustomerMappingCreate(BaseModel):
    customer_name: str
    customer_phone: str  # Format: +91XXXXXXXXXX
    client_code: Optional[str] = None
    notes: Optional[str] = None

class CustomerMappingUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    client_code: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

# ============================================
# ENDPOINTS
# ============================================

@router.get("/api/whatsapp/customers")
async def list_customer_mappings(
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """
    List all WhatsApp customer mappings for current user
    """
    user_id = str(current_user["id"]) if isinstance(current_user, dict) else str(current_user.id)
    
    conn = sqlite3.connect("k24_shadow.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # First, ensure table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_customer_mappings (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            client_code TEXT,
            notes TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    
    # Create index for fast lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_whatsapp_phone 
        ON whatsapp_customer_mappings(customer_phone)
    """)
    
    conn.commit()
    
    # Query mappings
    if search:
        cursor.execute("""
            SELECT * FROM whatsapp_customer_mappings
            WHERE user_id = ?
            AND (customer_name LIKE ? OR customer_phone LIKE ?)
            ORDER BY customer_name
            LIMIT ? OFFSET ?
        """, (user_id, f'%{search}%', f'%{search}%', limit, offset))
    else:
        cursor.execute("""
            SELECT * FROM whatsapp_customer_mappings
            WHERE user_id = ?
            ORDER BY customer_name
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset))
    
    mappings = [dict(row) for row in cursor.fetchall()]
    
    # Get total count
    cursor.execute("""
        SELECT COUNT(*) as total 
        FROM whatsapp_customer_mappings 
        WHERE user_id = ?
    """, (user_id,))
    
    total = cursor.fetchone()['total']
    conn.close()
    
    return {
        "mappings": mappings,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/api/whatsapp/customers")
async def create_customer_mapping(
    mapping: CustomerMappingCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Add new customer phone mapping (synced to Supabase)
    """
    user_id = str(current_user["id"]) if isinstance(current_user, dict) else str(current_user.id)
    tenant_id = current_user.get("tenant_id") if isinstance(current_user, dict) else getattr(current_user, "tenant_id", None)
    
    # Validate phone format
    phone = mapping.customer_phone.strip()
    if not phone.startswith('+'):
        phone = f"+91{phone}"  # Add India code if missing
    
    # Validate phone length (E.164 format)
    if len(phone) < 10 or len(phone) > 15:
        raise HTTPException(status_code=400, detail="Invalid phone number format")
    
    conn = sqlite3.connect("k24_shadow.db")
    cursor = conn.cursor()
    
    # Check for duplicates (same user + same phone)
    cursor.execute("""
        SELECT id FROM whatsapp_customer_mappings
        WHERE user_id = ? AND customer_phone = ?
    """, (user_id, phone))
    
    existing = cursor.fetchone()
    if existing:
        conn.close()
        raise HTTPException(
            status_code=400, 
            detail=f"Customer with phone {phone} already registered"
        )
    
    # Insert new mapping
    mapping_id = f"wacust_{uuid.uuid4().hex[:12]}"
    cursor.execute("""
        INSERT INTO whatsapp_customer_mappings 
        (id, user_id, customer_name, customer_phone, client_code, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        mapping_id,
        user_id,
        mapping.customer_name,
        phone,
        mapping.client_code,
        mapping.notes
    ))
    
    conn.commit()
    conn.close()

    # ── Sync to Supabase (non-blocking) ──────────────────────────────────────
    try:
        from services.supabase_service import supabase_http_service
        if supabase_http_service.client:
            import httpx
            headers = supabase_http_service._get_headers(use_service_key=True)
            httpx.post(
                f"{supabase_http_service.url}/rest/v1/whatsapp_customer_mappings",
                headers={**headers, "Prefer": "resolution=merge-duplicates,return=minimal"},
                json={
                    "id": mapping_id,
                    "user_id": user_id,
                    "tenant_id": tenant_id or "",
                    "customer_name": mapping.customer_name,
                    "customer_phone": phone,
                    "client_code": mapping.client_code,
                    "notes": mapping.notes,
                    "is_active": True,
                },
                timeout=10
            )
            print(f"✅ Customer mapping synced to Supabase: {phone}")
    except Exception as e:
        print(f"⚠️ Supabase customer sync warning (non-fatal): {e}")

    return {
        "id": mapping_id,
        "message": "Customer mapping created successfully",
        "phone": phone
    }


@router.put("/api/whatsapp/customers/{mapping_id}")
async def update_customer_mapping(
    mapping_id: str,
    update: CustomerMappingUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update existing customer mapping
    """
    user_id = str(current_user["id"]) if isinstance(current_user, dict) else str(current_user.id)
    
    conn = sqlite3.connect("k24_shadow.db")
    cursor = conn.cursor()
    
    # Verify ownership
    cursor.execute("""
        SELECT id FROM whatsapp_customer_mappings
        WHERE id = ? AND user_id = ?
    """, (mapping_id, user_id))
    
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    # Build update query dynamically
    updates = []
    params = []
    
    if update.customer_name is not None:
        updates.append("customer_name = ?")
        params.append(update.customer_name)
    
    if update.customer_phone is not None:
        phone = update.customer_phone.strip()
        if not phone.startswith('+'):
            phone = f"+91{phone}"
        updates.append("customer_phone = ?")
        params.append(phone)
    
    if update.client_code is not None:
        updates.append("client_code = ?")
        params.append(update.client_code)
    
    if update.notes is not None:
        updates.append("notes = ?")
        params.append(update.notes)
    
    if update.is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if update.is_active else 0)
    
    updates.append("updated_at = datetime('now')")
    
    if updates:
        params.append(mapping_id)
        params.append(user_id)
        
        query = f"""
            UPDATE whatsapp_customer_mappings 
            SET {', '.join(updates)}
            WHERE id = ? AND user_id = ?
        """
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()
    
    return {"message": "Mapping updated successfully"}


@router.delete("/api/whatsapp/customers/{mapping_id}")
async def delete_customer_mapping(
    mapping_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete/deactivate customer mapping (synced to Supabase)
    """
    user_id = str(current_user["id"]) if isinstance(current_user, dict) else str(current_user.id)
    
    conn = sqlite3.connect("k24_shadow.db")
    cursor = conn.cursor()
    
    # Soft delete (set is_active = 0)
    cursor.execute("""
        UPDATE whatsapp_customer_mappings
        SET is_active = 0, updated_at = datetime('now')
        WHERE id = ? AND user_id = ?
    """, (mapping_id, user_id))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    conn.commit()
    conn.close()

    # ── Sync delete to Supabase (soft-delete: set is_active = false) ─────────
    try:
        from services.supabase_service import supabase_http_service
        if supabase_http_service.client:
            import httpx
            httpx.patch(
                f"{supabase_http_service.url}/rest/v1/whatsapp_customer_mappings?id=eq.{mapping_id}",
                headers=supabase_http_service._get_headers(use_service_key=True),
                json={"is_active": False},
                timeout=10
            )
    except Exception as e:
        print(f"⚠️ Supabase delete sync warning (non-fatal): {e}")

    return {"message": "Mapping deleted successfully"}

# ============================================
# BOT NUMBER CONFIGURATION
# ============================================

class BotNumberUpdate(BaseModel):
    whatsapp_number: str

@router.get("/api/whatsapp/bot-number")
async def get_bot_number(
    current_user: dict = Depends(get_current_user)
):
    """
    Get the tenant's registered bot WhatsApp number from Supabase tenant_config.
    This is the number the cloud backend routes incoming messages TO.
    """
    import httpx, os

    tenant_id = current_user.get("tenant_id") if isinstance(current_user, dict) else getattr(current_user, "tenant_id", None)
    if not tenant_id:
        return {"whatsapp_number": None, "configured": False}

    supa_url = os.getenv("SUPABASE_URL", "https://gxukvnoiyzizienswgni.supabase.co")
    supa_key = os.getenv("SUPABASE_SERVICE_KEY", "sb_secret_qJuJk2q0_hO144oQLmSYxA_6WB_qtkR")
    headers = {"apikey": supa_key, "Authorization": f"Bearer {supa_key}"}

    try:
        resp = httpx.get(
            f"{supa_url}/rest/v1/tenant_config",
            params={"tenant_id": f"eq.{tenant_id}", "select": "whatsapp_number"},
            headers=headers,
            timeout=10
        )
        data = resp.json()
        if data and len(data) > 0 and data[0].get("whatsapp_number"):
            return {"whatsapp_number": data[0]["whatsapp_number"], "configured": True}
        return {"whatsapp_number": None, "configured": False}
    except Exception as e:
        print(f"[bot-number] fetch error: {e}")
        return {"whatsapp_number": None, "configured": False}


@router.put("/api/whatsapp/bot-number")
async def update_bot_number(
    body: BotNumberUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Save / update the bot WhatsApp number in Supabase tenant_config (upsert).
    This is the CRITICAL step that registers the tenant with the Cloud routing engine.
    When changed, the cloud will immediately start routing to the new number.
    """
    import httpx, os

    tenant_id = current_user.get("tenant_id") if isinstance(current_user, dict) else getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant_id found for this user. Please log in again.")

    # Normalize to E.164 format
    phone = body.whatsapp_number.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = f"+91{phone}"
    if len(phone) < 10 or len(phone) > 16:
        raise HTTPException(status_code=400, detail="Invalid phone number. Use format: +91XXXXXXXXXX")

    supa_url = os.getenv("SUPABASE_URL", "https://gxukvnoiyzizienswgni.supabase.co")
    supa_key = os.getenv("SUPABASE_SERVICE_KEY", "sb_secret_qJuJk2q0_hO144oQLmSYxA_6WB_qtkR")
    headers = {
        "apikey": supa_key,
        "Authorization": f"Bearer {supa_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal"
    }

    try:
        resp = httpx.post(
            f"{supa_url}/rest/v1/tenant_config",
            headers=headers,
            json={"tenant_id": tenant_id, "whatsapp_number": phone},
            timeout=10
        )
        if resp.status_code in (200, 201, 204):
            print(f"[bot-number] Updated Supabase tenant_config for {tenant_id}: {phone}")
            return {"status": "success", "whatsapp_number": phone}
        else:
            print(f"[bot-number] Supabase error {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=500, detail=f"Supabase error: {resp.text[:200]}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save: {str(e)}")


# ============================================
# MESSAGE STATS
# ============================================

@router.get("/api/whatsapp/message-stats")
async def get_message_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Return real sent/received WhatsApp message counts from the local queue DB.
    Counts rows in whatsapp_message_queue per direction.
    """
    user_id = str(current_user["id"]) if isinstance(current_user, dict) else str(current_user.id)

    conn = sqlite3.connect("k24_shadow.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Ensure table exists before querying (safe guard)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_message_queue (
            id TEXT PRIMARY KEY,
            tenant_id TEXT,
            user_id TEXT,
            direction TEXT DEFAULT 'inbound',
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Count messages sent (outbound) by this user
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM whatsapp_message_queue
        WHERE user_id = ? AND direction IN ('outbound', 'sent')
    """, (user_id,))
    sent = cursor.fetchone()["cnt"]

    # Count messages received (inbound) by this user
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM whatsapp_message_queue
        WHERE user_id = ? AND direction IN ('inbound', 'received')
    """, (user_id,))
    received = cursor.fetchone()["cnt"]

    conn.close()

    return {
        "sent": sent,
        "received": received,
        "total": sent + received
    }


@router.post("/api/whatsapp/identify-user")
async def identify_user_by_phone(phone: str):
    """
    Identify which K24 user/tenant owns this customer phone number
    Used by Baileys listener for multi-tenant routing
    
    Phase 3: Now includes tenant_id for proper data isolation
    """
    conn = sqlite3.connect("k24_shadow.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Query with tenant_id by joining with users table
    cursor.execute("""
        SELECT 
            wcm.user_id, 
            wcm.customer_name, 
            wcm.client_code,
            u.tenant_id
        FROM whatsapp_customer_mappings wcm
        LEFT JOIN users u ON CAST(wcm.user_id AS TEXT) = CAST(u.id AS TEXT)
        WHERE wcm.customer_phone = ? AND wcm.is_active = 1
    """, (phone,))
    
    matches = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if len(matches) == 0:
        return {
            "status": "unknown",
            "message": "Phone number not registered",
            "user_id": None,
            "tenant_id": None
        }
    elif len(matches) == 1:
        return {
            "status": "found",
            "user_id": matches[0]['user_id'],
            "tenant_id": matches[0]['tenant_id'],  # <-- NEW for routing!
            "customer_name": matches[0]['customer_name']
        }
    else:
        # Multiple users have this customer (conflict)
        return {
            "status": "conflict",
            "message": "Multiple users registered this number",
            "matches": matches  # Each match now includes tenant_id
        }
