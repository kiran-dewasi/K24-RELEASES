# K24 Implementation Plan – Phase 1

**Goal**: A real customer can install the desktop app, log in via deep link from the web, and use the WhatsApp → Cloud → Desktop → Tally flow reliably.

**Status as of 2026-02-11**: ~35% complete (detailed gap analysis below)

---

## 1. Current Reality (Updated)

### ✅ What's Working
- **Desktop Backend**: Fully functional Tally XML integration, sync engine, local SQLite
- **Frontend**: Complete UI (login, onboarding, dashboard, reports)
- **Auth System**: JWT authentication, Supabase integration, role-based access
- **Tauri Config**: Desktop app structure, deep-link plugin configured
- **Cloud Backend Structure**: FastAPI cloud-backend directory with routers
- **Database Schemas**: Supabase migrations for tenants, multi-tenancy, WhatsApp mappings

### ⚠️ Partially Working
- **Cloud Webhook**: Skeleton exists but doesn't insert to queue
- **Tauri Installer**: Config ready but backend sidecar not bundled
- **Auth Deep Link**: Plugin configured but token flow untested

### ❌ Critical Gaps (Blocking Phase 1)
1. **Tenant Routing**: Cloud webhook (`whatsapp_cloud.py` line 47) has TODO, needs to query `whatsapp_customer_mappings`
2. **Queue Insertion**: Webhook doesn't insert messages into `whatsapp_message_queue` table
3. **Desktop Poller**: `whatsapp_poller.py` doesn't exist, no polling endpoints in cloud
4. **Backend Sidecar**: Not built/bundled with Tauri installer
5. **Baileys Listener**: Deployment unclear (code location, Railway/VPS hosting)
6. **Integration Tests**: No end-to-end tests for WhatsApp → Desktop flow
7. **Deep Link Flow**: Token passing web → desktop untested with real `device_licenses` table
8. **Device Activation**: Endpoint exists but needs to use real `device_licenses` + `subscriptions` tables

---

## 2. Milestones (Strategic Implementation Order)

### M1 – Supabase WhatsApp Queue & Cloud Webhook
**Status**: 60% complete | **Priority**: CRITICAL | **Estimated**: 2-3 days

**Owner**: Builder

**Current State**:
- ✅ `whatsapp_message_queue` table EXISTS in Supabase (confirmed in schema)
  - Columns: `id`, `tenant_id`, `user_id`, `customer_phone`, `message_type`, `message_text`, `media_url`, `raw_payload`, `status`, `processed_at`, `error_message`, `created_at`
- ✅ `whatsapp_customer_mappings` table EXISTS for phone → tenant routing
  - Columns: `id`, `user_id`, `tenant_id`, `customer_phone`, `customer_name`, `client_code`, `notes`, `is_active`, `created_at`, `updated_at`
- ✅ `tenants` table EXISTS with `id`, `company_name`, `tally_company_name`, `whatsapp_number`, `license_key`
- ✅ Cloud webhook skeleton at `cloud-backend/routers/whatsapp_cloud.py`
- ❌ Tenant routing logic incomplete (TODO at line 47)
- ❌ Queue insertion not implemented

**Tasks**:

1. **Verify/Create index on queue table** (1 hour)
   - Check if index exists: `(tenant_id, status)` on `whatsapp_message_queue`
   - If missing, run in Supabase SQL Editor:
     ```sql
     CREATE INDEX IF NOT EXISTS idx_queue_tenant_status
     ON whatsapp_message_queue(tenant_id, status);
     ```
   - File: Document in `backend/database/migrations/20260211_queue_indexes.sql`

2. **Implement tenant routing in cloud webhook** (2-3 hours)
   - File: `cloud-backend/routers/whatsapp_cloud.py` line 47-58
   - Replace TODO with:
     ```python
     # Lookup tenant from customer phone
     result = supabase.table('whatsapp_customer_mappings')\
       .select('tenant_id, user_id')\
       .eq('customer_phone', message.from_number)\
       .eq('is_active', True)\
       .single()\
       .execute()

     if not result.data:
       raise HTTPException(404, "Unknown customer phone")

     tenant_id = result.data['tenant_id']
     user_id = result.data.get('user_id')
     ```
   - Handle errors: unknown phone → return 404 with helpful message

