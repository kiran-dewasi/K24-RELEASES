from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging
import base64
import os
import asyncio
import uuid
from typing import Optional, List

from database import get_db, Ledger, Tenant, User
from auth import get_current_tenant_id
from tools.invoice_tool import invoice_tool
# from graph import run_agent # Avoiding circular import if possible, or lazy import
import google.generativeai as genai

logger = logging.getLogger("baileys")

router = APIRouter(prefix="/api/baileys", tags=["baileys"])

# Setup Gemini
if os.getenv("GOOGLE_API_KEY"):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"), transport="rest")

class BaileysMessageRequest(BaseModel):
    sender_phone: str # +919876543210
    message_text: str
    media: Optional[dict] = None # { type: 'image', buffer: 'base64...', mimetype: '...' }

class BatchImageItem(BaseModel):
    buffer: str  # Base64 encoded image data
    mimetype: str
    filepath: Optional[str] = None

class BaileysMessageBatchRequest(BaseModel):
    sender_phone: str
    images: List[BatchImageItem]
    batch_id: str

# SECURITY: Verify Baileys listener is legitimate
def verify_baileys_secret(request: Request):
    """Validate request is from our Baileys listener"""
    secret = request.headers.get('X-Baileys-Secret')
    expected_secret = os.getenv('BAILEYS_SECRET', 'k24_baileys_secret')

    if secret != expected_secret:
        raise HTTPException(status_code=401, detail='Invalid Baileys secret')

