# K24 Implementation Plan – Phase 1

Goal: A real customer can install the desktop app, log in via deep link from the web, and use the WhatsApp → Cloud → Desktop → Tally flow reliably.

---

## 1. Current Reality

- Local dev setup works end-to-end on founder's machine (terminal).
- WhatsApp flow, Tally integration, and AI pieces function in development.
- Remaining work:
  - Move and stabilise necessary pieces on cloud (Supabase, Vercel, Railway).
  - Make auth + deep link + licensing robust.
  - Package everything into a reliable Tauri installer.

---

## 2. Milestones

### M1 – Supabase WhatsApp Queue & Cloud Webhook

Owner: Planner + Builder

- Create and migrate `whatsapp_message_queue` in Supabase with RLS.
- Finalise Baileys → cloud webhook according to `contracts.md`.
- Insert messages into queue with correct `tenant_id`.
- Basic tests: insert/select with 2 tenants, ensure isolation.

### M2 – Desktop Poller & Job Completion

Owner: Builder

- Implement `GET /api/whatsapp/jobs/{tenant_id}` and completion endpoint in cloud-backend.
- Create `backend/services/whatsapp_poller.py` and integrate into `backend/desktop_main.py`.
- Poll every ~10 seconds, handle network errors gracefully.
- Tests: integration test that simulates one WhatsApp message through to desktop.

### M3 – Auth, Deep Link & Device Activation

Owner: Planner + Builder + Tester/Reviewer

- Document desired login/deep-link flow in this file + `contracts.md`.
- Make sure:
  - User logs in on web.
  - Deep link carries tokens/device info to desktop app.
  - Desktop stores tokens and can call cloud endpoints.
- Add tests and a manual checklist that runs a real login → deep link → desktop call.

### M4 – Tauri Installer & Startup Experience

Owner: Builder + Tester/Reviewer

- Ensure Tauri installer:
  - Installs desktop app cleanly.
  - Starts local backend correctly.
  - Handles environment configuration for cloud endpoints.
- Manual test:
  - Fresh Windows machine.
  - Install, login via deep link, confirm Tally connection status visible and WhatsApp jobs processing.

### M5 – Production Hardening

Owner: Tester/Reviewer

- Add monitoring hooks (e.g., Sentry) to cloud-backend and desktop where feasible.
- Write a small smoke-test script that:
  - Sends a test WhatsApp message,
  - Confirms it shows up in queue,
  - Confirms desktop picks it up.
- Run this for at least one real tenant in a staging/early-production environment.

---

## 3. Rules for Work in This Phase

- Do not redesign Tally, money logic, or core business flows that already work.
- Focus only on:
  - Cloud deployment of necessary features.
  - Auth / deep link stability.
  - Installer and startup reliability.
- All changes must be small, test-backed, and within the allowed areas of `CLAUDE.md`.

---

## 4. Definition of "Phase 1 Done"

- A new user, on a separate machine:
  - Installs the desktop app from the installer.
  - Logs in via the deep-link flow from the web.
  - Has their subscription/free-trial and message limits correctly enforced.
  - Sends a WhatsApp message / bill photo and sees it processed into Tally without manual hacks.

When this is true for at least one real customer, Phase 1 is considered complete.
