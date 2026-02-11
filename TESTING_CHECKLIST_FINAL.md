# K24.ai FINAL Pre-Production Testing Checklist

**Version:** 1.0.0
**Date:** 2026-01-29
**Status:** DRAFT
**Tester:** QA Team

SUCCESS CRITERIA: All CRITICAL and HIGH priority tests must pass. 95% of MEDIUM priority tests must pass.

---

## 1. SYSTEM ARCHITECTURE VERIFICATION

### 1.1 Backend Endpoints (FastAPI)
- [ ] **Auth**: `/api/auth/login`, `/api/auth/register`, `/api/auth/me`, `/api/auth/setup-company`
- [ ] **Agent**: `/api/v1/agent/chat` (WebSocket/Stream)
- [ ] **Dashboard**: `/dashboard/stats`, `/dashboard/receivables`, `/dashboard/cashflow`, `/dashboard/stock-summary`
- [ ] **Vouchers**: `/api/vouchers/`, `/api/vouchers/{id}`
- [ ] **Inventory**: `/api/inventory/items`, `/api/inventory/stock`
- [ ] **Ledgers**: `/api/ledgers/`, `/api/ledgers/{id}`
- [ ] **Reports**: `/api/reports/daybook`, `/api/reports/trial-balance`
- [ ] **Settings**: `/api/settings/whatsapp`, `/api/settings/tally`

### 1.2 Frontend Pages (Next.js App Router)
- [ ] **Public**: `/login`, `/register`, `/forgot-password`, `/reset-password`
- [ ] **Protected**: `/` (Dashboard)
- [ ] **Vouchers**: `/vouchers`, `/vouchers/create`, `/vouchers/[id]`
- [ ] **Inventory**: `/inventory`, `/items`, `/items/[id]`
- [ ] **Parties**: `/parties` (Customers/Suppliers)
- [ ] **Reports**: `/reports`, `/daybook`
- [ ] **Settings**: `/settings`, `/onboarding`

### 1.3 Third-Party Integrations
- [ ] **Tally Prime**: Localhost 9000 (XML Interface)
- [ ] **Supabase**: PostgreSQL DB, Auth, Realtime
- [ ] **Gemini AI**: Google GenAI API (Flash 2.0)
- [ ] **WhatsApp (Baileys)**: Local Node.js Service / WhatsApp Web

### 1.4 AI Agents & Workflows
- [ ] **Main Agent**: `LangGraphOrchestrator` (Conversational)
- [ ] **Invoice Extractor**: `GeminiExtractor` (Vision API)
- [ ] **Tally Sync Agent**: Background Service (5s Interval)
- [ ] **WhatsApp Listener**: Message Batching & Routing

---

## 2. ENDPOINT TESTING

### 2.1 Auth Endpoints

**Test ID**: EP-AUTH-001
**Component**: Login (Hybrid)
**Steps**:
1. POST `/api/auth/login`
2. Payload: `{"email": "kittu@krishasales.com", "password": "password123"}`
**Expected Result**: 200 OK. Body includes `access_token` and `user` object. System checks Supabase first, then falls back to Local DB.
**Status**:

**Test ID**: EP-AUTH-002
**Component**: Register
**Steps**:
1. POST `/api/auth/register`
2. Payload: `{"email": "new@test.com", "password": "pass", "full_name": "Test User", "company_name": "Test Inc"}`
**Expected Result**: 200 OK. Creates User in Supabase AND Local DB. Returns Token.
**Status**:

### 2.2 Dashboard Endpoints

**Test ID**: EP-DASH-001
**Component**: Dashboard Stats (Tally Online)
**URL**: GET `/dashboard/stats`
**Steps**:
1. Ensure Tally is RUNNING.
2. Call Endpoint with Valid Token.
**Expected Result**: 200 OK. Body: `{"sales": 12345, "source": "tally", ...}`. Response < 200ms.
**Status**:

**Test ID**: EP-DASH-002
**Component**: Dashboard Stats (Tally Offline)
**URL**: GET `/dashboard/stats`
**Steps**:
1. CLOSE Tally Application.
2. Call Endpoint with Valid Token.
**Expected Result**: 200 OK. Body: `{"sales": 12345, "source": "database", ...}`. No 500 Error.
**Status**:

### 2.3 Agent Endpoints

**Test ID**: EP-AGENT-001
**Component**: Chat Stream
**URL**: POST `/api/v1/agent/chat`
**Steps**:
1. Payload: `{"thread_id": "uuid-123", "message": "Show me sales for today"}`
2. Consume Streaming Response (NDJSON).
**Expected Result**: 200 OK. Stream of event objects: `{"type": "thought", ...}`, `{"type": "message", "content": "Sales are..."}`.
**Status**:

---

## 3. FEATURE TESTING

### 3.1 Authentication & Onboarding

**Test ID**: FEAT-AUTH-001
**Component**: Password Reset Flow
**Steps**:
1. Click "Forgot Password" on login screen.
2. Enter email.
3. Check email for Supabase link.
4. Click link -> Redirect to `/reset-password`.
5. Enter new password.
**Expected Result**: Password updates in Supabase AND Local DB. User can login with new password immediately.
**Status**:

### 3.2 Dashboard & Visualization

**Test ID**: FEAT-DASH-001
**Component**: GST Summary Placeholder
**Steps**:
1. Go to Dashboard.
2. Locate GST methods or card.
**Expected Result**: Should NOT show hardcoded "18%" calculation. Should display accurate Tally data OR "0.00" / Placeholder if not available.
**Status**:

