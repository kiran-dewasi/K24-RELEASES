import os
import json
import hmac
import hashlib
import time
import httpx
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
SUPPORTED_WEBHOOK_EVENTS = {"payment_link.paid", "payment.captured"}


def _get_razorpay_webhook_secret() -> Optional[str]:
    return os.getenv("RAZORPAY_WEBHOOK_SECRET")


def _first_dict(*values: Any) -> dict[str, Any]:
    for value in values:
        if isinstance(value, dict):
            return value
    return {}

class CreatePaymentLinkRequest(BaseModel):
    tenant_id: str
    plan_id: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    source: str = "app"

@router.post("/create-link")
async def create_payment_link(req: CreatePaymentLinkRequest):
    sb = get_supabase_client()
    
    # 1. Load plan from Supabase
    res = sb.table("plans").select("*").eq("id", req.plan_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan = res.data[0]
    
    annual_base_paise = int(plan.get("price_monthly_paise") or 0)
    amount = int(annual_base_paise * 1.18)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid plan amount")

    ref_id = f"{req.tenant_id}_{int(time.time())}"
    
    # Step 1: Look up user_id from users_profile table
    user_res = sb.table("users_profile").select("id").eq("tenant_id", req.tenant_id).limit(1).execute()
    if not user_res.data:
        raise HTTPException(status_code=404, detail="No user found for tenant")
    user_id = user_res.data[0]["id"]
    
    # Step 2: Insert a pending row in subscriptions
    sub_data = {
        "user_id": user_id,
        "tenant_id": req.tenant_id,
        "plan": req.plan_id,
        "status": "pending",
    }
    sub_insert = sb.table("subscriptions").insert(sub_data).execute()
    sub_id = sub_insert.data[0]["id"] if sub_insert.data else None
    
    payload: dict[str, Any] = {
        "amount": amount,
        "currency": "INR",
        "accept_partial": False,
        "reference_id": ref_id,
        "description": f"{plan.get('display_name', req.plan_id)} Annual Subscription incl. 18% GST",
        "customer": {},
        "notes": {
            "tenant_id": req.tenant_id,
            "plan_id": req.plan_id,
            "source": req.source,
            "subscription_id": sub_id or ""
        }
    }
    
    if req.customer_name:
        payload["customer"]["name"] = req.customer_name
    if req.customer_email:
        payload["customer"]["email"] = req.customer_email
    if req.customer_phone:
        payload["customer"]["contact"] = req.customer_phone
        
    auth = (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=500, detail="Razorpay credentials not configured")
        
    # 2. Create payment link using direct API
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.razorpay.com/v1/payment_links",
            json=payload,
            auth=auth,
            headers={"Content-Type": "application/json"}
        )
        if resp.status_code >= 400:
            logger.error(f"Razorpay link creation failed: {resp.text}")
            raise HTTPException(status_code=resp.status_code, detail="Failed to create payment link")
            
        rp_data = resp.json()
    
    link_id = rp_data.get("id")
    link_url = rp_data.get("short_url")
    
    # Step 3: Store sub_id and payment_link_id in return response
    return {
        "payment_link_url": link_url,
        "payment_link_id": link_id,
        "subscription_id": sub_id,
        "amount": amount,
        "plan_id": req.plan_id
    }