3. **Insert messages into queue** (2 hours)
   - After tenant identified, insert into `whatsapp_message_queue`:
     ```python
     queue_item = supabase.table('whatsapp_message_queue').insert({
       'tenant_id': tenant_id,
       'user_id': user_id,  # can be null
       'customer_phone': message.from_number,
       'message_type': message.message_type,
       'message_text': message.text,
       'media_url': message.media_url,
       'raw_payload': message.raw_payload or {},
       'status': 'pending'
     }).execute()

     return {
       "status": "received",
       "message_id": queue_item.data[0]['id'],
       "queued": True
     }
     ```
   - File: `cloud-backend/routers/whatsapp_cloud.py`

4. **Add Supabase client initialization** (1 hour)
   - File: `cloud-backend/main.py` or `cloud-backend/services/supabase_client.py`
   - Initialize Supabase client with env vars:
     ```python
     from supabase import create_client
     SUPABASE_URL = os.getenv('SUPABASE_URL')
     SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')  # Use service role key
     supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
     ```
   - Import in whatsapp_cloud.py

5. **Update .env.example and Railway config** (30 mins)
   - Add to `cloud-backend/.env.example`:
     ```
     SUPABASE_URL=https://your-project.supabase.co
     SUPABASE_SERVICE_KEY=your_service_role_key
     BAILEYS_SECRET=k24_baileys_secret
     ```
   - Set same vars in Railway dashboard

**Testing**:
- Unit test: Mock Supabase calls, verify routing logic
- Integration test:
  1. Insert test mapping: `INSERT INTO whatsapp_customer_mappings (tenant_id, customer_phone, is_active) VALUES ('TEST_TENANT', '+919999999999', true)`
  2. POST to `/api/whatsapp/cloud/incoming` with that phone
  3. Query `whatsapp_message_queue` → verify row inserted with correct tenant_id
  4. Repeat with different tenant → verify isolation
- Manual: Use Postman, check Supabase dashboard

**Definition of Done**:
- [ ] Index verified/created on queue table
- [ ] Cloud webhook queries `whatsapp_customer_mappings` for tenant routing
- [ ] Messages inserted into `whatsapp_message_queue` with all fields
- [ ] Returns 202 with `message_id`
- [ ] Unknown phone returns 404
- [ ] Tested with 2 tenants, verified isolation
- [ ] Railway deployment updated with Supabase env vars

---

### M2 – Desktop Poller & Job Completion
**Status**: 15% complete | **Priority**: CRITICAL | **Estimated**: 4-5 days

**Owner**: Builder

**Current State**:
- ✅ Desktop backend exists with services structure
- ✅ `whatsapp_message_queue` table ready with all needed columns (`id`, `tenant_id`, `user_id`, `customer_phone`, `message_type`, `message_text`, `media_url`, `raw_payload`, `status`, `processed_at`, `error_message`, `created_at`)
- ❌ `backend/services/whatsapp_poller.py` does NOT exist
- ❌ Cloud polling endpoint missing: `GET /api/whatsapp/jobs/{tenant_id}`
- ❌ Job completion endpoint missing: `POST /api/whatsapp/jobs/{job_id}/complete`

**Tasks**:
1. ✅ **Create cloud polling endpoint** (COMPLETED - 2026-02-12)
   - **Endpoint**: `GET /api/whatsapp/jobs/{tenant_id}`
   - **File**: `cloud-backend/routers/whatsapp_cloud.py`
   - **Security**: API key authentication via `X-API-Key` header
     - Validates against `DESKTOP_API_KEY` env var (set in Railway)
     - Returns 401 if missing/invalid
     - Prevents unauthorized polling of message queues
   - Implementation: Uses FastAPI Depends + Header validation
   - Query with atomic update:
     ```python
     # Fetch and mark as processing in one transaction
     result = supabase.rpc('poll_queue_messages', {
       'p_tenant_id': tenant_id,
       'p_limit': limit
     }).execute()
     # OR simpler: SELECT + UPDATE (needs transaction)
     ```
   - SQL function to create in Supabase:
     ```sql
     CREATE OR REPLACE FUNCTION poll_queue_messages(p_tenant_id text, p_limit int DEFAULT 10)
     RETURNS SETOF whatsapp_message_queue AS $$
       UPDATE whatsapp_message_queue
       SET status = 'processing', processed_at = now()
       WHERE id IN (
         SELECT id FROM whatsapp_message_queue
         WHERE tenant_id = p_tenant_id AND status = 'pending'
         ORDER BY created_at ASC
         LIMIT p_limit
       )
       RETURNING *;
     $$ LANGUAGE sql;
     ```
   - Response: Include all columns: `id`, `tenant_id`, `user_id`, `customer_phone`, `message_type`, `message_text`, `media_url`, `raw_payload`, `status`, `created_at`

