# K24 — Architecture Decisions
# This file explains WHY, not WHAT.
# ✅ VERIFIED against live codebase — April 2026
# If a decision looks wrong — read the reasoning before trying to fix it.

***

## Real-Time Communication Architecture (VERIFIED)

This is the actual message flow confirmed by codebase inspection:

```
INBOUND (WhatsApp → Tally):
  1. User sends WhatsApp message
  2. Baileys listener (Railway) receives it
  3. Baileys calls cloud-backend POST /api/whatsapp/incoming
     └── cloud-backend/routers/whatsapp_cloud.py : line 164
  4. cloud-backend inserts row into Supabase whatsapp_message_queue
     └── cloud-backend/routers/whatsapp_cloud.py : line 262
  5. Desktop poller loops every ~5s, GETs pending rows from Supabase
     └── backend/services/whatsapp_poller.py : _fetch_pending_jobs() : line 245
  6. Desktop processes the job locally (Tally XML, OCR, etc.)

OUTBOUND (K24 reply → WhatsApp):
  7. Desktop POSTs response DIRECTLY to Baileys cloud listener
     └── backend/services/whatsapp_poller.py : lines 421-463
  ⚠️  This BYPASSES cloud-backend entirely on the return path.
      Desktop talks to Baileys directly, not through cloud-backend.

Desktop auto-starts the poller at launch:
  └── backend/api.py : lifespan : line 113
      asyncio.create_task(start_whatsapp_poller())
```

***

## Why Supabase Queue (Not WebSocket or Direct HTTP for Inbound)

**The constraint:** WhatsApp messages arrive on cloud. Desktop may be offline for hours.
Messages must persist until the desktop comes online and polls.

**The decision:** Supabase PostgreSQL table (whatsapp_message_queue) as the durable queue.
- Simple. Already in the stack.
- Handles offline-desktop gracefully — messages wait in the table.
- No new infrastructure required for a solo founder.
- Desktop polls every ~5 seconds — acceptable latency for accounting operations.

**The tradeoff:** Not real-time. ~5 second polling lag.
Acceptable for accounting — entries don't need millisecond response.

***

## The Dormant Socket.IO Server (IMPORTANT — Decision Required)

**What was found in the codebase:**
```
backend/socket_manager.py : line 16  → AsyncServer is instantiated at import
backend/api.py            : line 1434 → app.mount("/socket.io", socket_manager.app)
backend/auth.py           : line 67   → JWT creation for Socket.IO auth
frontend/ConnectDevice.tsx : line 165 → localStorage.setItem("k24_socket_token", ...)
```

**The reality:** A full Socket.IO server spins up every time the desktop backend starts.
A JWT is created for it. The frontend stores that JWT in localStorage.
**But no client in the entire codebase ever opens the WebSocket connection.**
The server is live, listening, and completely unused.

**This is not a bug — it is an incomplete feature.** The infrastructure was built.
The frontend side was never wired up to use it.

**Decision required (founder must decide, not agents):**
```
Option A: Complete it
  Wire frontend Socket.IO client to connect using the stored k24_socket_token.
  Use case: real-time dashboard updates, live Kittu responses, instant notifications.
  Cost: 1-2 days of builder work.

Option B: Remove it for now
  Remove socket_manager.py, remove the mount in api.py, remove token storage in frontend.
  Benefit: cleaner startup, fewer moving parts, no dead code.
  Cost: 30 minutes. Reversible later.
```
Until this decision is made: do not add new logic that depends on Socket.IO.
Do not remove it without founder approval. It stays dormant.

***

## The Duplicate whatsapp_poller.py (IMPORTANT — Known Risk)

**What was found:**
```
backend/services/whatsapp_poller.py           ← ACTIVE — runs on desktop
cloud-backend/services/whatsapp_poller.py     ← DUPLICATE — has a localhost call:
  line 352: local_url = f"http://127.0.0.1:{DESKTOP_BACKEND_PORT}/api/baileys/process"
```

**What this means:** The cloud version of the poller contains a direct HTTP call
to the desktop at 127.0.0.1 — which only works if cloud and desktop are on the same machine.
This is an architectural leftover from an earlier design where cloud would push to desktop directly.

**Current state:** The desktop version is the active poller. The cloud version appears dormant.

**The risk:** If someone deploys the cloud-backend and the cloud poller activates,
it will try to call localhost and fail silently — or cause confusion about which poller
is actually running.