async def extract_from_image(base64_data: str, mime_type: str):
    """Encapsulates Gemini Vision call"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        image_bytes = base64.b64decode(base64_data)
        
        # Simple prompt
        response = model.generate_content([
            "Extract all text and key details (Invoice No, Date, Amount, Party) from this image. Output in clear text.",
            {"mime_type": mime_type, "data": image_bytes}
        ])
        return {"type": "text", "content": response.text}
    except Exception as e:
        logger.error(f"OCR Error: {e}")
        return {"type": "error", "content": "Failed to extract text from image."}

@router.post("/process")
async def process_baileys_message(
    payload: BaileysMessageRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_baileys_secret)
):
    """
    Process incoming WhatsApp message from Baileys with Strict Multi-Tenancy.
    """
    try:
        sender_phone = payload.sender_phone
        message_text = payload.message_text
        media = payload.media
        
        logger.info(f"📬 Processing message from {sender_phone}")
        
        # ============ STEP 1: STRICT TENANT LOOKUP ============
        # Priority 1: Check if it's a Dashboard User (Personal Assistant Mode)
        from database import WhatsAppMapping
        
        user_binding = db.query(User).filter(User.whatsapp_number == sender_phone).first()
        
        tenant_id = None

        if user_binding:
            tenant_id = user_binding.tenant_id
            logger.info(f"✅ Authenticated Dashboard User: {user_binding.username} (Tenant: {tenant_id})")
        
        # --- HARDCODE OVERRIDE FOR 7339906200 & LID ---
        elif "7339906200" in sender_phone or "185628738236618" in sender_phone:
             logger.info(f"🔒 DEBUG OVERRIDE: Forcing {sender_phone} to TENANT-12345")
             # Ensure mapping exists so we don't fall into onboarding next time if we remove this block
             try:
                 existing = db.query(WhatsAppMapping).filter(WhatsAppMapping.whatsapp_number == sender_phone).first()
                 if not existing:
                      logger.info(f"➕ Creating permanent mapping for {sender_phone}")
                      new_map = WhatsAppMapping(whatsapp_number=sender_phone, tenant_id="TENANT-12345")
                      db.add(new_map)
                      db.commit()
             except Exception as map_err:
                 logger.error(f"Mapping creation failed: {map_err}")
             
             tenant_id = "TENANT-12345"
        
        else:
            # Priority 2: Check if it's a Customer/Vendor (External Onboarding)
            mapping = db.query(WhatsAppMapping).filter(
                WhatsAppMapping.whatsapp_number == sender_phone
            ).first()
            
            if mapping:
                tenant_id = mapping.tenant_id
                logger.info(f"✅ Tenant verified via Mapping: {tenant_id}")
            else:
                # Priority 3: Unknown -> Trigger Onboarding
                logger.info(f"🆕 Unmapped user: {sender_phone}. Triggering onboarding.")
                from routers.onboarding_utils import handle_onboarding
                
                response_text = await handle_onboarding(db, sender_phone, message_text)
                return {
                    "status": "success",
                    "reply_message": response_text
                }
        
        # ============ STEP 2: PREPARE IMAGE DATA ============
        image_data = None
        if media and media.get('type') == 'image':
            logger.info("🖼️ Image detected. Preparing for Vision Agent...")
            image_data = media.get('buffer') # Base64 string
            # No manual OCR here. The Agent Router will handle it.
        
        # ============ STEP 3: PASS TO AGENT ============
        try:
            from graph import run_agent
            agent_result = await run_agent(
                message_text=message_text,
                thread_id=sender_phone,
                user_id=tenant_id,
                image_data=image_data
            )
            
            # PERSISTENCE: Log to ChatHistory
            try:
                from database import ChatHistory
                log_entry = ChatHistory(
                    tenant_id=tenant_id,
                    user_phone=sender_phone,
                    message_content=message_text,
                    ai_response=agent_result,
                    has_image=bool(image_data)
                )
                db.add(log_entry)
                db.commit()
            except Exception as log_err:
                logger.error(f"Failed to save chat history: {log_err}")
            
            return {
                "status": "success",
                "reply_message": agent_result or "✅ Processed successfully (No text response)"
            }
            
        except Exception as e:
            logger.error("Agent execution failed", exc_info=True)
            return {
                "status": "error",
                "reply_message": "Something went wrong. Please try again."
            }

    except Exception as e:
        error_ref = uuid.uuid4().hex[:8]
        logger.error("❌ Unhandled error in process_baileys_message [ref=%s]", error_ref, exc_info=True)
        return {
            "status": "error",
            "reply_message": f"Something went wrong. (ref: {error_ref})"
        }

@router.get("/health")
def baileys_health_check():
    """Simple health check for Baileys Listener"""
    return {"status": "ok", "timestamp": "now"}


@router.post("/process-batch")
async def process_batch(
    payload: BaileysMessageBatchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(verify_baileys_secret)
):
    """
    Process a batch of bill images sent via WhatsApp.
    Uses BulkBillProcessor for parallel processing with rate limiting.
    """
    import time
    import tempfile
    from pathlib import Path
    
    start_time = time.time()
    temp_files = []  # Track for cleanup
    
    try:
        sender_phone = payload.sender_phone
        images = payload.images
        batch_id = payload.batch_id
        
        logger.info(f"📦 BATCH PROCESSING: {len(images)} images from {sender_phone}")
        logger.info(f"   Batch ID: {batch_id}")
        
        # ============ TENANT LOOKUP ============
        # Handle both phone numbers and LID (Linked ID) format
        from database import WhatsAppMapping
        
        # Normalize the sender_phone - could be phone number or LID
        is_lid_format = len(sender_phone) > 15 or not sender_phone.startswith('9')
        
        user_binding = None
        tenant_id = None
        
        # Try direct phone match first
        user_binding = db.query(User).filter(User.whatsapp_number == sender_phone).first()
        
        if user_binding:
            tenant_id = user_binding.tenant_id
            logger.info(f"✅ Authenticated Dashboard User: {user_binding.username} (Tenant: {tenant_id})")
        else:
            # Try partial match (for cases like 917339906200 vs 7339906200)
            if "7339906200" in sender_phone:
                # Known dev phone - use default tenant
                tenant_id = "TENANT-12345"
                logger.info(f"✅ Dev phone match: {sender_phone} -> TENANT-12345")
            else:
                # Try WhatsApp mapping table
                mapping = db.query(WhatsAppMapping).filter(
                    WhatsAppMapping.whatsapp_number == sender_phone
                ).first()
                
                if mapping:
                    tenant_id = mapping.tenant_id
                    logger.info(f"✅ Found via WhatsApp mapping: {tenant_id}")
                elif is_lid_format:
                    # LID format - try to find any tenant with matching LID
                    # For now, use default tenant for LID messages (they should bind their phone)
                    logger.warning(f"⚠️ LID format detected: {sender_phone}")
                    
                    # Check if there's a default tenant we can use
                    from database import Tenant
                    default_tenant = db.query(Tenant).first()
                    if default_tenant:
                        tenant_id = default_tenant.id
                        logger.info(f"✅ Using default tenant for LID user: {tenant_id}")
        
        if not tenant_id:
            logger.error(f"❌ No tenant found for: {sender_phone}")
            return {
                "status": "error",
                "error": "Unregistered phone number. Please onboard first.",
                "vouchers": [],
                "stats": {"total": 0, "success": 0, "failed": len(images), "total_items": 0, "total_amount": 0}
            }
        
        # ============ SAVE IMAGES TO TEMP FILES ============
        image_paths = []
        for i, img in enumerate(images):
            try:
                image_bytes = base64.b64decode(img.buffer)
                
                # Create temp file
                suffix = '.jpg' if 'jpeg' in img.mimetype.lower() or 'jpg' in img.mimetype.lower() else '.png'
                tmp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
                tmp_file.write(image_bytes)
                tmp_file.close()
                
                image_paths.append(tmp_file.name)
                temp_files.append(tmp_file.name)
                logger.info(f"  Saved image {i+1} to: {tmp_file.name}")
                
            except Exception as e:
                logger.error(f"  Failed to save image {i+1}: {e}")
        
        if not image_paths:
            return {
                "status": "error",
                "error": "Failed to save any images for processing",
                "vouchers": [],
                "stats": {"total": 0, "success": 0, "failed": len(images), "total_items": 0, "total_amount": 0}
            }
        
        # ============ USE BULK PROCESSOR WITH AUTO-EXECUTION ============
        from services.bulk_processor import BulkBillProcessor
        
        processor = BulkBillProcessor(max_concurrent=10)
        api_key = os.getenv("GOOGLE_API_KEY")
        
        # Process batch in parallel with auto-execution
        result = await processor.process_batch(
            image_paths=image_paths,
            user_id=tenant_id,
            api_key=api_key,
            auto_post_enabled=False
        )
        
        # ============ COMPILE STATS ============
        results = result.get('results', [])
        
        stats = {
            "total": len(results),
            "success": sum(1 for r in results if r.get('status') == 'success'),
            "failed": sum(1 for r in results if r.get('status') == 'error'),
            "total_items": sum(r.get('items_count', 0) for r in results if r.get('status') == 'success'),
            "total_amount": sum(
                float(r.get('total_amount', 0) or r.get('voucher', {}).get('total_amount', 0) or 0)
                for r in results if r.get('status') == 'success'
            ),
            "elapsed_seconds": result.get('elapsed_seconds', round(time.time() - start_time, 2)),
            # Auto-execution breakdown
            "auto_posted": result.get('auto_posted', 0),
            "auto_created": result.get('auto_created', 0),
            "needs_review": result.get('needs_review', 0),
            "needs_clarification": result.get('needs_clarification', 0)
        }
        
        # Extract voucher summaries
        vouchers = []
        questions = []  # Collect any clarification questions
        
        for r in results:
            if r.get('status') == 'success':
                voucher_data = r.get('voucher', {})
                vouchers.append({
                    "party": r.get('party_name') or voucher_data.get('party_name', 'Unknown'),
                    "party_name": r.get('party_name') or voucher_data.get('party_name', 'Unknown'),
                    "amount": r.get('total_amount') or voucher_data.get('total_amount', 0),
                    "total_amount": r.get('total_amount') or voucher_data.get('total_amount', 0),
                    "items_count": r.get('items_count', 0),
                    "confidence": r.get('confidence', 0.0),
                    "confidence_level": r.get('confidence_level', 'unknown'),
                    "action": r.get('action', 'unknown'),
                    "voucher_id": voucher_data.get('id') if isinstance(voucher_data, dict) else None,
                    "message": r.get('message')
                })
            
            # Collect any questions for clarification
            if r.get('action') == 'needs_clarification' and r.get('question'):
                questions.append({
                    "image": r.get('image', ''),
                    "question": r.get('question'),
                    "party_name": r.get('party_name', 'Unknown')
                })
        
        # ============ CLEANUP IN BACKGROUND ============
        background_tasks.add_task(cleanup_temp_files, temp_files)
        
        logger.info(f"📦 BATCH COMPLETE: {stats['success']}/{stats['total']} in {stats['elapsed_seconds']}s")
        logger.info(f"   ✅ Auto-posted: {stats['auto_posted']} | Auto-created: {stats['auto_created']}")
        logger.info(f"   ⚠️ Needs review: {stats['needs_review']} | ❓ Clarifications: {stats['needs_clarification']}")
        
        return {
            "status": "success",
            "vouchers": vouchers,
            "stats": stats,
            "batch_id": batch_id,
            "questions": questions if questions else None  # Include if any clarifications needed
        }
        
    except Exception as e:
        error_ref = uuid.uuid4().hex[:8]
        logger.error("❌ Batch processing error [ref=%s]", error_ref, exc_info=True)

        # Still schedule cleanup even on error
        if temp_files:
            background_tasks.add_task(cleanup_temp_files, temp_files)

        return {
            "status": "error",
            "error": f"Batch processing failed. (ref: {error_ref})",
            "vouchers": [],
            "stats": {"total": 0, "success": 0, "failed": 0, "total_items": 0, "total_amount": 0}
        }


async def cleanup_temp_files(file_paths: List[str]):
    """Delete temporary image files after processing"""
    from pathlib import Path
    import asyncio
    
    await asyncio.sleep(5)  # Wait a bit before cleanup
    
    for path in file_paths:
        try:
            Path(path).unlink()
            logger.info(f"  🗑️ Cleaned up: {path}")
        except Exception as e:
            logger.warning(f"  Failed to delete {path}: {e}")


@router.get("/status")
def get_baileys_status(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Returns the connection status of the Baileys listener.
    Used by the Frontend Settings page.
    """
    tn = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if tn and tn.whatsapp_number:
        return {
            "whatsapp_connected": True,
            "phone_number": tn.whatsapp_number,
            "qr_code": None
        }
    
    return {
        "whatsapp_connected": False,
        "phone_number": None,
        "qr_code": None
    }