2. **Create job completion endpoint** (2 hours)
   - **Endpoint**: `POST /api/whatsapp/jobs/{job_id}/complete`
   - **File**: `cloud-backend/routers/whatsapp_cloud.py`
   - Auth: Verify JWT
   - Request validation:
     ```python
     class JobComplete(BaseModel):
       status: Literal['delivered', 'failed']
       error_message: Optional[str] = None  # Required if status='failed'
       result_summary: Optional[str] = None
     ```
   - Update query:
     ```python
     supabase.table('whatsapp_message_queue').update({
       'status': request.status,
       'error_message': request.error_message,
       'processed_at': 'now()'  # Supabase handles server time
     }).eq('id', job_id).execute()
     ```
   - Validate: if `status='failed'`, `error_message` must be provided
   - Response: `{ "status": "ok", "job_id": "...", "processed_at": "ISO 8601" }`

3. **Create desktop poller service**
   - File: `backend/services/whatsapp_poller.py` (new)
   - Class: WhatsAppPoller
   - Method: `start_polling()` – runs in background thread
   - Poll every 10 seconds: GET /api/whatsapp/jobs/{tenant_id}
   - For each message: process via AI/Tally, then POST completion
   - Handle network errors: exponential backoff, log failures
   - Use tenant_id from current desktop auth context

