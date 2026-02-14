# M5 – Production Hardening: Execution Plan

**Status**: 40% Complete (Sentry Monitoring integrated)
**Objective**: Prepare K24 for production release by adding monitoring, creating automated smoke tests, and validating in a staging environment.

---

## ✅ Completed Items

### 1. Sentry Monitoring
- **Implementation**:
  - `cloud-backend/main.py`: Initializes Sentry SDK with FastAPI integration if `SENTRY_DSN` is present.
  - `backend/api.py`: Initializes Sentry SDK for desktop backend if `SENTRY_DSN` is present.
- **Result**:
  - Application captures unhandled exceptions and performance traces.
  - Environment specific monitoring via `ENV` variable (production/development).
- **Action Required**:
  - Set `SENTRY_DSN` environment variable in Railway (for Cloud).
  - (Optional) Set `SENTRY_DSN` in desktop environment for crash reporting.

---

## 🚀 Remaining Tasks

### 2. Create Smoke Test Script (High Priority)
A script to verify the critical "WhatsApp → Cloud → Desktop → Tally" loop.

- **File**: `tests/smoke_test.py`
- **Logic**:
  1. **Direct Injection**: Insert a test message into Supabase `whatsapp_message_queue` (mimicking a webhook).
  2. **Verify Polling**: Wait for desktop to pick it up (status changes to `processing`).
  3. **Verify Completion**: Wait for status to change to `delivered` or `failed`.
  4. **Verify Tally**: (Optional/Advanced) Query Tally API to ensure voucher/ledger was created.
- **Usage**:
  ```bash
  python tests/smoke_test.py --env staging --tenant test_tenant_id
  ```

### 3. Staging Environment Setup
Create a safe playground to run smoke tests before touching production data.

- **Cloud Deployment**:
  - Deploy `cloud-backend` to a separate Railway service (or same service with `ENV=staging`).
  - Use a separate Supabase project OR a separate schema/tenant in the existing project.
- **Desktop Config**:
  - Configure a local desktop instance to point to the staging cloud URL.
  - `backend/config/cloud.json` -> `https://k24-staging.up.railway.app` (example).

### 4. End-to-End Validation
Run the full loop with a real device (if possible) or the smoke test script.

- **Steps**:
  1. Deploy Staging Cloud.
  2. Point local Desktop App to Staging Cloud.
  3. Run `tests/smoke_test.py`.
  4. Verify Sentry captures any forced errors (e.g., stopping the Tally connector).

---

## 📋 Implementation Checklist

- [x] **Task 1**: Sentry Integration (Code Complete)
- [ ] **Task 2**: `tests/smoke_test.py` creation
- [ ] **Task 3**: Railway Staging Environment URL
- [ ] **Task 4**: Verify Sentry in Railway Dashboard

## 📝 Configuration Updates

**Railway Variables (Cloud)**:
```env
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
ENV=production
```

**Desktop Variables (Local/Prod)**:
```env
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
ENV=production
```