@router.post("/webhook")
async def razorpay_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    webhook_secret = _get_razorpay_webhook_secret()
    
    if not signature or not webhook_secret:
        raise HTTPException(status_code=400, detail="Missing signature or internal secret misconfigured")
    
    # Validate Signature
    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    logger.info("Razorpay webhook signature verified")
        
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    event = payload.get("event")
    logger.info("Razorpay webhook received: event=%s", event)
    # Only handle successful payment events that can complete a payment-link purchase.
    if event not in SUPPORTED_WEBHOOK_EVENTS:
        logger.info("Razorpay webhook ignored: event=%s", event)
        return {"ok": True, "msg": f"Ignored event: {event}"}

    event_payload = payload.get("payload", {})
    payment_link_entity = _first_dict(
        event_payload.get("payment_link", {}).get("entity"),
        event_payload.get("order", {}).get("entity"),
    )
    payment_entity = _first_dict(event_payload.get("payment", {}).get("entity"))
    payment_id = payment_entity.get("id")

    notes = _first_dict(
        payment_link_entity.get("notes"),
        payment_entity.get("notes"),
        event_payload.get("order", {}).get("entity", {}).get("notes"),
    )
    tenant_id = notes.get("tenant_id")
    plan_id = notes.get("plan_id")
    
    if not payment_id or not tenant_id or not plan_id:
        # Fallback to payment entity notes
        notes = _first_dict(payment_entity.get("notes"))
        tenant_id = tenant_id or notes.get("tenant_id")
        plan_id = plan_id or notes.get("plan_id")
        if not payment_id or not tenant_id or not plan_id:
            logger.error("Razorpay webhook missing critical fields")
            raise HTTPException(status_code=400, detail="Missing required fields")
            
    sb = get_supabase_client()
    
    # Validate plan exists and get max credits
    plan_res = sb.table("plans").select("max_credits_per_cycle").eq("id", plan_id).execute()
    if not plan_res.data:
        logger.error(f"Razorpay webhook error: Plan not found: {plan_id}")
        raise HTTPException(status_code=400, detail="Invalid plan")
    max_credits = int(plan_res.data[0].get("max_credits_per_cycle") or 0)
    
    # Idempotency check using subscription_id from notes
    sub_id = notes.get("subscription_id")
    if sub_id:
        sub_res = sb.table("subscriptions").select("id,status").eq("id", sub_id).limit(1).execute()
    else:
        sub_res = sb.table("subscriptions").select("id,status").eq("tenant_id", tenant_id).eq("status","pending").order("created_at", desc=True).limit(1).execute()

    if sub_res.data and sub_res.data[0].get("status") == "paid":
        return {"ok": True, "msg": "Already processed"}

    # Update subscription to paid
    if sub_res.data:
        sb.table("subscriptions").update({
            "status": "paid"
        }).eq("id", sub_res.data[0]["id"]).execute()
        
    now = datetime.now(timezone.utc)
    cycle_end = now + timedelta(days=365)
    now_iso = now.isoformat()
    cycle_end_iso = cycle_end.isoformat()

    # B. Update tenant_config
    sb.table("tenant_config").update({
        "subscription_status": "active",
        "subscription_ends_at": cycle_end_iso
    }).eq("tenant_id", tenant_id).execute()

    # C. Upsert tenant_plans
    # Check if a row already exists for this tenant
    existing_plan = sb.table("tenant_plans").select("id").eq("tenant_id", tenant_id).limit(1).execute()
    if existing_plan.data:
        # Update the existing row
        sb.table("tenant_plans").update({
            "plan_id": plan_id,
            "status": "active",
            "current_period_start": now_iso,
            "current_period_end": cycle_end_iso,
            "updated_at": now_iso
        }).eq("tenant_id", tenant_id).execute()
    else:
        # Insert new row
        sb.table("tenant_plans").insert({
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "status": "active",
            "current_period_start": now_iso,
            "current_period_end": cycle_end_iso
        }).execute()
        
    # D. Expire old active billing_cycles for tenant
    sb.table("billing_cycles").update({
        "status": "expired"
    }).eq("tenant_id", tenant_id).eq("status", "active").execute()
    
    # E. Create new active billing_cycle
    # Assume yearly only; billing cycle always 1 year on paid activation
    cycle_insert = sb.table("billing_cycles").insert({
        "tenant_id": tenant_id,
        "plan_id": plan_id,
        "cycle_start": now_iso,
        "cycle_end": cycle_end_iso,
        "status": "active",
        "max_credits": max_credits
    }).execute()
    
    # Insert new tenant_usage_summary row
    if cycle_insert.data:
        new_cycle_id = cycle_insert.data[0]["id"]
        sb.table("tenant_usage_summary").insert({
            "tenant_id": tenant_id,
            "billing_cycle_id": new_cycle_id,
            "credits_used_total": 0,
            "credits_used_voucher": 0,
            "credits_used_document": 0,
            "credits_used_message": 0,
            "events_count_total": 0,
            "events_count_voucher": 0,
            "events_count_document": 0,
            "events_count_message": 0
        }).execute()

    logger.info(
        "Razorpay webhook processed: event=%s tenant_id=%s plan_id=%s payment_id=%s",
        event,
        tenant_id,
        plan_id,
        payment_id,
    )
    return {"ok": True}