**Action required before .exe launch:**
- Confirm cloud-backend/services/whatsapp_poller.py is NOT being started in cloud-backend/main.py
- If it is not used, mark it clearly with a comment: `# DEPRECATED — desktop poller handles this`
- If it is used, document why and when

***

## The Outbound Response Path Bypasses cloud-backend

**The discovered reality:**
After processing a WhatsApp message, the desktop backend calls Baileys directly:
```
backend/services/whatsapp_poller.py : lines 421-463
→ self._http_cloud.post(baileys_url, ...)
```

This means the outbound path is:
`Desktop → Baileys directly` (not `Desktop → cloud-backend → Baileys`)

**Why this matters:**
- The cloud-backend has no visibility into outbound responses
- There is no outbound message logging or audit trail in cloud-backend
- Baileys URL must be configured correctly in desktop environment variables
- If Baileys URL changes, desktop .env must be updated (not just cloud-backend)

**For Phase 2:** Route all outbound through cloud-backend for unified logging and retry logic.
For Phase 1: This is acceptable — it works. Document it and don't accidentally break it.

***

## Why Tally as the Database Engine

**The reality:** 63 million Indian SMBs run on Tally.
Their historical data, their CAs, their auditors — all in Tally.
Migrating away means abandoning years of records and established processes.

**The decision:** K24 uses Tally as the accounting ledger.
We post XML, Tally stores and validates. User never migrates.
K24 is a powerful interface on top of what already exists.

**The consequence:** Everything K24 writes must be valid Tally XML.
`tally_golden_xml.py` is the sacred contract. An invalid tag breaks all Tally posting silently.

***

## Why localhost:9000 Only (No Network Tally)

Tally's XML API only listens on localhost by default.
Exposing it over a network requires third-party tools and IT setup most SMBs don't have.

Hardcoded: localhost:9000. Same machine as desktop app always. No exceptions.

***

## Why SQLite Shadow Database (k24_shadow.db)

Direct Tally XML queries are slow (XML parsing + HTTP round-trip).
Kittu needs to answer business questions in under 3 seconds.

Mirror Tally data into SQLite (k24_shadow.db). Kittu queries SQLite first.
Falls back to direct Tally XML only if needed.

**Known risk:** Shadow DB can drift after crash or failed sync. Documented architectural debt.
**Current issue (KU-1):** Dashboard showing wrong receivables, cash, top customers — shadow DB sync bug.

***

## Why Two Railway Projects

Baileys is Node.js. Backend is Python.
One Railway project = runtime and dependency conflicts.

- Railway Project 1: cloud-backend/ (Python FastAPI)
- Railway Project 2: baileys-listener/ (Node.js)

Communication: cloud-backend writes to Supabase queue. Desktop reads it.
Baileys sends webhook to cloud-backend. Desktop responds directly to Baileys.

***

## Why api.py Is a God-File (1435 Lines)

Early development prioritized getting the full pipeline working end-to-end.
Structural separation was correctly deferred.

**What lives inside it:**
- Lines ~1-250: App setup, CORS (including localhost:1420 and tauri.localhost for desktop frontend),
  security, Sentry, router registration, lifespan (auto-starts WhatsApp poller + Tally sync + Socket.IO mount)
- Lines ~251-900: Kittu AI chat, conversation memory, streaming responses, credit limits, health checks
- Lines ~901-1435: CRUD for ledgers/parties, dashboard queries, shadow DB reads, WebSocket mount

**Current rule:** Do not add to api.py. New logic → new files in backend/services/.

***

## GST Architecture

Rates come from Tally's own ledger and stock item configuration — NOT from K24 code.
All GST logic lives in backend/compliance/gst_engine.py only. Zero inline calculations elsewhere.

**Current bug (KU-4):** Desktop auto-creates a new party from OCR but does NOT create
the GST ledger for that party in Tally. Fix required before .exe launch.

***

## Phase 2 Architecture Target

```
CURRENT (Phase 1):                    →    TARGET (Phase 2):
Supabase queue as only inbound path   →    + Socket.IO for real-time (complete dormant server)
Outbound bypasses cloud-backend       →    All outbound routed through cloud-backend
Duplicate whatsapp_poller.py          →    Single canonical poller, cloud version removed
SQLite as primary local DB            →    Supabase PostgreSQL as primary
api.py god-file (1435 lines)          →    Split: startup/ + routers/ + services/
Baileys unofficial WhatsApp           →    Evaluate WhatsApp Business API
```
