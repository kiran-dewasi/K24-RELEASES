from dotenv import load_dotenv
load_dotenv()


from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body, Depends, BackgroundTasks, Security, Request
# Trigger Reload

from fastapi.responses import StreamingResponse
import os
from contextlib import asynccontextmanager
import json
import uuid

# Task 2.1: Sentry Error Monitoring (optional - may not work on Python 3.14)
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    _sentry_available = True
except Exception as _sentry_err:
    sentry_sdk = None  # type: ignore
    _sentry_available = False
    print(f"[WARNING] sentry_sdk unavailable (Python 3.14 compat issue): {_sentry_err}")

sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn and _sentry_available:
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=os.getenv("ENV", "production"),
        integrations=[FastApiIntegration(transaction_style="url")],
        traces_sample_rate=0.1,
        auto_enabling_integrations=False,  # Prevent langchain conflict
        default_integrations=False,  # Only use explicitly listed integrations
    )

from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, Iterable
import pandas as pd
from loader import LedgerLoader
from agent import TallyAuditAgent
from tally_connector import TallyConnector, get_customer_details
import crud
from tally_live_update import (
    dispatch_tally_update,
    TallyAPIError,
    TallyIgnoredError,
)
from tally_xml_builder import TallyXMLValidationError
from orchestration.workflows.update_gstin import update_gstin_workflow
from audit_engine import AuditEngine
from compliance.gst_engine import GSTEngine
import io
import logging
from fastapi.encoders import jsonable_encoder


from fastapi.security.api_key import APIKeyHeader
from dependencies import get_api_key

# Import new components
from database.repository import ChatRepository, AuditRepository, TaskRepository
# from tasks import create_ledger_async, create_voucher_async
# from celery_app import app as celery_app
from background_jobs import job_manager


# Initialize repositories
chat_repo = ChatRepository()
audit_repo = AuditRepository()
task_repo = TaskRepository()
from auth import get_current_tenant_id


from fastapi.middleware.cors import CORSMiddleware
# Explicitly import routers to avoid namespace issues
from routers import (
    reports, operations, gst, setup, debug, compliance, 
    auth, agent, sync, bills, contacts, whatsapp, baileys, whatsapp_binding,
    whatsapp_cloud, dashboard, vouchers, ledgers, search, inventory,
    customers, items, settings, query, devices
)
# Credit / Usage system routers (Phase: Usage + Admin portal)
from routers import usage as usage_router
from routers import admin as admin_router


from compliance.audit_service import AuditService
from typing import Optional

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Verify Background Job Mode
    try:
        logging.info(f"Job Manager Mode: {job_manager.mode}")
    except Exception as e:
        logging.error(f"Job Manager error: {e}")
    
    # Existing startup logic
    await startup_event()
    
    # Start Tally Sync Service
    try:
        import asyncio
        from services.tally_sync_service import start_sync_service, stop_sync_service
        asyncio.create_task(start_sync_service())
        logger.info("✅ Tally Sync Service Auto-Started")
    except Exception as e:
        logger.error(f"❌ Failed to start Tally Sync Service: {e}")

    # Start WhatsApp Poller Service
    try:
        from services.whatsapp_poller import start_whatsapp_poller
        asyncio.create_task(start_whatsapp_poller())
        logger.info("✅ WhatsApp Poller Auto-Started")
    except Exception as e:
        logger.error(f"❌ Failed to start WhatsApp Poller: {e}")
    
    yield
    
    # Shutdown
    try:
        from services.tally_sync_service import stop_sync_service
        await stop_sync_service()
        logger.info("🛑 Tally Sync Service Stopped")
    except Exception as e:
        logger.error(f"Error stopping Tally Sync Service: {e}")

    try:
        from services.whatsapp_poller import stop_whatsapp_poller
        await stop_whatsapp_poller()
        logger.info("🛑 WhatsApp Poller Stopped")
    except Exception as e:
        logger.error(f"Error stopping WhatsApp Poller: {e}")

app = FastAPI(title="K24 API", description="Financial Intelligence Engine", lifespan=lifespan)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if sentry_dsn and _sentry_available:
        sentry_sdk.capture_exception(exc)
    
    logging.error(f"Global Exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# Desktop Security Middleware (validates X-Desktop-Token in production)
# IMPORTANT: Added BEFORE CORSMiddleware so in Starlette's reverse stack order,
# CORS runs first (outermost), then security — ensuring CORS headers are ALWAYS present.
from middleware.desktop_security import DesktopSecurityMiddleware, is_desktop_mode
app.add_middleware(DesktopSecurityMiddleware)

# Enable CORS — must be added AFTER DesktopSecurityMiddleware so it wraps outside it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8001", "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

if is_desktop_mode():
    print("[SECURITY] Desktop security mode ENABLED - API protected with session token")
else:
    print("[SECURITY] Development mode - API accessible without desktop token")

from auth import check_subscription_active
protected_deps = [Depends(check_subscription_active)]

# Include Routers
app.include_router(auth.router)          # Auth first (no API key required)
app.include_router(whatsapp_binding.router, dependencies=protected_deps)  # WhatsApp Binding
app.include_router(whatsapp_cloud.router)    # ← Cloud Incoming (Baileys → Queue)

# Include Routers
app.include_router(whatsapp.router, dependencies=protected_deps)
# app.include_router(invoices.router) # Phase D: Unified Invoices - Deprecated infavor of vouchers.py
app.include_router(baileys.router) # Phase E: Baileys Integration
app.include_router(vouchers.router, prefix="/api", dependencies=protected_deps) # Phase F: Vouchers Refactor
app.include_router(ledgers.router, prefix="/api", dependencies=protected_deps) # Phase G: Ledgers Profile
app.include_router(inventory.router, prefix="/api", dependencies=protected_deps) # Phase H: Inventory
app.include_router(items.router, dependencies=protected_deps) # Phase I: Items 360° Profile (No prefix, handles own paths)
app.include_router(customers.router, prefix="/api", dependencies=protected_deps) # Phase I: Customer 360° Profile

from routers import tenant_config as tenant_config_router
app.include_router(tenant_config_router.router)

# Restoring routers preserved from previous versions
app.include_router(contacts.router, dependencies=protected_deps) 
app.include_router(reports.router, dependencies=protected_deps)
app.include_router(operations.router, dependencies=protected_deps)
app.include_router(gst.router, dependencies=protected_deps)
app.include_router(setup.router, dependencies=protected_deps)
app.include_router(debug.router, dependencies=protected_deps)
app.include_router(compliance.router, prefix="/api", dependencies=protected_deps)
app.include_router(sync.router, dependencies=protected_deps)
app.include_router(bills.router, dependencies=protected_deps)
app.include_router(dashboard.router, prefix="/api", dependencies=protected_deps)
app.include_router(search.router, prefix="/api", dependencies=protected_deps)
app.include_router(settings.router, dependencies=protected_deps) # Phase ?: User Settings
app.include_router(agent.router, dependencies=protected_deps) # Ensure agent router is here too if not duplicate
app.include_router(query.router, prefix="/api", dependencies=protected_deps) # Day 5: Smart Query API
app.include_router(devices.router, prefix="/api/devices", dependencies=protected_deps) # Licensing
# ── Credit & Usage system ─────────────────────────────────────────────────
app.include_router(usage_router.router)   # POST /internal/usage/event
app.include_router(admin_router.router)   # GET  /admin/tenants etc.
# ── Public subscription (UPI payment flow) ────────────────────────────────
from routers import subscribe as subscribe_router
app.include_router(subscribe_router.router)  # POST /public/subscribe/intent etc.
# Auth router is already included at line 83
# Global simulated in-memory dataframe (single-user MVP)
# Global simulated in-memory dataframe (single-user MVP)
dataframe = None

import sys
import io

# Fix for Windows Console Unicode Error (CP1252 vs emojis)
if sys.platform.startswith("win"):
    # Reconfigure stdout/stderr to use utf-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # For older python versions or weird environments
        pass

def get_user_data_dir():
    """Get safe user writable directory for creating files"""
    if getattr(sys, "frozen", False):
         base_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "k24")
         os.makedirs(base_dir, exist_ok=True)
         return base_dir
    return "."

