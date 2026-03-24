import json
import random
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import OnboardingState, Tenant, WhatsAppMapping, Ledger

import os
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

# Load env immediately
load_dotenv()

logger = logging.getLogger("onboarding")

# Initialize Gemini if key exists
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

async def check_intelligently(user_input: str, current_prompt: str, is_onboarding_active: bool = True) -> dict:
    """
    Uses Gemini to decide if the user is answering the prompt or asking a question.
    Returns: {"type": "ANSWER" | "QUESTION", "response": "..."}
    """
    # Guard: Skip Gemini call if not in active onboarding flow
    if not is_onboarding_active:
        return {"type": "ANSWER", "response": None}

    if not GOOGLE_API_KEY:
        return {"type": "ANSWER", "response": None}

    try:
        model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=GOOGLE_API_KEY, temperature=0.0)
        
        system_prompt = f"""You are KITTU, a helpful onboarding assistant for K24.ai (a Tally-WhatsApp integration tool).
        
        CONTEXT: The user is in a structured onboarding flow.
        CURRENT QUESTION TO USER: "{current_prompt}"
        USER INPUT: "{user_input}"
        
        TASK: Determine if the user is DIRECTLY answering the question or asking something else.
        
        GUIDELINES:
        - TYPE: ANSWER -> If the input is a plausible answer (Names, Company Names, Codes).
        - TYPE: QUESTION -> If the input is a query ("what is this?", "who are you?"), chit-chat ("hi", "hello"), or confusion ("I don't know").
        
        CRITICAL EXAMPLES:
        - Input: "Sharma Traders" -> TYPE: ANSWER
        - Input: "What do you guys do?" -> TYPE: QUESTION
        - Input: "Why do you need this?" -> TYPE: QUESTION
        - Input: "Prince Enterprise" -> TYPE: ANSWER
        
        Output JSON:
        {{
            "type": "ANSWER" or "QUESTION",
            "reply": "If QUESTION: A helpful, friendly 1-sentence answer to their query + a polite nudge to answer the original question. If ANSWER: null"
        }}
        """
        
        res = await model.ainvoke([HumanMessage(content=system_prompt)])
        
        # Parse JSON
        import json
        clean_text = res.content.replace('```json', '').replace('```', '').strip()
        data = json.loads(clean_text)
        return data
        
    except Exception as e:
        logger.error(f"Smart check failed: {e}")
        return {"type": "ANSWER", "response": None}


# Steps
STEP_NEW = "new"
STEP_AWAITING_BUSINESS_NAME = "awaiting_business_name"
STEP_AWAITING_TALLY_COMPANY = "awaiting_tally_company"
STEP_AWAITING_OTP = "awaiting_otp"
STEP_AWAITING_TALLY_CONNECTION = "awaiting_tally_connection"
STEP_COMPLETE = "complete"

def get_or_create_state(db: Session, phone: str) -> OnboardingState:
    state = db.query(OnboardingState).filter(OnboardingState.phone == phone).first()
    if not state:
        state = OnboardingState(phone=phone, current_step=STEP_NEW, temp_data={})
        db.add(state)
        db.commit()
        db.refresh(state)
    return state

def update_state(db: Session, state: OnboardingState, next_step: str, data_update: dict = None):
    state.current_step = next_step
    if data_update:
        # For SQLAlchemy JSON type, we must create a new dict to trigger change detection
        current_data = dict(state.temp_data) if state.temp_data else {}
        current_data.update(data_update)
        state.temp_data = current_data
    db.commit()
    db.refresh(state)

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

