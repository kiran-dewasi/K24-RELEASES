# K24 Platform – AI Agent Constitution
# Every agent reads this file COMPLETELY before touching any file.
# This is the law. Not a suggestion. Not documentation. The law.
# ✅ VERIFIED against live codebase — April 2026
# Human authority: Founder only.

***

## 1. PROJECT IDENTITY

**What K24 is:**
K24 is an AI-powered ERP where Tally is the database engine and the user never opens Tally again.
A wholesaler photos a bill on WhatsApp → Gemini reads it → K24 creates the voucher → posts to Tally. Automatically.
A wholesaler asks "mera kitna udhar bacha hai" → K24 queries his Tally data → replies in seconds.
The desktop app (with Kittu, the AI assistant) shows receivables, cash, top customers, sales graph,
and inventory — live from Tally — without him ever opening Tally.

**One-line for users:**
"K24 saves your time and effort, makes your data accessible worldwide via WhatsApp,
lets you push data from anywhere on mobile, and gives you a 24/7 personal assistant for your business."

**Target user:** Indian SMBs — primarily wholesalers.

**Two most critical features right now:**
1. Photo → Bill (WhatsApp, zero manual entry)
2. Real-time business data on WhatsApp, anytime, anywhere

**Current phase:** Phase 1 — Productionise an already-working system.
Not redesign. Not rebuild. Make it reliable for real users outside the dev machine.

**Phase 1 success definition:**
A real user installs the desktop app, logs in via deep link, uses the full WhatsApp + Tally flow reliably,
sees accurate dashboard data, and the installer works stably — all outside the founder's dev machine.

***

## 2. ARCHITECTURE OVERVIEW

```
CLOUD:
  cloud-backend/        FastAPI multi-tenant API
                        (Supabase, WhatsApp queue, licensing)
  Supabase Postgres     auth, tenants, whatsapp_message_queue, mappings
  Baileys listener      WhatsApp Web socket (Node.js on Railway)
  Frontend on Vercel    Next.js

DESKTOP:
  backend/              FastAPI sidecar, talks to Tally via XML on localhost:9000
  k24_shadow.db         SQLite — local mirror of Tally (fast queries)
  k24.db                SQLite — core app data
  Tauri wrapper         Desktop shell around frontend

VERIFIED MESSAGE FLOW:
  Inbound:
    WhatsApp → Baileys → cloud-backend POST /api/whatsapp/incoming
    → Supabase insert (whatsapp_message_queue)
    → Desktop poller polls Supabase every ~5s
    → Desktop processes locally (Tally XML, OCR, etc.)

  Outbound:
    Desktop → POST directly to Baileys cloud listener  ⚠️ bypasses cloud-backend
    (cloud-backend has NO visibility into outgoing replies)

KITTU AI (chat assistant):
  Data source:  k24_shadow.db (SQLite) primary
                Direct Tally XML query (LangGraph tool) fallback
  Models:       Gemini 2.0 Flash (default)
                Gemini 1.5 Flash (complex: >300 chars, "analyze", images)
                Gemini 1.5 Pro (rate-limit fallback)
  Personality:  Formal. Answers in Hindi or English as the user writes.

DORMANT (built but not connected):
  backend/socket_manager.py  Socket.IO server runs at startup, zero clients connect
  ⚠️ Decision required: complete it or remove it. See ARCHITECTURE.md.
```

***

## 3. CRITICAL: DO NOT TOUCH ZONES

### 3.1 Tally XML & Money Logic — ASK FOUNDER FIRST

```
backend/tally_connector.py              Tally XML API client
backend/tally_xml_builder.py            Voucher/ledger XML generation
backend/tally_golden_xml.py             Golden XML templates — THE canonical reference
backend/services/tally_operations.py    Workflows that push vouchers to Tally
```

**Rule:** If you think ANY of these must change → STOP.
Ask: "Do you want to change Tally XML / money logic here?" and wait for explicit founder approval.

### 3.2 Authentication & Deep Link — REVIEW REQUIRED

```
backend/auth.py                         includes Socket.IO JWT creation
cloud-backend/routers/auth.py
backend/middleware/tenant_context.py
frontend/src/middleware.ts
frontend/src/lib/supabase/server.ts
```

**Rule:**
- MAY fix concrete bugs and wiring problems.
- MAY NOT change the overall auth model (Supabase + JWT + deep link) without an approved plan.
- For any auth change: add tests + run a real login/deeplink flow before declaring done.

### 3.3 Multi-Tenant Isolation & Encryption

```
backend/database/__init__.py            TenantMixin, all models
backend/database/encryption.py          Field-level encryption
backend/routers/whatsapp.py             identify_user_by_phone and mappings
Supabase RLS policies                   backend/database/phase*_schema.sql
```

**Rule:** Every DB write scoped to tenant_id. Never bypass RLS. Never.

### 3.4 Production Config & Secrets

