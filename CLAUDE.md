# K24 Platform – AI Agent Safety Guide

## 1. Project Identity

- Project: K24 – Hybrid accounting assistant that connects Tally on the desktop with a cloud WhatsApp + AI orchestration layer.
- Current phase: Phase 1 – Productionise an already-working system (cloud, auth, installer), not redesign it.
- Primary objective: A real user can install the desktop app, log in via deep link, and use the full flow reliably.
- Success: App works end-to-end outside my dev machine, with stable auth and installer, and no broken money/Tally logic.

## 2. Architecture Overview

- Cloud:
  - `cloud-backend/` FastAPI multi-tenant API (Supabase, WhatsApp queue, licensing).
  - Supabase Postgres (auth, tenants, whatsapp_message_queue, mappings).
  - Baileys listener for WhatsApp.
  - Frontend on Vercel (Next.js).
- Desktop:
  - `backend/` FastAPI sidecar, talks to Tally via XML on localhost.
  - SQLite `k24_shadow.db` as local mirror of Tally.
  - Tauri desktop wrapper around frontend.
- Main data flow:
  - WhatsApp → Baileys → Cloud webhook → Supabase queue → Desktop poller → Tally XML → local DB updates → optional response via cloud.

## 3. CRITICAL: Do Not Touch Zones

### 3.1 Tally XML & Money Logic (ASK FOUNDER FIRST)

These files are extremely sensitive. Do not modify them without explicit instruction from the founder.

- `backend/tally_connector.py` – Tally XML API client.
- `backend/tally_xml_builder.py` – Voucher/ledger XML generation.
- `backend/tally_golden_xml.py` – Golden XML templates.
- `backend/services/tally_operations.py` – Workflows that push vouchers to Tally.
- Rule:
  - If you think any of these must change, STOP and ask: "Do you want to change Tally XML / money logic here?" and wait for explicit approval.

### 3.2 Authentication & Deep Link (REVIEW REQUIRED)

Auth is allowed to be fixed, but never silently redesigned.

- `backend/auth.py`
- `cloud-backend/routers/auth.py`
- `backend/middleware/tenant_context.py`
- `frontend/src/middleware.ts`
- `frontend/src/lib/supabase/server.ts`
- Rule:
  - You may fix concrete bugs, wiring problems, and MCPS/tool integration.
  - You may not change the overall auth model (Supabase + JWT + deep link) without an approved plan.
  - For any auth/deeplink change: add tests + run a real login/deeplink flow.

### 3.3 Multi-Tenant Isolation & Encryption

- `backend/database/__init__.py` (TenantMixin, models).
- `backend/database/encryption.py` (field-level encryption).
- `backend/routers/whatsapp.py` – `identify_user_by_phone` and mappings.
- Supabase RLS policies in `backend/database/phase*_schema.sql`.
- Rule:
  - Every DB write must be scoped to `tenant_id`.
  - Never remove or bypass tenant filters or RLS checks.

### 3.4 Production Config & Secrets

- Any `.env` files.
- `frontend/src-tauri/tauri.conf.json` (signing, URLs).
- Dockerfiles, Github Actions workflows.
- Rule:
  - Do not hardcode secrets.
  - Treat env values as opaque; do not print them or expose them in logs.

## 4. Safe to Modify Zones (Preferred Work Area)

- Cloud WhatsApp flow:
  - `cloud-backend/routers/whatsapp_cloud.py`
  - `cloud-backend/services/tenant_routing.py` (extracted from backend)
  - `cloud-backend/database/supabase_client.py`
- Cloud message queue:
  - Supabase migrations for `whatsapp_message_queue`, related services.
- Desktop poller and glue:
  - `backend/services/whatsapp_poller.py` (new)
  - Desktop startup wiring in `backend/desktop_main.py` (non-auth sections).
- Tests and verification:
  - `tests/**`, `test_*.py`, `verify_*.py`.
- UI that does not affect auth:
  - `frontend/src/components/**`
  - `frontend/src/app/**/page.tsx`

## 5. Current Phase Focus

Phase 1: make the existing working system production-ready.

- Stabilise cloud WhatsApp queue (Supabase) and desktop poller.
- Move the right WhatsApp + tenant routing logic into `cloud-backend/`.
- Fix auth + deep link for desktop login and device licensing.
- Make Tauri installer reliable: install app, auto-start backend, and connect to cloud.

Out of scope for now:

- Changing Tally XML or financial algorithms.
- Multi-company features.
- Full UI redesign or new big product areas.

## 6. Builder + MCPS Rules

- Builder may:
  - Use MCPs/tools for Supabase, Vercel, Railway, logs, and DB inspection.
  - Fix end-to-end issues across desktop + cloud as long as they stay within allowed files.
- For any change touching:
  - Tally XML, money logic, or sensitive auth/deeplink code,
  - Builder must propose the change and ask for founder approval before editing code.

## 7. Testing & Verification

For every non-trivial change:

1. **Tests**
   - Add or update tests in `tests/` or appropriate `test_*.py` files.
   - For WhatsApp flow: cover queue insert, poll, complete, and tenant isolation.
2. **Run**
   - Run the relevant `pytest` subset and document exact commands + results.
3. **End-to-End Check**
   - Simulate at least one realistic flow (e.g., WhatsApp message through to desktop poller).
   - For auth changes: perform a real login + deep link through the desktop app / frontend.
4. **Done definition**
   - Change is within allowed scope.
   - Tests pass.
   - One real-flow check is successful and described.

## 8. Style & Philosophy

- Priority: speed + quality + security for the customer.
- No over-optimisation or big abstractions that don't give clear value.
- Prefer simple, explicit code that is easy to debug.
- When in doubt: ask for a smaller change and confirm with the founder.
