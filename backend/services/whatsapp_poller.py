"""
WhatsApp Poller Service
=======================

Architecture Role:
  Cloud (Railway) receives WhatsApp messages and writes them to the
  Supabase `whatsapp_message_queue` table with status='pending'.

  This service runs inside the DESKTOP backend. It:
    1. Polls Supabase every N seconds for 'pending' jobs scoped to this tenant
    2. Claims each job (marks it 'processing') to prevent double-pickup
    3. Forwards the message to the local AI pipeline (/api/baileys/process)
    4. Sends the AI reply to the customer via the Baileys listener (/send-reply)
    5. Marks the job 'completed' or 'failed' in Supabase

Usage:
  Started automatically by api.py lifespan on backend startup.
  Stop gracefully on shutdown.

Environment Variables (all optional — production defaults are baked in):
  BAILEYS_LISTENER_URL   - Override the Baileys listener URL (dev/staging only)
  BAILEYS_SECRET         - Override the shared secret (dev/staging only)
  SUPABASE_URL           - Override the Supabase project URL (dev/staging only)
  SUPABASE_SERVICE_KEY   - Override the Supabase service-role key (dev/staging only)
  WA_POLL_INTERVAL       - Polling interval in seconds (default: 5)
  WA_POLL_BATCH_SIZE     - Max jobs to pick up per poll cycle (default: 5)
  DESKTOP_BACKEND_PORT   - Port the local backend is listening on (default: 8001)
"""

import asyncio
import httpx
import os
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger("whatsapp_poller")

# ──────────────────────────────────────────────
# Configuration — Production defaults baked in.
# End users need ZERO configuration for this to work.
# Env vars override these (useful for dev/staging).
# ──────────────────────────────────────────────
_PROD_SUPABASE_URL        = "https://gxukvnoiyzizienswgni.supabase.co"
_PROD_SUPABASE_SERVICE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd4dWt2bm9peXppemllbnN3Z25pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTc1MzE5OCwiZXhwIjoyMDg1MTEzMTk4fQ"
    ".QXK3psAWhGl-cdYqfSnqdjJBiREZIrVlt9a7HLH0WU4"
)
_PROD_BAILEYS_URL          = "https://artistic-healing-production.up.railway.app"
_PROD_BAILEYS_SECRET       = "k24_baileys_secret"

POLL_INTERVAL: int        = int(os.getenv("WA_POLL_INTERVAL", "5"))
POLL_BATCH_SIZE: int      = int(os.getenv("WA_POLL_BATCH_SIZE", "5"))
DESKTOP_BACKEND_PORT: int = int(os.getenv("DESKTOP_BACKEND_PORT", "8001"))

# These fall back to the baked-in production values if the env var is absent.
BAILEYS_LISTENER_URL: str     = os.getenv("BAILEYS_LISTENER_URL") or _PROD_BAILEYS_URL
BAILEYS_SECRET: str           = os.getenv("BAILEYS_SECRET")        or _PROD_BAILEYS_SECRET
SUPABASE_URL: str             = os.getenv("SUPABASE_URL")          or _PROD_SUPABASE_URL
SUPABASE_SERVICE_KEY: str     = os.getenv("SUPABASE_SERVICE_KEY")  or _PROD_SUPABASE_SERVICE_KEY