```
Any .env files
frontend/src-tauri/tauri.conf.json      signing, bundle IDs, URLs
Dockerfiles
GitHub Actions workflows
```

**Rule:** No hardcoded secrets. Treat env values as opaque. Never log them.

### 3.5 Socket.IO Server — DO NOT CHANGE WITHOUT DECISION

```
backend/socket_manager.py              Socket.IO AsyncServer
backend/api.py : line 1434             app.mount("/socket.io", ...)
backend/auth.py : line 67              Socket.IO JWT creation
frontend/src/components/auth/ConnectDevice.tsx : line 165  token storage
```

**Status:** Server is live at startup but completely unused — no client connects.
**Rule:** Do not add logic that depends on Socket.IO until the founder decides Option A or B.
Do not remove it without founder approval. It stays dormant until a decision is made.
Full context in ARCHITECTURE.md → "The Dormant Socket.IO Server".

### 3.6 GST Rules — NON-NEGOTIABLE

**NEVER hardcode GST rates.** Not 0.18. Not 18. Not 0.09. Not 9. Not 0.05. Not 5. Not 0.28. Not 28.
Rates come from Tally's own ledger and stock item configuration.

```
backend/compliance/gst_engine.py   THE ONLY place GST logic lives
```

Zero inline GST calculations anywhere else. If GST logic is unclear → stop and ask.

### 3.7 Agent Scope Creep — Zero Tolerance

If a prompt does not explicitly name a file, the agent MUST NOT touch that file.
Seeing a failing test is NOT permission to fix the underlying production code.
Fixing tests is NOT permission to fix the code being tested.

Any agent that modifies a 🔴 zone file without explicit founder approval
has violated this constitution. The change must be reviewed and potentially reverted
before any further work proceeds.

***

## 4. SAFE TO MODIFY (PREFERRED WORK AREA)

```
Cloud WhatsApp flow:
  cloud-backend/routers/whatsapp_cloud.py
  cloud-backend/services/tenant_routing.py
  cloud-backend/database/supabase_client.py

Cloud message queue:
  Supabase migrations for whatsapp_message_queue

Desktop poller (ACTIVE one — backend/ version only):
  backend/services/whatsapp_poller.py
  backend/desktop_main.py (non-auth sections only)

New services and schemas:
  backend/services/          (new files only — do not add to god-files)
  backend/schemas/           (new files only)
  backend/compliance/        (all files)

Tests — always encouraged:
  tests/**, test_*.py, verify_*.py

UI that does not affect auth:
  frontend/src/components/**
  frontend/src/app/**/page.tsx
```

### God-Files — FROZEN (Do Not Add To These)

```
backend/api.py              1435 lines — read to understand, never add to it
backend/routers/vouchers.py god-file — plan the split before touching
```

New logic always goes in new files in backend/services/.

### The Duplicate Poller — Handle With Care

```
backend/services/whatsapp_poller.py          ← ACTIVE — this is the real one
cloud-backend/services/whatsapp_poller.py    ← DUPLICATE — has localhost call inside
                                               line 352: http://127.0.0.1:{PORT}/api/baileys/process
```

**Rule:** Only modify the backend/ version. Verify cloud-backend version is NOT
being started in cloud-backend/main.py before any deployment changes.

***

## 5. PHASE 1 FOCUS — WHAT WE ARE BUILDING NOW

```
✅ Stabilise cloud WhatsApp queue (Supabase) and desktop poller
✅ Move WhatsApp + tenant routing logic into cloud-backend/
✅ Fix auth + deep link for desktop login and device licensing
✅ Make Tauri installer reliable: install → auto-start backend → connect cloud
✅ Fix dashboard data accuracy (receivables, cash, top customers wrong)
✅ Fix desktop app → Tally sync (ignores GST and extra expenses on new parties)
✅ Fix PDF and Excel export templates (incomplete, data gaps)
✅ Harden fallback paths before .exe launch
✅ Resolve duplicate whatsapp_poller.py (confirm cloud version is dormant)
✅ Decide: Socket.IO complete or remove (dormant server running at every startup)
```

### Out of Scope for Phase 1

```
❌ Changing Tally XML or financial algorithms
❌ Multi-company features
❌ Full UI redesign or new product areas
❌ Mobile app, voice input, bank reconciliation, e-Invoicing
```

***

## 6. CURRENT SYSTEM STATE (update as things are fixed)

### ✅ Working
- WhatsApp push: photo → Gemini OCR → Tally voucher
- WhatsApp pull: basic queries work
- Tally XML generation and posting (tally_golden_xml.py is the reference)
- Gemini OCR: party matching, auto-creates new party if not found
- Kittu text chat: SQLite shadow DB queries work
- Multi-tenant auth: Supabase maps WhatsApp number → tenant_id correctly
- Desktop poller: correctly polls Supabase queue, processes jobs
- Outbound responses: desktop → Baileys direct call works