### 3.3 Smart Invoice Extraction

**Test ID**: FEAT-INV-001
**Component**: Complex Invoice (8+ Items)
**Steps**:
1. Upload/Send invoice image with > 8 line items via WhatsApp.
2. Wait for processing.
**Expected Result**:
- All items extracted.
- Units defaulted to "Kgs" if missing.
- Subtotal matches sum of items.
- Confidence score > 0.90.
**Status**:

### 3.4 WhatsApp Integration

**Test ID**: FEAT-WA-001
**Component**: Smart Batching
**Steps**:
1. Send 10 invoice images within 5 seconds from same number.
2. Observe logs and response.
**Expected Result**:
- System enters "Batch Mode".
- Only 1 "Processing batch..." acknowledgement sent.
- All 10 images processed in parallel.
- Single summary report sent at the end.
**Status**:

---

## 4. INTEGRATION TESTING

### 4.1 Tally Integration

**Test ID**: INT-TALLY-001
**Component**: XML Injection (Sales Voucher)
**Steps**:
1. Create Sales Voucher in K24 Web UI.
2. Save.
3. Check Tally "Daybook".
**Expected Result**: Voucher appears in Tally instantly (if online). Fields match exactly: Date, Party, Items, Quantity, Rate, Amount.
**Status**:

**Test ID**: INT-TALLY-002
**Component**: Data Sync (Tally -> Supabase)
**Steps**:
1. Create Voucher in Tally directly.
2. Wait 10 seconds.
3. Refresh K24 Dashboard.
**Expected Result**: New voucher amount reflected in Dashboard Sales figures via Background Sync.
**Status**:

### 4.2 Supabase Integration

**Test ID**: INT-SUPA-001
**Component**: Offline/Online Sync
**Steps**:
1. Disconnect Internet.
2. Create Voucher in Local K24.
3. Reconnect Internet.
**Expected Result**: Voucher syncs to Supabase Cloud automatically on reconnection (if configured) or via scheduled job. *Note: Verify current sync implementation scope.*
**Status**:

---

## 5. AI AGENT TESTING

### 5.1 Intent Recognition

**Test ID**: AI-INT-001
**Component**: Vague Requests
**Input**: "How is business?"
**Expected Result**: Agent queries Dashboard Stats tool and summarizes Sales, Receivables, and Cash flow. Tone is professional.
**Status**:

**Test ID**: AI-INT-002
**Component**: Specific Action
**Input**: "Create invoice for Ramesh for 10kg Sugar at 40"
**Expected Result**:
- Agent extracts: Party="Ramesh", Item="Sugar", Qty=10, Rate=40.
- Agent Drafts Voucher.
- Agent asks for confirmation before saving.
**Status**:

### 5.2 Error Handling & Interrupts

**Test ID**: AI-ERR-001
**Component**: Missing Information
**Input**: "Create invoice for Ramesh"
**Expected Result**: Agent asks: "What items would you like to add for Ramesh?" (Does NOT fail/hallucinate).
**Status**:

**Test ID**: AI-ERR-002
**Component**: Human Approval
**Input**: "Delete voucher #123"
**Expected Result**: Agent pauses workflow. Returns: `"Do you really want to delete voucher #123? Type 'yes' to proceed."`
**Status**:

---

## 6. DATABASE & SYNC TESTING

**Test ID**: DB-SYNC-001
**Component**: Schema Consistency
**Steps**:
1. Verify `user_profiles` table exists in Supabase.
2. verify `subscriptions` table exists.
3. Check RLS policies are enabled.
**Expected Result**: Schema matches `SUPABASE_PRODUCTION_SCHEMA.md`. RLS active.
**Status**:

**Test ID**: DB-SYNC-002
**Component**: Tally Ledger Mapping
**Steps**:
1. Rename Ledger in Tally.
2. Trigger Sync.
**Expected Result**: K24 DB updates Ledger Name to match Tally. UUID remains same (if possible) or handled gracefully.
**Status**:

---

## 7. SECURITY & AUTHENTICATION

**Test ID**: SEC-001
**Component**: RLS Violation Check
**Steps**:
1. Login as User A.
2. Attempt to fetch User B's invoices via API ID manipulation.
**Expected Result**: 403 Forbidden or Empty List. RLS prevents access.
**Status**:

**Test ID**: SEC-002
**Component**: API Rate Limiting
**Steps**:
1. Send 100 requests to `/api/v1/agent/chat` in 10 seconds.
**Expected Result**: 429 Too Many Requests (if configured) or handled without crashing server.
**Status**:

---

## 8. PRODUCTION READINESS CHECKLIST

### 8.1 Environment & Config
- [ ] `.env` file exists and contains NO default passwords.
- [ ] `SUPABASE_URL` and `SUPABASE_KEY` are set.
- [ ] `GOOGLE_API_KEY` is valid for Gemini 2.0.
- [ ] `TALLY_URL` defaults to `http://localhost:9000`.

### 8.2 Logging & Monitoring
- [ ] Backend logs print to stdout/file.
- [ ] Tally Connection errors are logged but do NOT crash the app.
- [ ] Agent thoughts are logged for debugging.

### 8.3 Deployment
- [ ] `requirements.txt` is frozen and up to date.
- [ ] Frontend builds without linting errors (`npm run build`).
- [ ] Docker containers (if used) spin up correctly.
- [ ] Database backup taken before deployment.

### 8.4 Rollback Plan
- [ ] Manual DB Restore script ready.
- [ ] Previous Stable Build (v0.9) archived and ready to run.