USER_DATA_DIR = get_user_data_dir()
DATA_LOG_PATH = os.path.join(USER_DATA_DIR, "data_log.pkl")
CONFIG_PATH = os.path.join(USER_DATA_DIR, "k24_config.json")

TALLY_COMPANY = os.getenv("TALLY_COMPANY", "Krishasales")
TALLY_URL = os.getenv("TALLY_URL", "http://localhost:9000")
LIVE_SYNC = bool(os.getenv("TALLY_LIVE_SYNC", ""))
# Safety flag for live Tally updates - set to "true" to enable actual sync to Tally
TALLY_LIVE_UPDATE_ENABLED = os.getenv("TALLY_LIVE_UPDATE_ENABLED", "true").lower() == "true"
print(f"[INFO] TALLY LIVE UPDATE ENABLED: {TALLY_LIVE_UPDATE_ENABLED}")

# Load Config from JSON (Overrides env vars)
import json
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Check both local (for easy dev config) and user directory
paths_to_check = ["k24_config.json", CONFIG_PATH]
for path in paths_to_check:
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                config = json.load(f)
                GOOGLE_API_KEY = config.get("google_api_key", GOOGLE_API_KEY)
                TALLY_COMPANY = config.get("company_name", TALLY_COMPANY)
                TALLY_URL = config.get("tally_url", TALLY_URL)
                print(f"[CONFIG] Loaded config from {path}")
                break
        except:
            pass

# Initialize Tally Connector
tally = TallyConnector(url=TALLY_URL, company_name=TALLY_COMPANY)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tally_api")
from orchestrator import K24Orchestrator
from database import init_db, get_db, Ledger, StockItem, Bill, Voucher
from sqlalchemy.orm import Session
from orchestration.response_builder import ResponseBuilder, ResponseType
from orchestration.follow_up_manager import FollowUpManager
from sync.sync_monitor import monitor as sync_monitor