### 🔶 Broken or Incomplete (fix before .exe launch)
- Dashboard data: receivables, cash, top customers showing wrong values
- Desktop → Tally sync: ignores GST fields and extra expenses on new parties
- PDF and Excel export: templates incomplete, data gaps
- Socket.IO server: running at startup, zero clients — decision pending
- cloud-backend/services/whatsapp_poller.py: duplicate with localhost call — needs confirmation

### ❓ Unknown (must investigate before launch)
- GST source in WhatsApp flow: does photo→bill inherit GST from Tally ledger or guess?
- Kittu query routing: what exactly decides SQLite path vs direct Tally XML?
- 2AM recovery: if k24_shadow.db corrupts, what is the recovery path?
- Desktop GST ledger creation: confirmed broken, root cause unknown

***

## 7. BUILDER + MCP RULES

**Builder may:**
- Use MCP tools for Supabase, Vercel, Railway, logs, and DB inspection.
- Fix end-to-end issues across desktop + cloud within the allowed file list.

**For any change touching Tally XML, money logic, or auth/deeplink:**
→ Propose the change and get explicit founder approval before editing any code.

***

## 8. TESTING & VERIFICATION

**1. Tests** — add or update in tests/ for every non-trivial change.
WhatsApp flow: cover queue insert, poll, complete, tenant isolation.
Dashboard: cover accuracy of receivables, cash, top customers vs shadow DB.

**2. Run** — document exact pytest command + results.

**3. End-to-End Check** — simulate one realistic flow per change.
Auth changes: real login + deep link through desktop app required.

**4. Done Definition — ALL of these must be true:**
- Change is within the allowed file scope
- Tests pass (results documented)
- One real-flow check successful and described
- No new ruff lint errors
- tier1 eval score has not decreased

***

## 9. AGENT OPERATING RULES

Every agent session MUST:
1. Read this file completely before any action
2. Read ETHOS.md before writing any code
3. Check learnings/sessions/ for the module being touched
4. Write a step-by-step plan — no code until plan is acknowledged
5. Run pytest after every file change
6. Declare done only when Done Definition (Section 8) is fully satisfied

Every agent session MUST NEVER:
- Touch 🔴 zones without explicit founder approval
- Hardcode any GST rate anywhere
- Write GST logic outside backend/compliance/gst_engine.py
- Add new logic to api.py or vouchers.py (god-files — frozen)
- Modify cloud-backend/services/whatsapp_poller.py without confirming it is truly dormant
- Add Socket.IO client logic without founder's Option A/B decision
- Write raw SQL strings — ORM or Supabase client only
- Swallow errors silently on any financial operation
- Guess on tax or financial logic — stop and ask

***

## 10. KNOWN UNKNOWNS — Must Be Resolved Before .exe Launch

```
KU-1: GST source in WhatsApp flow
      When photo→bill runs, does it correctly inherit GST from Tally ledger
      or does it guess/default? Trace through tools/__init__.py → tally_xml_builder.py

KU-2: Kittu query routing decision
      What decides SQLite path vs direct Tally XML in Kittu?
      Trace in query_orchestrator.py and graph.py. Document the decision rule.

KU-3: 2AM recovery process
      If k24_shadow.db corrupts or Railway goes down, what is the recovery path?
      No documented process exists. Must define before launch.

KU-4: ✅ RESOLVED — SVCURRENTCOMPANY added to ledger XML (April 2026)
      backend/tally_xml_builder.py _wrap_envelope() was missing
      <STATICVARIABLES><SVCURRENTCOMPANY> inside <REQUESTDESC>.
      Without it, Tally ignored the company context on ledger creation,
      causing new WhatsApp parties to be created without GST ledgers.
      Fix verified against official Tally XML specification.
KU-5: Cloud poller status (NEW — found in codebase audit)
      cloud-backend/services/whatsapp_poller.py contains a localhost:DESKTOP_PORT call.
      Confirm this file is NOT started anywhere in cloud-backend/main.py.
      If it is started, document why. If it is not, mark it DEPRECATED.

KU-6: ✅ RESOLVED — Socket.IO removed (April 2026)
      Was a Remote Tally Agent bridge, never a frontend feature.
      invoice_tool.py and tally_live_update.py now use direct
      localhost:9000 Tally XML path exclusively. 8 files cleaned up.

KU-7: pytest namespace collision — fix before launch
      cloud-backend tests use `from database import get_supabase_client`
      which collides with backend/database/ when running from root.
      Fix: add conftest.py files to scope test paths correctly.
      Does NOT affect production. Blocks local full-suite test runs.
```

***

## 11. STYLE & PHILOSOPHY

- Priority: speed + quality + security for the customer.
- No over-optimisation or abstractions that don't give clear value.
- Prefer simple, explicit code that is easy to debug.
- When in doubt: ask for a smaller change and confirm with the founder.
- Financial code: zero tolerance for "probably fine" — verify or stop.