4. **Integrate poller into desktop startup**
   - File: `backend/desktop_main.py` (or equivalent startup file)
   - On startup: Initialize WhatsAppPoller with tenant_id from config
   - Start polling in background thread (don't block main)
   - Graceful shutdown: stop polling when app closes

5. **Handle message processing**
   - In WhatsAppPoller: delegate to existing AI/Tally services
   - Parse message_text, extract intent, execute operations
   - Catch errors, send 'failed' status with error_message
   - Send 'delivered' status with result_summary on success

**Testing**:
- Unit test: Mock queue with 3 messages, verify poller fetches and completes
- Integration test: Insert message in Supabase, start desktop, verify processed
- Error test: Kill cloud API mid-poll, verify desktop retries gracefully
- Manual: Send WhatsApp message → verify desktop picks up → verify Tally updated

**Definition of Done**:
- [x] Cloud polling endpoint implemented and tested (✅ API key auth added)
- [ ] Cloud completion endpoint implemented and tested
- [ ] Desktop poller service created
- [ ] Poller integrated into desktop startup
- [ ] Network error handling works (tested with cloud offline)
- [ ] Full integration test passes (message → desktop → Tally)

---

### Infrastructure: Domain & URL Management Strategy

**Status**: ✅ Custom Domain Active (api.k24.ai)  
**Migration Date**: Feb 12, 2026

#### Current URL Architecture
| Service | Env Var | Production Value | Status |
|---------|---------|------------------|--------|
| cloud-backend | API_BASE_URL | https://api.k24.ai | ✅ Set |
| baileys-listener | BACKEND_URL | https://api.k24.ai | ✅ Updated |
| Desktop app (M4) | CLOUD_API_URL | TBD | ⏳ Not implemented |

#### DNS Configuration
- **Domain**: k24.ai (owned)
- **Subdomain**: api.k24.ai
- **CNAME**: api → 8dbzflwh.up.railway.app
- **TTL**: 5 minutes (fast propagation)

#### Known Issues & Resolutions

**Issue 1: Bidirectional Communication (cloud ↔ baileys)**
- **Problem**: BAILEYS_SERVICE_URL not set in Railway cloud-backend
- **Impact**: Cloud cannot call baileys for health checks or QR status
- **Priority**: Low (not needed for M1/M2)
- **Resolution**: Add to M3 or when bidirectional needed:
  - Set Railway env: `BAILEYS_SERVICE_URL=https://artistic-healing-production.up.railway.app` (or custom domain)
  - Update `cloud-backend/routers/whatsapp_cloud.py` to use this URL

**Issue 2: Desktop Cloud Config (M4 blocker)**
- **Problem**: Desktop app has no way to know production cloud URL
- **Impact**: Cannot ship installers without hardcoding URL
- **Priority**: High (blocks M4)
- **Resolution**: 
   - Create `backend/config/cloud.json`:
     ```json
     {
       "cloud_api_url": "https://api.k24.ai",
       "desktop_api_key": "<from_secure_storage>",
       "environment": "production"
     }
     ```
   - Add `backend/services/config_service.py` to read this
   - Package config.json with Tauri installer
   - Add to M4 Task 1 checklist
   - **CRITICAL**: Desktop must include `X-API-Key` header in all cloud requests

**Issue 3: Auth URLs Not Configured**
- **Problem**: Supabase Auth doesn't allow api.k24.ai redirects yet
- **Impact**: OAuth flows will fail from cloud domain
- **Priority**: Medium (needed before auth flows)
- **Resolution**: ✅ IN PROGRESS
  - Add to Supabase → Authentication → URL Configuration:
    - Site URL: https://api.k24.ai
    - Redirect URLs: https://api.k24.ai/**, k24://**

#### CORS Verification Checklist
Ensure `cloud-backend/main.py` allows:
- `https://tauri.localhost` (desktop app dev)
- `k24://*` (desktop deep links)
- `https://api.k24.ai` (production frontend if needed)

#### API Key Authentication Pattern

**Added**: 2026-02-12 (M2 Task 1)

##### Overview
Desktop-to-cloud communication uses simple API key authentication to prevent unauthorized access to the WhatsApp job polling endpoint. This is a lightweight alternative to full JWT auth for machine-to-machine communication.

##### Security Model
- **Endpoint**: `GET /api/whatsapp/jobs/{tenant_id}`
- **Header**: `X-API-Key: <value>`
- **Validation**: Server compares against `DESKTOP_API_KEY` env var
- **Failure**: Returns `401 Unauthorized` if missing/invalid

##### Implementation Details

**Cloud Backend** (`cloud-backend/routers/whatsapp_cloud.py`):
```python
def verify_desktop_api_key(x_api_key: str = Header(None)):
    """Verify that the request comes from authenticated desktop app"""
    expected_key = os.getenv("DESKTOP_API_KEY")
    if not expected_key:
        logger.error("DESKTOP_API_KEY not configured in environment")
        raise HTTPException(status_code=500, detail="Server configuration error")
    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True

@router.get("/jobs/{tenant_id}")
async def poll_whatsapp_jobs(
    tenant_id: str,
    authenticated: bool = Depends(verify_desktop_api_key)
):
    # ... polling logic
```

**Desktop Client** (to be implemented in `backend/services/whatsapp_poller.py`):
```python
import requests
from backend.services.config_service import get_cloud_url, get_api_key

headers = {
    "X-API-Key": get_api_key(),
    "Content-Type": "application/json"
}

response = requests.get(
    f"{get_cloud_url()}/api/whatsapp/jobs/{tenant_id}",
    headers=headers
)
```

##### Environment Variables

**Railway (cloud-backend)**:
- **Variable**: `DESKTOP_API_KEY`
- **Value**: Generate secure random string (e.g., `openssl rand -hex 32`)
- **Status**: ✅ Set in Railway dashboard (2026-02-12)

**Desktop App** (to be implemented):
- **Storage**: Windows DPAPI encrypted config or secure keyring
- **Config**: `backend/config/cloud.json` (template, not actual key)
- **Runtime**: Read from secure storage via `config_service.get_api_key()`

##### Why Not JWT?
For desktop polling, API key is simpler because:
1. **No user context needed**: Desktop polls for its tenant, not specific user
2. **No expiry**: Avoids refresh token complexity
3. **Easy distribution**: One key per deployment, packaged with installer
4. **Adequate security**: Endpoint only returns data for explicitly requested tenant_id

##### Migration Path
- **Phase 1**: Use single shared API key for all desktop clients
- **Phase 2** (optional): Per-tenant API keys if needed for rotation/revocation

---

### M3 – Auth, Deep Link & Device Activation
**Status**: 75% complete | **Priority**: HIGH | **Estimated**: 2-3 days

**Owner**: Builder + Tester

**Current State**:
- ✅ JWT auth in backend and cloud-backend
- ✅ Tauri deep-link plugin configured (k24:// scheme)
- ✅ Frontend login/onboarding pages
- ✅ Real Supabase tables: `device_licenses`, `subscriptions`, `users_profile`, `tenants`
- ✅ `device_licenses` table with columns: `id`, `license_key` (UNIQUE), `user_id` (FK), `tenant_id`, `device_fingerprint`, `device_name`, `status`, `activated_at`, `last_validated_at`, `created_at`
- ✅ `subscriptions` table with: `id`, `user_id` (FK), `tenant_id`, `plan`, `status`, `trial_starts_at`, `trial_ends_at`, `expires_at`
- ❌ Device activation endpoint needs to INSERT into `device_licenses` table
- ❌ Deep link token flow untested (web → k24:// → desktop)
- ❌ Desktop token storage mechanism not implemented

**Tasks**:
1. **Deep link flow is ALREADY documented** ✅
   - See: `contracts.md` section 3.1-3.3 (updated)
   - Format: `k24://activate?license_key={key}&tenant_id={id}`
   - Skip this task, move to implementation

2. **Implement device activation endpoint** (3 hours)
   - **File**: `cloud-backend/routers/devices.py`
   - **Endpoint**: `POST /api/devices/activate`
   - Request model:
     ```python
     class DeviceActivation(BaseModel):
       license_key: str  # From deep link
       device_fingerprint: str  # Generated by desktop
       device_name: Optional[str] = None
     ```
   - Process:
     1. Validate `license_key` exists and not already used:
        ```python
        existing = supabase.table('device_licenses')\
          .select('*')\
          .eq('license_key', license_key)\
          .execute()
        if existing.data:
          raise HTTPException(400, "License already activated")
        ```
     2. Get user/tenant from license (need to link license_key to user somehow - clarify with founder)
     3. Check subscription status:
        ```python
        sub = supabase.table('subscriptions')\
          .select('*')\
          .eq('user_id', user_id)\
          .eq('tenant_id', tenant_id)\
          .single()\
          .execute()
        if sub.data['status'] not in ['trial', 'active']:
          raise HTTPException(403, "Subscription expired")
        ```
     4. Insert into `device_licenses`:
        ```python
        device = supabase.table('device_licenses').insert({
          'license_key': license_key,
          'user_id': user_id,
          'tenant_id': tenant_id,
          'device_fingerprint': device_fingerprint,
          'device_name': device_name,
          'status': 'active',
          'activated_at': 'now()',
          'last_validated_at': 'now()'
        }).execute()
        ```
     5. Generate JWT with claims: `{ user_id, tenant_id, device_id }`
     6. Return tokens + subscription info
   - Response matches `contracts.md` section 3.1
   - Check if device already activated, handle limits (free trial)
   - File: `cloud-backend/routers/devices.py` (verify/complete)

3. **Implement device fingerprinting** (desktop)
   - Generate unique device ID from: machine UUID, MAC address, hostname
   - Store in Windows registry or `%APPDATA%/K24/device.json`
   - File: `backend/services/device_service.py` (new)

4. **Implement desktop token storage**
   - Store access_token, refresh_token in `%APPDATA%/K24/auth.json`
   - Encrypt with Windows DPAPI or simple encryption key
   - On startup: read tokens, validate, refresh if expired
   - File: `backend/services/token_storage.py` (new)

5. **Handle deep link in Tauri**
   - Frontend Tauri plugin: listen for k24:// URLs
   - Extract token, device_id, tenant_id from URL
   - Call desktop backend: `POST /api/auth/activate-from-deeplink`
   - Backend stores tokens via token_storage service
   - File: `frontend/src-tauri/src/main.rs` (add deep link handler)

6. **Implement token refresh on desktop**
   - Before any cloud API call: check token expiry
   - If expired: call `POST /api/auth/refresh` with refresh_token
   - Update stored tokens
   - File: `backend/middleware/auth_middleware.py` (enhance)

**Testing**:
- Unit test: Generate device fingerprint, verify consistent
- Unit test: Store/retrieve tokens, verify encryption works
- Integration test: Login on web → click deep link → verify desktop has tokens
- Manual: Fresh Windows machine → login on web → deep link opens desktop → desktop calls cloud API successfully

**Definition of Done**:
- [ ] Deep link flow documented in contracts.md
- [ ] Device activation endpoint working
- [ ] Device fingerprinting implemented
- [ ] Token storage implemented and encrypted
- [ ] Tauri deep link handler working
- [ ] Token refresh working
- [ ] Manual test: web login → deep link → desktop call succeeds

---

### M4 – Tauri Installer & Startup Experience
**Status**: 60% complete | **Priority**: HIGH | **Estimated**: 3-4 days

**Owner**: Builder + Tester/Reviewer

**Current State**:
- ✅ Tauri config with MSI/NSIS targets
- ✅ externalBin reference in tauri.conf.json
- ✅ Installer scripts (installer.ps1) exist
- ❌ Backend sidecar binary not built/bundled
- ❌ Backend auto-start mechanism unclear
- ❌ Environment config handling undefined

**Tasks**:
1. **Task 0: Desktop Cloud URL Configuration + API Key Auth** (NEW - BLOCKER)
   - Create `backend/config/cloud.json` with production URL
   - Implement `backend/services/config_service.py`:
     - Read `cloud_api_url` from config.json
     - Read `desktop_api_key` from secure storage (e.g., Windows DPAPI, keyring)
     - Fallback to localhost for dev
     - Expose via `get_cloud_url()` and `get_api_key()` methods
   - **CRITICAL**: Update `whatsapp_poller.py` to:
     - Use `config_service.get_cloud_url()`
     - Include `X-API-Key` header in ALL cloud requests:
       ```python
       headers = {
         "X-API-Key": config_service.get_api_key(),
         "Content-Type": "application/json"
       }
       ```
   - Update Tauri build config to package config.json
   - Test installer with production URL + API key
   - ✅ Ensures every tenant's desktop knows where to poll AND can authenticate

2. **Create PyInstaller spec for backend sidecar**
   - File: `backend/k24_backend.spec` (new)
   - Bundle: FastAPI app, all dependencies, Tally connectors
   - Output: `k24-backend.exe` (standalone, no Python required)
   - Test: Run .exe on machine without Python installed

2. **Build backend sidecar binary**
   - Command: `pyinstaller backend/k24_backend.spec --noconfirm`
   - Output: `backend/dist/k24-backend.exe`
   - Verify size < 100MB (use UPX compression if needed)

3. **Copy sidecar to Tauri binaries folder**
   - Windows: Copy to `frontend/src-tauri/binaries/k24-backend-x86_64-pc-windows-msvc.exe`
   - Linux: `k24-backend-x86_64-unknown-linux-gnu` (future)
   - macOS: `k24-backend-x86_64-apple-darwin` (future)
   - Tauri naming convention: {name}-{target-triple}

4. **Implement backend auto-start in Tauri**
   - File: `frontend/src-tauri/src/main.rs`
   - On app startup: spawn k24-backend.exe as child process
   - Pass config via env vars or command-line args
   - Monitor process, restart if crashes
   - On app shutdown: kill backend process gracefully

5. **Handle environment configuration**
   - Create config file: `%APPDATA%/K24/config.json`
   - Fields: TALLY_URL (default localhost:9000), CLOUD_API_URL, SUPABASE_URL
   - Desktop reads config on startup, passes to backend via env vars
   - Installer: create default config.json with sensible defaults
   - File: `backend/services/config_service.py` (new)

6. **Update installer script**
   - File: `installer.ps1` (enhance if needed)
   - Ensure: creates %APPDATA%/K24 folder, writes config.json
   - Desktop shortcut: points to Tauri .exe (not separate scripts)

**Testing**:
- Unit test: Backend .exe runs standalone (no Python installed)
- Integration test: Install on VM → launch desktop → backend starts → can call APIs
- Manual test: Fresh Windows 10 machine → run installer → double-click shortcut → app opens → Tally status shows "Online"

**Definition of Done**:
- [ ] PyInstaller spec created
- [ ] Backend sidecar built and < 100MB
- [ ] Sidecar copied to Tauri binaries folder
- [ ] Backend auto-start implemented in Tauri
- [ ] Config file handling implemented
- [ ] Installer creates config.json
- [ ] Manual test on fresh Windows machine passes

---

### M5 – Production Hardening
**Status**: 10% complete | **Priority**: MEDIUM | **Estimated**: 2-3 days

**Owner**: Tester/Reviewer

**Current State**:
- ✅ Unit tests exist for Tally sync, XML builder
- ❌ No Sentry monitoring
- ❌ No smoke test script
- ❌ No staging environment

**Tasks**:
1. **Add Sentry monitoring**
   - Cloud: Add sentry-sdk to cloud-backend/requirements.txt
   - Desktop: Add sentry-sdk to backend/requirements.txt (optional for desktop)
   - Initialize in main.py with DSN from env vars
   - Capture: exceptions, API errors, Tally connection failures

2. **Create smoke test script**
   - File: `tests/smoke_test.py` (new)
   - Test 1: Insert message directly into Supabase queue
   - Test 2: Poll for desktop to pick it up (check status='processing')
   - Test 3: Wait for completion (status='delivered')
   - Test 4: Verify Tally updated (query ledgers/vouchers)

3. **Set up staging environment**
   - Deploy cloud-backend to Railway (staging)
   - Deploy Baileys listener to VPS (staging)
   - Use Supabase staging project (separate from prod)
   - Run smoke test against staging

**Testing**:
- Run smoke test: verify passes in staging environment
- Trigger error: verify Sentry captures it
- Test with 1 real tenant (not founder's machine)

**Definition of Done**:
- [ ] Sentry configured for cloud-backend
- [ ] Smoke test script created
- [ ] Staging environment deployed
- [ ] Smoke test passes in staging
- [ ] Tested with 1 real tenant

---

## 3. Critical Path & Dependencies

### Parallel Workstreams
These can be worked on simultaneously:

**Stream A (WhatsApp Flow)**: M1 → M2 → M5
- M1 must complete before M2 (need queue table for polling)
- M2 must complete before M5 (need poller for smoke test)

**Stream B (Desktop Package)**: M3 → M4
- M3 can start immediately (independent of WhatsApp)
- M4 depends on M3 (need auth tokens before installer testing)

**Critical Bottleneck**: M1 is on critical path for WhatsApp flow
**Fastest Path to MVP**: Complete M3 + M4 first (can demo login/Tally without WhatsApp)

### Recommended Sequence
1. **Week 1**: M1 + M3 (parallel) – Core infrastructure
2. **Week 2**: M2 + M4 (parallel) – Desktop integration
3. **Week 3**: M5 + Integration testing – Production readiness

### Dependency Matrix
```
M1 (Queue)     → M2 (Poller)  → M5 (Hardening)
M3 (Auth)      → M4 (Installer)
M4 (Installer) ⟍
                  → Phase 1 Done
M2 (Poller)    ⟋
```

---

## 4. Risk Mitigation Strategies

### Risk 1: Baileys Listener Deployment Unclear
**Mitigation**:
- **Option A**: Deploy to Railway (easiest, costs ~$5/month)
- **Option B**: Deploy to DigitalOcean VPS ($6/month, more control)
- **Action**: Create `baileys-listener/` Docker container, test locally first
- **Fallback**: Use Meta WhatsApp API directly (requires Business verification)

### Risk 2: Desktop Poller Complexity
**Mitigation**:
- Start with simple 10-second polling (not websockets)
- Use `asyncio` for non-blocking polling
- Add exponential backoff for network errors
- Test offline scenario explicitly

### Risk 3: Backend Sidecar Size
**Mitigation**:
- Use PyInstaller `--onefile` mode
- Exclude unnecessary packages (matplotlib, jupyter, etc.)
- Use UPX compression (can reduce size 50%)
- Target: < 50MB final size

### Risk 4: Deep Link Testing on Fresh Machine
**Mitigation**:
- Use Windows Sandbox for testing (free, isolated)
- Document exact steps in manual test checklist
- Record screen video of successful flow
- Test on at least 2 different Windows machines

### Risk 5: Supabase RLS Performance
**Mitigation**:
- Add indexes on (tenant_id, status) for queue table
- Test with 1000+ messages in queue
- Use Supabase query analyzer to optimize
- Consider partitioning if > 100K messages

---

## 5. Rules for Work in This Phase

### DO
- ✅ Follow CLAUDE.md do-not-touch zones (Tally XML, money logic)
- ✅ Write tests for every new service/endpoint
- ✅ Test with 2+ tenants for isolation
- ✅ Use environment variables for all secrets
- ✅ Document decisions in relevant .md files

### DO NOT
- ❌ Redesign Tally XML or financial algorithms
- ❌ Touch `backend/tally_connector.py` or `tally_xml_builder.py` without founder approval
- ❌ Skip tests ("we'll add them later")
- ❌ Hardcode tenant_id or credentials
- ❌ Make changes that break existing dev setup

### Process
- Each milestone: Create subtasks → Implement → Test → Review with founder
- Before touching sensitive files (auth.py, middleware): Ask founder first
- After each milestone: Update this plan.md with actual vs estimated time
- If stuck for > 4 hours: Document blocker and ask for help

---

## 6. Definition of "Phase 1 Done"

### Success Criteria (All Must Pass)

**Installation Test** (Fresh Windows 10/11 machine):
- [ ] User downloads .msi or .exe installer
- [ ] Double-click installer → installs without errors
- [ ] Desktop shortcut created: "K24"
- [ ] No Python/Node.js installation required
- [ ] Backend sidecar starts automatically
- [ ] Time to install: < 5 minutes

**Authentication Test**:
- [ ] User opens web app → creates account
- [ ] Completes onboarding (4 steps)
- [ ] Clicks "Open Desktop App" → k24:// deep link launches
- [ ] Desktop app opens with user logged in
- [ ] Desktop can call cloud APIs (verify with /api/health call)
- [ ] Tokens persist after app restart

**Tally Integration Test**:
- [ ] User has Tally running (port 9000)
- [ ] Desktop shows "Tally: Online" status indicator
- [ ] User creates voucher in K24 → saves
- [ ] Voucher appears in Tally immediately
- [ ] User syncs from Tally → data appears in K24

**WhatsApp Flow Test** (End-to-End):
- [ ] User sends WhatsApp message to business number
- [ ] Message appears in Supabase queue (status='pending')
- [ ] Desktop polls and picks up message (status='processing')
- [ ] Desktop processes message via AI/Tally
- [ ] Desktop completes job (status='delivered')
- [ ] User receives WhatsApp reply (optional for Phase 1)
- [ ] Total time: < 30 seconds

**Multi-Tenant Test**:
- [ ] Install for Tenant A and Tenant B on separate machines
- [ ] Send WhatsApp from Customer A1 → Tenant A desktop processes
- [ ] Send WhatsApp from Customer B1 → Tenant B desktop processes
- [ ] Verify: Tenant A cannot see Tenant B's messages in Supabase
- [ ] Verify: No cross-tenant data leakage

**Subscription Test** (Optional for Phase 1):
- [ ] Free trial: 50 messages limit enforced
- [ ] After limit: Desktop shows "Upgrade" message
- [ ] Paid tier: Unlimited messages work

### Acceptance Criteria

When **all 6 tests above pass** for at least **1 real customer** (not founder's machine), Phase 1 is complete.

### Handoff to Phase 2

Phase 1 delivers:
- ✅ Working installer for Windows
- ✅ Auth + deep link flow
- ✅ Desktop ↔ Tally integration
- ✅ WhatsApp → Desktop → Tally flow
- ✅ Multi-tenant isolation

Phase 2 will add:
- Multi-company support per user
- Advanced AI features (OCR, bill parsing)
- Mobile app (React Native)
- Advanced reporting
- WhatsApp bulk operations

---

## 7. Timeline Estimate

| Milestone | Estimated | Dependencies | Owner |
|-----------|-----------|--------------|-------|
| M1 - Queue | 3-4 days | None | Builder |
| M2 - Poller | 4-5 days | M1 complete | Builder |
| M3 - Auth | 3-4 days | None | Builder + Tester |
| M4 - Installer | 3-4 days | M3 complete | Builder |
| M5 - Hardening | 2-3 days | M2, M4 complete | Tester |

**Parallel execution**: M1+M3 (week 1) → M2+M4 (week 2) → M5 (week 3)

**Total estimated time**: 15-20 days (3 weeks) with 1 full-time developer

**Buffer for unknowns**: +5 days (20%)

**Target completion**: 4 weeks from start date

---

**Last Updated**: 2026-02-13  
**Next Review**: After M1 completion  
**Status**: Plan approved, ready for implementation

**Recent Completions**:
- **M3 T2**: Device Fingerprinting – COMPLETE (commit 8cdcbda3)
- **M3 T3**: Token Storage & Encryption – COMPLETE (commit 3e693421) - Fernet encryption with device-ID-based key derivation