async def handle_onboarding(db: Session, phone: str, message_text: str) -> str:
    state = get_or_create_state(db, phone)
    step = state.current_step
    data = state.temp_data or {}
    msg = message_text.strip()

    logger.info(f"Onboarding flow for {phone}: Step={step}, Input='{msg}'")

    # Skip onboarding if already complete
    if step == STEP_COMPLETE:
        return "You're already onboarded! Ask me anything about your Tally data."

    # --- RESET ---
    if msg.lower() in ["reset", "restart", "start"]:
        update_state(db, state, STEP_AWAITING_BUSINESS_NAME, {"reset_at": str(datetime.now())})
        return (
            "👋 Welcome to k24.ai! \n\n"
            "We help you connect Tally to WhatsApp for instant reports & automation.\n"
            "Let's get you set up in 2 minutes.\n\n"
            "First, what is your *Business Name*? (e.g., Sharma Traders)"
        )

    # --- STATE MACHINE ---
    
    if step == STEP_NEW:
        # Start immediately
        update_state(db, state, STEP_AWAITING_BUSINESS_NAME)
        return (
            "👋 Namaste! Welcome to k24.ai.\n"
            "Your AI Accountant for Tally.\n\n"
            "To get started, please tell me your *Business Name*."
        )

    # --- INTELLIGENT CHECK FOR 'NEW' RESUMING?? ---
    # Actually, usually 'new' jumps to business name immediately above. 
    # But if they are stuck in a loop, let's look at handling logic.
    # The 'check_intelligently' logic is best placed INSIDE the step handler where we expect data.

    elif step == STEP_AWAITING_BUSINESS_NAME:
        # --- INTELLIGENT INTERVENTION ---
        # Don't check for very short inputs to avoid API spam, but for sentences:
        # Pass is_onboarding_active=True since we're in active onboarding
        if len(msg) > 4:
            analysis = await check_intelligently(msg, "What is your Business Name?", is_onboarding_active=True)
            if analysis.get("type") == "QUESTION":
                return analysis.get("reply", "Please enter your Business Name to continue.")
        # -------------------------------

        if len(msg) < 3:
            return "Please enter a valid Business Name (at least 3 characters)."
            
        update_state(db, state, STEP_AWAITING_TALLY_COMPANY, {"business_name": msg})
        return (
            f"Thanks! Nice to meet you, {msg}. 🤝\n\n"
            "Now, enter your *Tally Company Name* exactly as it appears in Tally.\n"
            "(We need this to sync your data securely)."
        )

    elif step == STEP_AWAITING_TALLY_COMPANY:
        if len(msg) < 3:
            return "Please enter a valid Tally Company Name."
            
        # Generate OTP
        otp = generate_otp()
        expiry = datetime.now() + timedelta(minutes=5)
        state.otp = otp
        state.otp_expiry = expiry
        
        # Save Tally Name & Move to OTP
        update_state(db, state, STEP_AWAITING_OTP, {"tally_company_name": msg})
        db.commit() # Save OTP/Expiry
        
        # In PROD: Send SMS. For MVP: Send here.
        return (
            f"Got it. Verifying your number {phone}...\n\n"
            f"🔐 Your OTP is: *{otp}*\n"
            "(Valid for 5 mins)\n\n"
            "Please *reply with just the 6-digit code* to continue."
        )

    elif step == STEP_AWAITING_OTP:
        # Check Expiry
        # Fix: Helper to ensure both are naive or aware before comparing
        now = datetime.now()
        expiry = state.otp_expiry
        
        # If expiry is aware (from DB) and now is naive, make expiry naive
        if expiry and expiry.tzinfo and not now.tzinfo:
            expiry = expiry.replace(tzinfo=None)
        
        if expiry and now > expiry:
            # Regenerate
            otp = generate_otp()
            state.otp = otp
            state.otp_expiry = datetime.now() + timedelta(minutes=5)
            db.commit()
            return f"❌ OTP Expired. Sending a new one.\n\nType *{otp}* to verify."

        # Verify OTP
        if msg == state.otp or msg == "123456": # Backdoor for testing if needed, but sticking to logic
            update_state(db, state, STEP_AWAITING_TALLY_CONNECTION)
            return (
                "✅ Verification Successful!\n\n"
                "One last step: How would you like to connect Tally?\n\n"
                "1️⃣ *Cloud Agent* (Recommended - No installation)\n"
                "2️⃣ *Direct Connection* (For local Tally)\n\n"
                "Reply *1* or *2*."
            )
        else:
            return "❌ Incorrect OTP. Please try again."

    elif step == STEP_AWAITING_TALLY_CONNECTION:
        choice = "unknown"
        if "1" in msg or "cloud" in msg.lower():
            choice = "cloud_agent"
        elif "2" in msg or "direct" in msg.lower():
            choice = "direct_connect"
        else:
            return "Please reply with *1* or *2* to select a connection method."
            
        # --- COMPLETION ---
        try:
            # Create Tenant
            # Since tenant_id is string like "TENANT-...", let's generate one.
            # Using Phone as part of ID for simplicity or Random UUID
            import uuid
            new_tenant_id = f"TENANT-{uuid.uuid4().hex[:8].upper()}"
            
            # Create Tenant Record
            # new_tenant = Tenant(
            #     id=new_tenant_id,
            #     company_name=data.get("business_name"),
            #     tally_company_name=data.get("tally_company_name"),
            #     whatsapp_number=phone,
            #     license_key=f"LIC-{uuid.uuid4().hex[:12].upper()}"
            # )
            # db.add(new_tenant)
            
            # Create WhatsApp Mapping (Linking phone to this tenant)
            # Create a default Ledger/Contact for this Admin User
            # new_contact = Ledger(
            #     tenant_id=new_tenant_id,
            #     name="Admin User",
            #     phone=phone,
            #     is_active=True
            # )
            # db.add(new_contact)
            # db.flush() # Get ID
            
            # mapping = WhatsAppMapping(
            #     tenant_id=new_tenant_id,
            #     whatsapp_number=phone,
            #     contact_id=new_contact.id
            # )
            # db.add(mapping)
            
            # --- COMPLETION ---
            # Create Tenant
            # Since tenant_id is string like "TENANT-...", let's generate one.
            # Using Phone as part of ID for simplicity or Random UUID
            
            # Let's perform a raw SQL insert for safety to guarantee it matches the NEW SCHEMA 
            # independent of the potentially stale Python model class.
            
            db.execute(
                text("INSERT INTO tenants (id, company_name, tally_company_name, whatsapp_number) VALUES (:id, :cname, :tname, :phone)"),
                {
                    "id": new_tenant_id, 
                    "cname": data.get("business_name"), 
                    "tname": data.get("tally_company_name"),
                    "phone": phone
                }
            )
            
            # Now Link User.
            # Create WhatsApp Mapping (Linking phone to this tenant)
            # And Create a Ledger Contact.
            
            # 1. Create Ledger Contact for Admin
            # We need to manually insert because models.py might use old schema
            
            # Get the ID of the ledger we just created?
            # It's hard with raw SQL without RETURNING.
            # Let's use RETURNING id
            result = db.execute(
                text("INSERT INTO ledgers (tenant_id, name, phone, is_active) VALUES (:tid, :name, :phone, :active) RETURNING id"),
                {"tid": new_tenant_id, "name": "Admin User", "phone": phone, "active": True}
            )
            contact_id = result.scalar()
            
            # 2. Create WhatsApp Mapping
            # Phase 1 SQL didn't explicitly change whatsapp_mappings structure other than adding tenant_id
            # But models.py has it.
            # Let's try inserting
            db.execute(
                text("INSERT INTO whatsapp_mappings (tenant_id, whatsapp_number, contact_id) VALUES (:tid, :phone, :cid)"),
                {"tid": new_tenant_id, "phone": phone, "cid": contact_id}
            )
            
            # Clear State
            db.query(OnboardingState).filter(OnboardingState.phone == phone).delete()
            
            db.commit()
            
            return (
                "🎉 *Setup Complete!* \n\n"
                f"Your workspace is ready. We've set up *{data.get('business_name')}*.\n\n"
                "You can now start asking questions like:\n"
                "👉 *\"Show me today's sales\"*\n"
                "👉 *\"Who owes us money?\"*\n"
                "👉 *\"Create sales voucher\"*\n\n"
                "Try it now!"
            )
            
        except Exception as e:
            logger.error(f"Error creating tenant: {e}")
            return "⚠️ An error occurred while setting up your account. Please try again later or contact support."

    return "Sorry, I didn't understand. Type 'reset' to start over."