# Initialize Orchestrator
orchestrator = None
# Lazy init — created on first /chat request only
@app.get("/audit/run", dependencies=[Depends(get_api_key), Depends(check_subscription_active)])
def run_pre_audit():
    """
    Run Pre-Audit Compliance Check (Section 44AB)
    Returns a comprehensive audit report with issues and recommendations
    """
    try:
        # Use the global 'tally' instance
        audit_engine = AuditEngine(tally)
        report = audit_engine.run_full_audit()
        return report
    except Exception as e:
        logger.error(f"Audit Engine Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Global Sync Instance
from sync_engine import SyncEngine # Assuming SyncEngine is a class
sync_engine = SyncEngine()
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from datetime import datetime
from typing import List

# Initialize Shadow DB
init_db()
print("DEBUG: Database Tables Checked/Created.")

# Global Orchestrator instance (lazy initialization)
orchestrator = None

# Global FollowUpManager for conversation state
follow_up_mgr = FollowUpManager()


# startup_event is now called by lifespan
async def startup_event():
    global orchestrator
    # Orchestrator initialization is now lazy - will be created on first use
    # This reduces startup API calls to Gemini
    

    # Initialize AI Agent Orchestrator
    try:
        # Load API Key from DB (User Settings) if available
        # This allows BYOK (Bring Your Own Key) feature
        from services.key_manager import get_google_api_key
        # We try to get key for default user or just general find
        try:
            # Load key for default_user (Migration target)
            key = get_google_api_key("default_user")
            if key:
                os.environ["GOOGLE_API_KEY"] = key
                print(f"[STARTUP] Loaded encrypted API key for default_user")
            else:
                 print(f"[STARTUP] No API key found for default_user")
        except Exception as e:
            logger.warning(f"Failed to load user API key at startup: {e}")

        # Verify License (Task 1.4)
        # This prevents unauthorized copying of the application
        try:
            from services.license_service import license_service
            status = license_service.validate_license()
            if not status["valid"]:
                logger.error(f"LICENSE ERROR: {status['reason']}")
                # Allow startup for now but log critical error, in prod we would exit
                # sys.exit(1)
            else:
                logger.info(f"License Verified: {status.get('plan')} (Expires: {status.get('expires_at')})")
        except Exception as e:
            logger.error(f"License check failed: {e}")

        # Capture Main Loop for Socket Manager Thread-Safety
        import asyncio
        loop = asyncio.get_running_loop()
        from socket_manager import socket_manager
        socket_manager.set_main_loop(loop)
        
        agent.init_orchestrator()
        
        # Load Initial Data for AI Brain
        initial_df = _load_initial_data()
        if initial_df is not None and not initial_df.empty:
            global dataframe
            dataframe = initial_df
            checkpoint(dataframe)
            logger.info(f"[INFO] Loaded K24 Brain with {len(dataframe)} rows of cached data.")
        else:
            logger.warning("[WARNING] No cached Tally data found. AI Brain starts empty.")
        
        # Initialize LangGraph Persistence 
        from memory import get_database_url
        # from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from langgraph.checkpoint.memory import MemorySaver
        
        db_url = get_database_url()
        if db_url.startswith("sqlite"):
            logger.info("[INFO] Using In-Memory Checkpointer (SQLite detected)")
            from langgraph.checkpoint.memory import MemorySaver
            # Initialize with MemorySaver if needed by your agent OR just skip
            # For now, we allow the agent to manage its own memory primarily
            pass
        else:
             # Only try Postgres if not sqlite
             try:
                 from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
                 async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:
                    await checkpointer.setup()
             except ImportError:
                 logger.warning("Postgres support not installed. Skipping.")
            
        logger.info("[SUCCESS] AI Agent orchestrator & persistence initialized")
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize AI Agent: {e}")

def checkpoint(df):
    crud.log_change(df, DATA_LOG_PATH)

def _load_initial_data():
    import os
    import pickle
    # Try from pkl, then XML
    if os.path.exists(DATA_LOG_PATH):
        try:
            with open(DATA_LOG_PATH, 'rb') as f:
                last_df = None
                while True:
                    try:
                        last_df = pickle.load(f)
                    except EOFError:
                        break
                if last_df is not None and not last_df.empty:
                    return last_df
        except Exception as ex:
            logger.warning(f"Could not load dataframe from {DATA_LOG_PATH}: {ex}")
    # Fallback: try to parse sample_tally.xml
    if os.path.exists('sample_tally.xml'):
        try:
            with open('sample_tally.xml', 'r', encoding='utf-8') as f:
                xml_text = f.read()
            df_ledgers = TallyConnector._parse_ledger_xml(xml_text)
            if not df_ledgers.empty:
                return df_ledgers
        except Exception as ex:
            logger.warning(f"Could not load from sample_tally.xml: {ex}")
    return None

def _ensure_dataframe():
    global dataframe
    if dataframe is None or dataframe.empty:
        logger.warning("No live data available yet. Please try your query again after Tally data is fetched.")
        return pd.DataFrame()  # Return empty instead of raising error
    return dataframe

def _normalize_update_keys(df, updates):
    # Maps keys to their DataFrame counterparts (case-insensitive)
    col_map = {col.lower(): col for col in df.columns}
    normalized = {}
    invalids = []
    for k, v in updates.items():
        keynorm = col_map.get(k.lower())
        if keynorm:
            normalized[keynorm] = v
        else:
            invalids.append(k)
    return normalized, invalids

class AuditRequest(BaseModel):
    question: str
    # Optionally allow text fields for CSV content or path

class ModifyRequest(BaseModel):
    action: str  # 'add' | 'update' | 'delete'
    data: Dict[str, Any]
    idx: Optional[int] = None  # For update/delete
    live_sync: Optional[bool] = False  # If True, always push change to Tally

# ----------------------- New Routes (minimal additions) -----------------------
class ImportXMLRequest(BaseModel):
    xml_input: str

@app.post("/import-tally/", dependencies=[Depends(get_api_key), Depends(check_subscription_active)])
def import_tally(req: ImportXMLRequest):
    global dataframe
    xml_text = req.xml_input
    # Try parsing as ledgers first
    df_ledgers = TallyConnector._parse_ledger_xml(xml_text)
    if not df_ledgers.empty:
        dataframe = df_ledgers
        rows = jsonable_encoder(df_ledgers.to_dict(orient="records"))
        return {"status": "ok", "type": "ledger", "rows": rows}
    # Try parsing as vouchers
    df_vouchers = TallyConnector._parse_voucher_xml(xml_text)
    if not df_vouchers.empty:
        rows = jsonable_encoder(df_vouchers.to_dict(orient="records"))
        return {"status": "ok", "type": "voucher", "rows": rows}
    # Unknown/empty
    return {"status": "ok", "type": "unknown", "rows": []}

class AgentQuery(BaseModel):
    query: str

@app.post("/ask-agent/", dependencies=[Depends(get_api_key), Depends(check_subscription_active)])
def ask_agent(request: AgentQuery):
    try:
        df = _ensure_dataframe()
        # API key retrieval and agent init is now handled safely by get_gemini_llm
        agent = TallyAuditAgent()
        result = agent.ask_audit_question(df, request.query)
        return {"result": result}
    except ValueError as e:
        logger.warning(f"AI Feature Unavailable: {e}")
        raise HTTPException(status_code=503, detail="AI features unavailable: Google API Key not configured.")
    except Exception as e:
        logger.error(f"Agent Error: {e}")
        raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")

class CustomerDetailsRequest(BaseModel):
    name: str

@app.post("/customer-details/", dependencies=[Depends(get_api_key), Depends(check_subscription_active)])
def customer_details(req: CustomerDetailsRequest):
    df = _ensure_dataframe()
    details = get_customer_details(df, req.name)
    return {"status": "ok", "name": req.name, "details": jsonable_encoder(details)}

# Endpoint moved to backend/routers/vouchers.py

# Endpoint moved to backend/routers/vouchers.py

@app.get("/api/reports/outstanding", dependencies=[Depends(get_api_key), Depends(check_subscription_active)])
async def get_outstanding_bills():
    """Fetch outstanding bills"""
    try:
        df = tally.fetch_outstanding_bills()
        if df.empty:
            return {"bills": []}
        return {"bills": df.to_dict(orient="records")}
    except Exception as e:
        logger.exception("Failed to fetch outstanding bills")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ledgers/search", dependencies=[Depends(get_api_key), Depends(check_subscription_active)])
async def search_ledgers(query: str):
    """Search ledgers for autocomplete"""
    try:
        matches = tally.lookup_ledger(query)
        return {"matches": matches}
    except Exception as e:
        logger.exception(f"Failed to search ledgers for '{query}'")
        raise HTTPException(status_code=500, detail=str(e))



# --------------------- End New Routes (minimal additions) ---------------------

# ----------------------- Tally Health Check -----------------------
@app.get("/api/health/tally")
def tally_health_check():
    """
    Check if Tally is reachable at the configured URL via XML POST.
    Returns status and timestamp.
    """
    tally_url = os.getenv("TALLY_URL", "http://localhost:9000")
    try:
        # Minimal XML to check if Tally is listening/open
        payload = "<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Companies</REPORTNAME></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"
        
        import requests
        # Must be POST
        response = requests.post(tally_url, data=payload, timeout=2)
        
        is_active = response.status_code == 200 and ("RESPONSE" in response.text or "List of Companies" in response.text)
        
        if is_active:
            return {
                "status": "online",
                "tally_running": True,
                "mode": "active",
                "url": tally_url,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "online",
                "tally_running": True,
                "mode": "idle (web server up, but invalid XML response)",
                "url": tally_url,
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.warning(f"Tally Health Check Failed: {e}")
        return {
            "status": "offline",
            "tally_running": False,
            "url": tally_url,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/health")
def health_check():
    """Health check endpoint for container/orchestrator - Updated"""
    from services.supabase_service import supabase_http_service
    supabase_status = "connected" if supabase_http_service.client else "disabled"
    return {"status": "ok", "supabase": supabase_status, "k24": "running"}

@app.post("/audit", dependencies=[Depends(get_api_key), Depends(check_subscription_active)])
def audit_entry(request: AuditRequest):
    try:
        df = _ensure_dataframe()
        agent = TallyAuditAgent()
        result = agent.ask_audit_question(df, request.question)
        return {"result": result}
    except ValueError as e:
        logger.warning(f"AI Feature Unavailable: {e}")
        raise HTTPException(status_code=503, detail="AI features unavailable: Google API Key not configured.")
    except Exception as e:
        logger.error(f"Audit Error: {e}")
        raise HTTPException(status_code=500, detail=f"Audit Error: {str(e)}")

# ----------------------- NEW CHAT & AUDIT ENDPOINTS -----------------------

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    user_id: str = "default_user"
    confirmation: bool = False

@app.post("/api/chat")
async def chat_with_memory(request: ChatRequest, tenant_id: str = Depends(get_current_tenant_id), _sub = Depends(check_subscription_active)):
    """
    Chat endpoint WITH MEMORY.
    
    Flow:
    1. Load previous messages from database (MEMORY!)
    2. Convert to LangChain format
    3. Add current user message
    4. Save user message to database
    5. Call agent with FULL CONVERSATION HISTORY
    6. Save agent response to database
    7. Stream back to frontend
    
    KEY: Agent sees entire conversation, not just current message!
    """

    # Generate thread ID if first message
    thread_id = request.thread_id or str(uuid.uuid4())
    
    # Ensure thread exists in DB (fix for FK violation)
    await chat_repo.create_thread(thread_id, request.user_id)

    from credit_engine.engine import check_credits_available
    from fastapi import HTTPException
    if not check_credits_available(tenant_id, "MESSAGE"):
        raise HTTPException(status_code=402, detail="Credit limit reached")

    print(f"\n{'='*70}")
    print(f"📨 CHAT REQUEST")
    print(f"   Thread: {thread_id}")
    print(f"   User: {request.user_id}")
    print(f"   Message: {request.message[:80]}...")
    print(f"{'='*70}")

    async def event_generator():
        import time
        t0 = time.time()
        try:
            # ====================================================================
            # STEP 1: LOAD PREVIOUS MESSAGES (THIS IS THE MEMORY!)
            # ====================================================================
            print(f"\n📚 LOADING CONVERSATION HISTORY...")
            
            previous_messages_raw = await chat_repo.get_thread_history(
                thread_id, 
                limit=100
            )
            
            print(f"   Found {len(previous_messages_raw)} previous messages")
            
            # Convert to LangChain message format
            from langchain_core.messages import HumanMessage, AIMessage
            from datetime import datetime
            messages = []
            
            for msg in previous_messages_raw:
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['message_content']))
                    print(f"   ✓ Loaded user message: {msg['content'][:60]}...")
                else:
                    messages.append(AIMessage(content=msg['message_content']))
                    print(f"   ✓ Loaded agent response: {msg['content'][:60]}...")
            
            # Add current user message with DATE CONTEXT
            # This helps KITTU understand "today", "yesterday", "this month" etc.
            now = datetime.now()
            date_context = f"\n\n[Context: Today is {now.strftime('%B %d, %Y')} ({now.strftime('%Y%m%d')})]"
            enhanced_message = request.message + date_context
            
            messages.append(HumanMessage(content=enhanced_message))
            print(f"\n   Total messages agent will see: {len(messages)}")
            
            print(f"[PERF] History loaded: {time.time()-t0:.2f}s")
            
            # Stream: Status update
            yield f"data: {json.dumps({'type': 'status', 'content': f'Processing with {len(messages)} messages in context...', 'thread_id': thread_id, 'context_size': len(messages)})}\n\n"
            
            # ====================================================================
            # STEP 2: SAVE USER MESSAGE TO DATABASE
            # ====================================================================
            print(f"\n💾 SAVING USER MESSAGE...")
            
            user_msg = await chat_repo.save_message(
                thread_id=thread_id,
                role="user",
                content=request.message,
                source="ui",
                user_id=request.user_id,
                tenant_id=tenant_id
            )
            print(f"[SAVE] User msg saved: {user_msg}, tenant: {tenant_id}")

            user_msg_id = user_msg.get('id') if user_msg else "temp_id"
            print(f"   ✓ Saved with ID: {user_msg_id}")
            
            print(f"[PERF] User msg saved: {time.time()-t0:.2f}s")
            
            # ====================================================================
            # STEP 3: CALL AGENT WITH FULL MESSAGE HISTORY
            # ====================================================================
            print(f"\n🤖 CALLING AGENT WITH MEMORY...")
            print(f"   Agent will process {len(messages)} messages")
            
            # Import your existing agent
            # We import here to ensure we get the latest if module reloading is trippy, 
            # though standard import is cached. 
            from agent import agent as memory_agent
            
            response_text = ""
            agent_msg_id = ""
            
            if not memory_agent:
                response_text = "Error: Agent not initialized properly (GOOGLE_API_KEY missing?)"
            else:
                try:
                    # CRITICAL: Pass the full message history!
                    # For ToolCallingAgent, 'chat_history' usually goes into 'messages' placeholder if defined.
                    # Or 'chat_history' variable if that's what placeholder uses.
                    # Our prompt uses "messages" placeholder.
                    
                    # We pass the input as "messages" because in a MessagesPlaceholder, 
                    # replacing it means the input dict key matches the variable_name.
                    # HOWEVER, standard AgentExecutor expect 'input' or 'chat_history'?
                    # If we use `create_tool_calling_agent`, the prompt usually expects `chat_history`.
                    # Our prompt has `MessagesPlaceholder(variable_name="messages")`.
                    # So passing `{"messages": <list>}` should work if the PromptTemplate supports it.
                    # But the 'system' message is fixed. 
                    # If we pass just 'messages', we might overwrite everything?
                    # Let's verify prompt structure in agent.py
                    # prompt = ChatPromptTemplate.from_messages([ ("system", ...), MessagesPlaceholder("messages"), ...])
                    # So we pass "messages" -> This fills the middle.
                    # Does user input go into "messages" or is it separate?
                    # Usually: system + chat_history + user_input + agent_scratchpad
                    # Our logic passes ALL messages (history + current) into "messages".
                    # This implies "messages" covers the whole conversation.
                    
                    agent_response = await memory_agent.ainvoke({
                        "messages": messages,  # Full conversation history!
                        "thread_id": thread_id,
                        "user_id": request.user_id
                    })
                    
                    # Extract response text
                    if isinstance(agent_response, dict) and 'output' in agent_response:
                        response_text = agent_response['output']
                    elif isinstance(agent_response, dict) and 'messages' in agent_response:
                        # If agent returns intermediate messages
                        response_text = str(agent_response['messages'][-1].content)
                    else:
                        response_text = str(agent_response)
                    
                    print(f"   ✓ Agent response: {response_text[:80]}...")
                    
                except Exception as agent_error:
                    print(f"   ✗ Agent error: {agent_error}")
                    response_text = f"Error processing request: {str(agent_error)}"
            
            print(f"[PERF] Agent responded: {time.time()-t0:.2f}s")
            
            # Stream: Agent response in progress
            yield f"data: {json.dumps({'type': 'status', 'content': 'Agent processed. Saving response...', 'thread_id': thread_id})}\n\n"
            
            # ====================================================================
            # STEP 4: SAVE AGENT RESPONSE TO DATABASE
            # ====================================================================
            print(f"\n💾 SAVING AGENT RESPONSE...")
            
            agent_msg = await chat_repo.save_message(
                thread_id=thread_id,
                role="assistant",
                content=response_text,
                source="ui",
                user_id="agent",
                tenant_id=tenant_id
            )
            print(f"[SAVE] Agent msg saved: {agent_msg}, tenant: {tenant_id}")

            agent_msg_id = agent_msg.get('id') if agent_msg else "temp_id"
            print(f"   ✓ Saved with ID: {agent_msg_id}")
            
            print(f"[PERF] Agent msg saved: {time.time()-t0:.2f}s")
            
            # ====================================================================
            # STEP 5: STREAM RESPONSE TO FRONTEND
            # ====================================================================
            print(f"\n📤 STREAMING RESPONSE TO FRONTEND...")
            
            yield f"data: {json.dumps({'type': 'response', 'content': response_text, 'message_id': agent_msg_id, 'thread_id': thread_id})}\n\n"
            
            from credit_engine import record_event
            record_event(
                tenant_id=tenant_id,
                event_type="MESSAGE",
                event_subtype="action"
            )
            
            # Stream: Complete
            yield f"data: {json.dumps({'type': 'complete', 'thread_id': thread_id, 'user_message_id': user_msg_id, 'agent_message_id': agent_msg_id, 'total_messages': len(messages) + 1})}\n\n"
            
            print(f"\n{'='*70}")
            print(f"✓ CHAT COMPLETE")
            print(f"   User message ID: {user_msg_id}")
            print(f"   Agent message ID: {agent_msg_id}")
            print(f"   Total in thread: {len(messages) + 1}")
            print(f"{'='*70}\n")
            
        except Exception as e:
            print(f"\n✗ FATAL ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            
            yield f"data: {json.dumps({'type': 'error', 'content': str(e), 'thread_id': thread_id})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/chat/{thread_id}/history")
async def get_chat_history(thread_id: str):
    """
    Get full chat history for a thread.
    Returns all messages in chronological order.
    """
    try:
        history = await chat_repo.get_thread_history(thread_id, limit=100)
        count = await chat_repo.count_messages(thread_id)
        
        return {
            "status": "success",
            "thread_id": thread_id,
            "messages": history,
            "count": count
        }
    
    except Exception as e:
        print(f"✗ Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audit/{record_id}")
async def get_audit_trail(record_id: str):
    """Get audit trail for a record"""
    trail = await audit_repo.get_audit_trail("ledgers", record_id) # Defaulting to ledgers for now
    return {"status": "success", "audit_trail": trail}

@app.get("/api/task/{task_id}/progress")
async def get_task_progress(task_id: str):
    """Get real-time task progress"""
    progress = await task_repo.get_task_progress(task_id)
    return {"status": "success", "progress": progress}

    """
    Extract ledger name from dataframe row.
    Tries common column names: NAME, LEDGERNAME, LEDGER_NAME, PARTYNAME, etc.
    """
    if idx < 0 or idx >= len(df):
        return None
    
    row = df.iloc[idx]
    # Try common name column variations
    name_columns = ['NAME', 'LEDGERNAME', 'LEDGER_NAME', 'PARTYNAME', 'PARTY_NAME', 'COMPANY_NAME']
    for col in name_columns:
        if col in df.columns:
            name = row.get(col)
            if pd.notna(name) and name:
                return str(name)
    # Fallback: try to find any column containing 'name' (case-insensitive)
    for col in df.columns:
        if 'name' in str(col).lower() and pd.notna(row.get(col)) and row.get(col):
            return str(row.get(col))
    return None


def _sync_to_tally_live(company_name: str, ledger_name: Optional[str], updates: Dict[str, Any],
                        action: str, tally_url: str, entity_type: str = "ledger",
                        line_items: Optional[Iterable[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Sync changes to Tally using live update API.
    Only performs sync if TALLY_LIVE_UPDATE_ENABLED is True.
    Returns dict with sync status and any errors.
    """
    if not TALLY_LIVE_UPDATE_ENABLED:
        logger.info(f"Tally live update is disabled (dry-run mode). Would sync: {action} for ledger '{ledger_name}' with updates: {updates}")
        return {"status": "skipped", "reason": "dry_run_mode", "message": "Tally live update is disabled"}
    
    if entity_type == "ledger" and not ledger_name:
        raise HTTPException(status_code=400, detail="Ledger name not found")
    
    if entity_type == "ledger" and (not updates or action == 'delete'):
        # Skip sync for delete actions or if no updates
        logger.info(f"Skipping Tally sync for {action} action (no updates to sync)")
        return {"status": "skipped", "reason": "no_updates", "message": f"No updates to sync for {action} action"}
    
    try:
        logger.info(
            "Syncing %s change to Tally: company='%s', ledger='%s', entity='%s', updates=%s",
            action,
            company_name,
            ledger_name,
            entity_type,
            updates,
        )
        if entity_type == "ledger":
            payload = {"ledger_name": ledger_name, "fields": updates}
        else:
            payload = {
                "action": action,
                "voucher": updates,
                "line_items": line_items or [],
            }
        response = dispatch_tally_update(
            entity_type=entity_type,
            company_name=company_name,
            payload=payload,
            tally_url=tally_url,
            timeout=15,
        )
        logger.info(
            "Successfully synced %s to Tally (entity=%s, ledger='%s')",
            action,
            entity_type,
            ledger_name,
        )
        return {"status": "success", "response": response.to_dict()}
    except TallyIgnoredError as exc:
        logger.warning(
            "Tally ignored %s update for ledger '%s': %s",
            action,
            ledger_name,
            exc,
        )
        response = getattr(exc, "response", None)
        return {
            "status": "ignored",
            "reason": "tally_ignored",
            "message": str(exc),
            "response": response.to_dict() if response else None,
        }
    except (TallyAPIError, TallyXMLValidationError) as exc:
        logger.error(
            "Failed to sync %s to Tally for ledger '%s': %s",
            action,
            ledger_name,
            exc,
        )
        response = getattr(exc, "response", None)
        raise HTTPException(status_code=400, detail=str(exc))
    except TallyXMLValidationError as exc:
        # If exc.args[0] is a dict (from revised _sanitize_ledger_fields), return as detail
        if exc.args and isinstance(exc.args[0], dict):
            raise HTTPException(status_code=400, detail=exc.args[0])
        else:
            raise HTTPException(status_code=400, detail={"status": "error", "message": str(exc)})
    except Exception as exc:
        logger.exception("Unexpected error during Tally sync")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/modify", dependencies=[Depends(get_api_key)])
def modify_entry(request: ModifyRequest):
    df = _ensure_dataframe()
    checkpoint(df)
    sync_result = None
    try:
        use_live = request.live_sync or LIVE_SYNC
        tc = TallyConnector(TALLY_URL) if use_live else None
        company = TALLY_COMPANY if use_live else None
        # Use enhanced CRUD when live sync is requested
        id_col = "ID" if "ID" in df.columns else df.columns[0]
        crud_obj = crud.LedgerCRUD(df, id_col=id_col, tally_connector=tc, company_name=company) if use_live else None
        
        if request.action == 'add':
            if use_live:
                crud_obj.add_entry(request.data)
                df = crud_obj.df
            else:
                df = crud.add_entry(df, request.data)
            
            # Sync to Tally after successful add
            if TALLY_LIVE_UPDATE_ENABLED or request.live_sync:
                ledger_name = request.data.get('NAME') or request.data.get('LEDGERNAME') or request.data.get('PARTYNAME')
                if ledger_name:
                    updates = {k: v for k, v in request.data.items() if k not in ['ID', 'NAME', 'LEDGERNAME', 'PARTYNAME']}
                    sync_result = _sync_to_tally_live(
                        company_name=TALLY_COMPANY,
                        ledger_name=ledger_name,
                        updates=updates if updates else request.data,
                        action='add',
                        tally_url=TALLY_URL
                    )
                
        elif request.action == 'update':
            ledger_name = None
            if use_live:
                entry_id = request.data.get("ID")
                if entry_id is None:
                    raise HTTPException(status_code=400, detail="Must supply ID for updates in live mode.")
                try:
                    crud_obj.update_entry(entry_id, request.data)
                except Exception as ee:
                    raise HTTPException(status_code=400, detail=str(ee))
                df = crud_obj.df
                # Get ledger name from updated row
                updated_row = df[df[id_col] == entry_id]
                if not updated_row.empty:
                    ledger_name = _get_ledger_name_from_dataframe(df, updated_row.index[0], id_col)
            else:
                if request.idx is None:
                    raise HTTPException(status_code=400, detail="Must supply idx for updates in non-live mode.")
                if request.idx < 0 or request.idx >= len(df):
                    raise HTTPException(status_code=400, detail=f"Index {request.idx} is out of bounds. DataFrame has {len(df)} rows.")
                try:
                    df = crud.update_entry(df, request.idx, request.data)
                except Exception as ee:
                    raise HTTPException(status_code=400, detail=str(ee))
                # Get ledger name from updated row
                ledger_name = _get_ledger_name_from_dataframe(df, request.idx, id_col)
            
            # Sync to Tally after successful update
            if TALLY_LIVE_UPDATE_ENABLED or request.live_sync:
                sync_result = _sync_to_tally_live(
                    company_name=TALLY_COMPANY,
                    ledger_name=ledger_name,
                    updates=request.data,
                    action='update',
                    tally_url=TALLY_URL
                )
                
        elif request.action == 'delete':
            if use_live:
                entry_id = request.data.get("ID")
                if entry_id is None:
                    raise HTTPException(status_code=400, detail="Must supply ID for delete in live mode.")
                # Get ledger name before deletion
                row_to_delete = df[df[id_col] == entry_id]
                ledger_name = None
                if not row_to_delete.empty:
                    ledger_name = _get_ledger_name_from_dataframe(df, row_to_delete.index[0], id_col)
                try:
                    crud_obj.delete_entry(entry_id)
                except Exception as ee:
                    raise HTTPException(status_code=400, detail=str(ee))
                df = crud_obj.df
            else:
                if request.idx is None:
                    raise HTTPException(status_code=400, detail="Must supply idx for delete in non-live mode.")
                if request.idx < 0 or request.idx >= len(df):
                    raise HTTPException(status_code=400, detail=f"Index {request.idx} is out of bounds. DataFrame has {len(df)} rows.")
                # Get ledger name before deletion
                ledger_name = _get_ledger_name_from_dataframe(df, request.idx, id_col)
                try:
                    df = crud.delete_entry(df, request.idx)
                except Exception as ee:
                    raise HTTPException(status_code=400, detail=str(ee))
            
            # Note: We typically don't sync deletes to Tally, but log it
            if TALLY_LIVE_UPDATE_ENABLED or request.live_sync:
                logger.info(f"Delete action for ledger '{ledger_name}' - Tally sync skipped for delete operations")
                sync_result = {"status": "skipped", "reason": "delete_action", "message": "Delete operations are not synced to Tally"}
        else:
            raise HTTPException(status_code=400, detail="Unknown action")
        
        response = {"status": "success"}
        if sync_result:
            response["tally_sync"] = sync_result
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in modify_entry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/load", dependencies=[Depends(get_api_key)])
def load_ledger(file: UploadFile = File(...), filetype: str = Form("csv")):
    global dataframe
    content = file.file.read()
    if filetype == "csv":
        df = pd.read_csv(io.BytesIO(content))
    elif filetype == "xlsx":
        df = pd.read_excel(io.BytesIO(content))
    else:
        raise HTTPException(status_code=400, detail="Invalid filetype.")
    dataframe = df
    checkpoint(df)
    return {"status": "loaded", "shape": df.shape}

@app.post("/live_load", dependencies=[Depends(get_api_key)])
def live_load(company: Optional[str] = Form(None), load_type: str = Form("ledger")):
    """Load ledgers or vouchers live from Tally, fallback to CSV if error."""
    global dataframe
    comp = company or TALLY_COMPANY
    if load_type == "ledger":
        df = LedgerLoader.load_tally_ledgers(comp, tally_url=TALLY_URL)
        if df is None:
            raise HTTPException(status_code=500, detail="Failed to load ledgers from Tally.")
    elif load_type == "voucher":
        df = LedgerLoader.load_tally_vouchers(comp, tally_url=TALLY_URL)
        if df is None:
            raise HTTPException(status_code=500, detail="Failed to load vouchers from Tally.")
    else:
        raise HTTPException(status_code=400, detail="Invalid load_type.")
    dataframe = df
    checkpoint(df)
    return {"status": "loaded", "shape": df.shape, "source": "tally"}

@app.post("/tally/push", dependencies=[Depends(get_api_key)])
async def push_tally(xml_data: str = Body(..., embed=True)):
    from tally_connector import push_to_tally
    result = push_to_tally(xml_data)
    if result is None:
        return {"status": "error", "detail": "Tally push failed"}
    return {"status": "success", "response": result}

# ============================================================================
# WORKFLOW ORCHESTRATION ENDPOINTS
# ============================================================================

class WorkflowRequest(BaseModel):
    workflow_name: str
    party_name: str
    company: Optional[str] = "SHREE JI SALES"
    auto_approve: Optional[bool] = False

@app.post("/workflows/execute", dependencies=[Depends(get_api_key)])
async def execute_workflow(request: WorkflowRequest):
    """
    Execute a KITTU workflow
    
    Currently supports:
    - invoice_reconciliation: Detect and fix invoice discrepancies
    """
    from orchestration.workflows.invoice_reconciliation import reconcile_invoices_workflow
    
    if request.workflow_name == "invoice_reconciliation":
        try:
            result = reconcile_invoices_workflow(
                party_name=request.party_name,
                company=request.company,
                tally_url=TALLY_URL,
                auto_approve=request.auto_approve
            )
            return result
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")
    else:
        raise HTTPException(status_code=404, detail=f"Workflow '{request.workflow_name}' not found")

@app.get("/workflows/list", dependencies=[Depends(get_api_key)])
async def list_workflows():
    """List available workflows"""
    return {
        "workflows": [
            {
                "name": "invoice_reconciliation",
                "description": "Detect and fix invoice discrepancies for a party",
                "parameters": {
                    "party_name": "string (required)",
                    "company": "string (optional, default: SHREE JI SALES)",
                    "auto_approve": "boolean (optional, default: false)"
                }
            }
        ]
    }

# ============================================================================
# CONVERSATIONAL AI ENDPOINTS (KITTU)
# ============================================================================

from context_manager import ContextManager
from intent_recognizer import IntentRecognizer, IntentType

# Initialize components
# Use fallback if Redis is not available
context_mgr = ContextManager(use_fallback=True)
intent_recognizer = None

def get_intent_recognizer():
    """Lazy initialization of IntentRecognizer"""
    global intent_recognizer
    if intent_recognizer is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set, IntentRecognizer will fail")
            return None
        intent_recognizer = IntentRecognizer(api_key=api_key)
    return intent_recognizer

@app.get("/sync/status", dependencies=[Depends(get_api_key)])
def get_sync_status():
    """Get current sync health status"""
    return sync_monitor.get_health_report()

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default_user"
    company: Optional[str] = None # Allow user to specify company for chat
    client_context: Optional[Dict[str, Any]] = None # Context from frontend (e.g. current page)
    active_draft: Optional[Dict[str, Any]] = None

@app.post("/chat", dependencies=[Depends(get_api_key)])
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint for KITTU.
    Delegates to the K24Orchestrator ("The Director").
    """
    try:
        # Lazy initialization of orchestrator on first use
        global orchestrator
        if orchestrator is None:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")
            orchestrator = K24Orchestrator(api_key=api_key)
            logger.info("Orchestrator initialized lazily on first request")

        # Pass request to the Director
        response_data = await orchestrator.process_message(
            user_id=request.user_id,
            message=request.message,
            active_draft=request.active_draft
        )

        return response_data

    except Exception as e:
        logger.exception("Chat processing failed")
        raise HTTPException(status_code=500, detail=str(e))

# --- Headless Tally Endpoints (Shadow DB) ---

@app.get("/ledgers", dependencies=[Depends(get_api_key)])
def get_ledgers(db: Session = Depends(get_db), tenant_id: str = Depends(get_current_tenant_id)):
    """Get all ledgers from Shadow DB (Instant)"""
    return db.query(Ledger).filter(Ledger.tenant_id == tenant_id).all()

@app.get("/items", dependencies=[Depends(get_api_key)])
def get_items(db: Session = Depends(get_db), tenant_id: str = Depends(get_current_tenant_id)):
    """Get all stock items from Shadow DB (Instant)"""
    return db.query(StockItem).filter(StockItem.tenant_id == tenant_id).all()

@app.get("/bills", dependencies=[Depends(get_api_key)])
def get_bills(db: Session = Depends(get_db), tenant_id: str = Depends(get_current_tenant_id)):
    """Get outstanding bills from Shadow DB (Instant)"""
    return db.query(Bill).filter(Bill.tenant_id == tenant_id).all()

@app.get("/bills/receivables", dependencies=[Depends(get_api_key)])
def get_receivables(db: Session = Depends(get_db), tenant_id: str = Depends(get_current_tenant_id)):
    """Get only money owed TO us (Psychological: Anxiety Reduction)"""
    # Assuming positive amount is receivable
    return db.query(Bill).filter(Bill.amount > 0, Bill.tenant_id == tenant_id).all()

@app.get("/dashboard/kpi", dependencies=[Depends(get_api_key)])
def get_dashboard_kpi(db: Session = Depends(get_db), tenant_id: str = Depends(get_current_tenant_id)):
    """
    Get Key Performance Indicators for the Dashboard.
    - Total Sales (This Month vs Last Month)
    - Total Receivables (Current)
    - Total Payables (Current)
    - Cash in Hand (Current)
    """
    try:
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        
        # Calculate Last Month Start/End
        if now.month == 1:
            start_of_last_month = datetime(now.year - 1, 12, 1)
            end_of_last_month = datetime(now.year - 1, 12, 31)
        else:
            start_of_last_month = datetime(now.year, now.month - 1, 1)
            # Last day of last month is start_of_month - 1 day
            end_of_last_month = start_of_month - timedelta(days=1)

        # 1. Sales Logic
        # This Month
        sales_this_month = db.query(func.sum(Voucher.amount)).filter(
            Voucher.voucher_type == "Sales",
            Voucher.date >= start_of_month,
            Voucher.tenant_id == tenant_id
        ).scalar() or 0.0
        
        # Last Month
        sales_last_month = db.query(func.sum(Voucher.amount)).filter(
            Voucher.voucher_type == "Sales",
            Voucher.date >= start_of_last_month,
            Voucher.date <= end_of_last_month,
            Voucher.tenant_id == tenant_id
        ).scalar() or 0.0
        
        # Sales Change %
        if sales_last_month == 0:
            sales_change = 100.0 if sales_this_month > 0 else 0.0
        else:
            sales_change = ((sales_this_month - sales_last_month) / sales_last_month) * 100.0

        # Total Sales (All Time or Year to Date? Usually Dashboard shows YTD or Monthly. Let's show Monthly for "Total Sales" context or All Time? 
        # The UI says "Total Sales". Usually implies YTD. But for change %, we compare months.
        # Let's return This Month's Sales as the main number for now, as that's more actionable.
        # OR return Total YTD. Let's stick to Total YTD for the main number, but change is monthly? 
        # Actually, let's make "Total Sales" be "This Month's Sales" to match the change metric. 
        # User wants "math logic more correct". If I show Total All Time and say "12% from last month", that's confusing.
        # Let's return This Month's Sales.
        
        # 2. Receivables & Payables (Snapshot)
        # We don't have historical snapshots, so we can't calculate change accurately.
        # Better to show 0% change than fake data.
        receivables = db.query(func.sum(Bill.amount)).filter(Bill.amount > 0, Bill.tenant_id == tenant_id).scalar() or 0.0
        payables = db.query(func.sum(Bill.amount)).filter(Bill.amount < 0, Bill.tenant_id == tenant_id).scalar() or 0.0
        
        # 3. Cash in Hand
        cash_ledger = db.query(Ledger).filter(Ledger.name == "Cash", Ledger.tenant_id == tenant_id).first()
        cash_balance = cash_ledger.closing_balance if cash_ledger else 0.0
        
        return {
            "sales": sales_this_month,
            "sales_change": round(sales_change, 1),
            "receivables": receivables,
            "receivables_change": 0.0, # No historical data yet
            "payables": abs(payables),
            "payables_change": 0.0, # No historical data yet
            "cash": cash_balance,
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"KPI Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/daybook", dependencies=[Depends(get_api_key)])
def get_daybook(db: Session = Depends(get_db), tenant_id: str = Depends(get_current_tenant_id)):
    """Get today's transactions (Psychological: Dopamine/Activity)"""
    # For MVP, returning all. In real app, filter by date.
    return db.query(Voucher).filter(
        Voucher.tenant_id == tenant_id,
        Voucher.is_deleted == False  # ← ENTERPRISE: Exclude soft-deleted vouchers
    ).order_by(Voucher.date.desc()).all()

@app.get("/search", dependencies=[Depends(get_api_key)])
def global_search(q: str, db: Session = Depends(get_db), tenant_id: str = Depends(get_current_tenant_id)):
    """Global Search (Psychological: Control)"""
    ledgers = db.query(Ledger).filter(Ledger.name.ilike(f"%{q}%"), Ledger.tenant_id == tenant_id).all()
    items = db.query(StockItem).filter(StockItem.name.ilike(f"%{q}%"), StockItem.tenant_id == tenant_id).all()
    vouchers = db.query(Voucher).filter(or_(
        Voucher.voucher_number.ilike(f"%{q}%"),
        Voucher.party_name.ilike(f"%{q}%")
    ), Voucher.tenant_id == tenant_id).all()
    
    return {
        "ledgers": ledgers,
        "items": items,
        "vouchers": vouchers
    }

@app.post("/sync", dependencies=[Depends(get_api_key)])
async def trigger_sync(background_tasks: BackgroundTasks):
    """Trigger Tally Sync in Background"""
    background_tasks.add_task(sync_engine.sync_now)
    return {"status": "Sync Started", "message": "Data is being pulled from Tally..."}

# Model moved to backend/routers/vouchers.py

class LedgerDraft(BaseModel):
    name: str
    parent: str
    opening_balance: float
    gstin: Optional[str] = None
    email: Optional[str] = None

@app.post("/ledgers", dependencies=[Depends(get_api_key)])
async def create_ledger_endpoint(ledger: LedgerDraft):
    """
    Create a new ledger in Tally via the Sync Engine.
    """
    # 1. Validate GSTIN if provided
    if ledger.gstin:
        validation = GSTEngine.validate_gstin(ledger.gstin)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=f"Invalid GSTIN: {validation['error']}")

    try:
        # 2. Construct ledger data
        ledger_data = ledger.dict()
        
        # 3. Push to Tally
        result = sync_engine.tally.create_ledger(ledger_data)
        
        if result['status'] == "Success":
            # 4. Save to Shadow DB
            db = SessionLocal()
            try:
                new_ledger = Ledger(
                    name=ledger.name,
                    parent=ledger.parent,
                    opening_balance=ledger.opening_balance,
                    gstin=ledger.gstin,
                    email=ledger.email,
                    last_synced=datetime.now()
                )
                db.add(new_ledger)
                db.commit()
            except Exception as e:
                logger.error(f"Shadow DB Error: {e}")
                # Don't fail request if Tally succeeded
            finally:
                db.close()
                
            return {"status": "success", "message": "Ledger created successfully", "tally_response": result}
        else:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Tally Rejected", "details": result})

    except Exception as e:
        logger.error(f"Failed to create ledger: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint moved to backend/routers/vouchers.py

# Endpoint moved to backend/routers/vouchers.py

@app.get("/")
def root():
    return {"status": "ok", "message": "K24 Backend with KITTU Orchestration & Conversational AI"}

# Mount Socket.IO App (WebSocket) as FINAL fallback
from socket_manager import socket_manager
app.mount("/socket.io", socket_manager.app)