# ──────────────────────────────────────────────
# Helper: Supabase REST Headers
# ──────────────────────────────────────────────
def _supabase_headers(use_service_key: bool = True) -> Dict[str, str]:
    """Build the auth headers for direct Supabase REST API calls."""
    key = SUPABASE_SERVICE_KEY if use_service_key else os.getenv("SUPABASE_ANON_KEY", "")
    return {
        "apikey": key or "",
        "Authorization": f"Bearer {key or ''}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _supabase_rest_url(table: str) -> str:
    """Return the Supabase PostgREST endpoint for a given table."""
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is not configured.")
    return f"{SUPABASE_URL}/rest/v1/{table}"


# ──────────────────────────────────────────────
# WhatsAppPoller Class
# ──────────────────────────────────────────────
class WhatsAppPoller:
    """
    Background service that drains the Supabase whatsapp_message_queue
    and triggers the local AI pipeline + Baileys send-reply for each job.
    """

    def __init__(self):
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._http: Optional[httpx.AsyncClient] = None

    # ── Lifecycle ──────────────────────────────

    async def start(self):
        """Start the poller as a background task."""
        # All values have baked-in production defaults — no .env required for end users.
        # Guard is only a sanity check in case something went very wrong at import time.
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            logger.warning(
                "⚠️  WhatsApp Poller disabled: Supabase config missing (this should not happen)."
            )
            return

        self._running = True
        self._http = httpx.AsyncClient(timeout=20.0)
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(
            f"🟢 WhatsApp Poller started "
            f"(interval={POLL_INTERVAL}s, batch={POLL_BATCH_SIZE}, "
            f"baileys={BAILEYS_LISTENER_URL})"
        )

    async def stop(self):
        """Signal the poll loop to stop and await clean shutdown."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._http:
            await self._http.aclose()
        logger.info("🔴 WhatsApp Poller stopped.")

    # ── Main Poll Loop ─────────────────────────

    async def _poll_loop(self):
        """Core polling loop — runs forever until stopped."""
        logger.info("🔄 Poller loop running...")
        while self._running:
            try:
                tenant_id = self._get_tenant_id()
                if not tenant_id:
                    logger.debug("No tenant_id resolved yet — skipping this cycle.")
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                jobs = await self._fetch_pending_jobs(tenant_id)

                if jobs:
                    logger.info(f"📥 Fetched {len(jobs)} pending job(s) for tenant {tenant_id}")

                for job in jobs:
                    if not self._running:
                        break
                    await self._handle_job(job)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Poll loop error: {e}", exc_info=True)

            await asyncio.sleep(POLL_INTERVAL)

    async def _handle_job(self, job: Dict[str, Any]):
        """Process a single job end-to-end."""
        job_id: str = job.get("id", "unknown")
        customer_phone: str = job.get("customer_phone", "")
        message_text: str = job.get("message_text", "")
        tenant_id: str = job.get("tenant_id", "")

        logger.info(f"🔧 Handling job {job_id} | from: {customer_phone}")

        # Step 1: Claim the job (set status → 'processing')
        claimed = await self._claim_job(job_id)
        if not claimed:
            logger.warning(f"⚠️  Job {job_id} already claimed by another worker — skipping.")
            return

        # Step 2: Run the AI pipeline
        reply_text: Optional[str] = None
        try:
            reply_text = await self._process_via_ai(customer_phone, message_text, job)
        except Exception as e:
            logger.error(f"❌ AI processing failed for job {job_id}: {e}", exc_info=True)
            await self._complete_job(job_id, "failed", error_message=str(e))
            return

        # Step 3: Send reply via Baileys listener
        if reply_text:
            try:
                await self._send_reply(to_phone=customer_phone, reply_text=reply_text)
            except Exception as e:
                logger.error(f"❌ Send-reply failed for job {job_id}: {e}", exc_info=True)
                await self._complete_job(job_id, "failed", error_message=f"send_reply_error: {e}")
                return

        # Step 4: Mark completed
        await self._complete_job(job_id, "completed")
        logger.info(f"✅ Job {job_id} completed.")

    # ── Supabase Queue Operations ──────────────

    async def _fetch_pending_jobs(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Read pending jobs from whatsapp_message_queue scoped to this tenant.
        Only fetches 'pending' rows (not 'processing', 'completed', or 'failed').
        """
        try:
            url = _supabase_rest_url("whatsapp_message_queue")
            params = {
                "tenant_id": f"eq.{tenant_id}",
                "status": "eq.pending",
                "order": "created_at.asc",
                "limit": str(POLL_BATCH_SIZE),
                "select": "id,tenant_id,customer_phone,message_text,message_type,raw_payload,created_at",
            }
            resp = await self._http.get(url, headers=_supabase_headers(), params=params)

            if resp.status_code == 200:
                return resp.json()
            else:
                logger.error(
                    f"Supabase fetch failed: {resp.status_code} — {resp.text[:200]}"
                )
                return []
        except Exception as e:
            logger.error(f"_fetch_pending_jobs error: {e}", exc_info=True)
            return []

    async def _claim_job(self, job_id: str) -> bool:
        """
        Atomically claim a job by updating status to 'processing'.
        Uses a conditional PATCH: only succeeds if status is still 'pending'.
        Returns True if successfully claimed, False if already taken.
        """
        try:
            url = _supabase_rest_url("whatsapp_message_queue")
            params = {
                "id": f"eq.{job_id}",
                "status": "eq.pending",   # Guard: only update if STILL pending
            }
            body = {
                "status": "processing",
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            resp = await self._http.patch(url, headers=_supabase_headers(), params=params, json=body)

            # Supabase PATCH returns 200 with the updated row(s), or 200 with [] if no rows matched
            if resp.status_code == 200:
                updated_rows = resp.json()
                return len(updated_rows) > 0
            else:
                logger.error(f"Claim failed: {resp.status_code} — {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"_claim_job error: {e}", exc_info=True)
            return False

    async def _complete_job(
        self, job_id: str, status: str, error_message: Optional[str] = None
    ):
        """
        Mark a job as 'completed' or 'failed' in Supabase with a timestamp.
        """
        try:
            url = _supabase_rest_url("whatsapp_message_queue")
            params = {"id": f"eq.{job_id}"}
            body: Dict[str, Any] = {
                "status": status,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            if error_message:
                body["error_message"] = error_message[:500]  # cap to prevent DB overflow

            resp = await self._http.patch(url, headers=_supabase_headers(), params=params, json=body)

            if resp.status_code != 200:
                logger.error(
                    f"_complete_job [{status}] failed for {job_id}: "
                    f"{resp.status_code} — {resp.text[:200]}"
                )
        except Exception as e:
            logger.error(f"_complete_job error: {e}", exc_info=True)

    # ── AI Pipeline ────────────────────────────

    async def _process_via_ai(
        self, customer_phone: str, message_text: str, job: Dict[str, Any]
    ) -> Optional[str]:
        """
        Forward the message to the local backend's Baileys AI pipeline
        (POST /api/baileys/process) and return the reply text.

        This reuses ALL existing logic in routers/baileys.py:
          - Tenant resolution
          - LangGraph agent call
          - ChatHistory logging
        """
        local_url = f"http://127.0.0.1:{DESKTOP_BACKEND_PORT}/api/baileys/process"

        payload = {
            "sender_phone": customer_phone,
            "message_text": message_text or "",
            # Pass through media if present in the raw_payload
            "media": (job.get("raw_payload") or {}).get("media"),
        }

        headers = {
            "X-Baileys-Secret": BAILEYS_SECRET,
            "Content-Type": "application/json",
        }

        logger.debug(f"🤖 Calling AI pipeline for {customer_phone}: {message_text[:60]}...")
        resp = await self._http.post(local_url, headers=headers, json=payload)

        if resp.status_code == 200:
            data = resp.json()
            reply = data.get("reply_message") or data.get("message")
            logger.info(f"🤖 AI reply: {str(reply)[:80]}...")
            return reply
        else:
            logger.error(
                f"AI pipeline error: {resp.status_code} — {resp.text[:300]}"
            )
            raise RuntimeError(
                f"AI pipeline returned {resp.status_code}: {resp.text[:200]}"
            )

    # ── Baileys Send-Reply ─────────────────────

    async def _send_reply(self, to_phone: str, reply_text: str):
        """
        Send a reply back to the WhatsApp customer via the Baileys listener's
        /send-reply endpoint (listener.js line 129).

        Baileys listener (Railway - artistic-healing) expected payload:
          { "to": "917XXXXXXXXX", "text": "Reply text here" }   ← key is 'text', NOT 'message'

        The listener auto-appends @s.whatsapp.net or @lid based on number length.
        """
        url = f"{BAILEYS_LISTENER_URL}/send-reply"
        # NOTE: Baileys listener.js parses { to, text } — NOT { to, message }
        payload = {"to": to_phone, "text": reply_text}
        headers = {
            "Content-Type": "application/json",
            "X-Baileys-Secret": BAILEYS_SECRET,
        }

        logger.info(f"📤 Sending reply to {to_phone} via Baileys ({BAILEYS_LISTENER_URL})...")
        resp = await self._http.post(url, headers=headers, json=payload)

        if resp.status_code in (200, 201, 202):
            logger.info(f"✅ Reply sent to {to_phone}")
        else:
            raise RuntimeError(
                f"Baileys /send-reply returned {resp.status_code}: {resp.text[:200]}"
            )

    # ── Tenant ID Resolution ───────────────────

    def _get_tenant_id(self) -> Optional[str]:
        """
        Get the tenant_id for the currently logged-in user on this desktop.

        Lookup order:
          1. TENANT_ID env var (explicit override, useful for dev)
          2. Local SQLite User table — active user's tenant_id
          3. None (poller will skip this cycle and retry)
        """
        # 1. Explicit env var override (dev convenience)
        env_tid = os.getenv("TENANT_ID")
        if env_tid:
            return env_tid

        # 2. Query local SQLite
        try:
            from backend.database import SessionLocal, User

            db = SessionLocal()
            try:
                # Get the first active user with a tenant_id
                user = (
                    db.query(User)
                    .filter(User.tenant_id.isnot(None))
                    .order_by(User.id)
                    .first()
                )
                if user and user.tenant_id:
                    return str(user.tenant_id)
            finally:
                db.close()
        except Exception as e:
            logger.debug(f"Could not resolve tenant_id from User table: {e}")

        logger.warning("⚠️  Could not resolve tenant_id — set TENANT_ID env var or log in first.")
        return None


# ──────────────────────────────────────────────
# Module-level singleton + lifecycle helpers
# (called by api.py lifespan)
# ──────────────────────────────────────────────

_poller_instance: Optional[WhatsAppPoller] = None


async def start_whatsapp_poller():
    """Start the global WhatsApp Poller. Called from api.py on startup."""
    global _poller_instance
    _poller_instance = WhatsAppPoller()
    await _poller_instance.start()


async def stop_whatsapp_poller():
    """Stop the global WhatsApp Poller. Called from api.py on shutdown."""
    global _poller_instance
    if _poller_instance:
        await _poller_instance.stop()
        _poller_instance = None


def get_poller_status() -> Dict[str, Any]:
    """Return current poller health info (used by /health-style endpoints if needed)."""
    if _poller_instance is None:
        return {"running": False, "reason": "not_started"}
    return {
        "running": _poller_instance._running,
        "poll_interval_seconds": POLL_INTERVAL,
        "batch_size": POLL_BATCH_SIZE,
        "baileys_url": BAILEYS_LISTENER_URL,
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_SERVICE_KEY),
    }
