# K24 Architecture: Desktop Backend vs Cloud Backend
> Analysis Date: 2026-02-18 | Status: Root cause of login bug identified

---

## THE CRITICAL BUG (Read This First)

**The previous change was WRONG.** Setting `NEXT_PUBLIC_API_URL=https://weare-production.up.railway.app` in `frontend/.env.local` pointed the login page at the **cloud backend**, which has **no auth endpoints**. That's why Railway `/docs` shows 404 for auth.

**The correct fix:** `NEXT_PUBLIC_API_URL` must point to `http://localhost:8000` (the local desktop backend), which is the only place auth endpoints exist.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    DESKTOP APP (Tauri)                          │
│                                                                 │
│  ┌─────────────────┐         ┌──────────────────────────────┐  │
│  │  Next.js UI     │ ──────► │  Desktop Backend (Python)    │  │
│  │  (frontend/)    │         │  (backend/ folder)           │  │
│  │                 │         │  Runs on: localhost:8000     │  │
│  │  Login page     │         │  Handles: Auth, Tally, AI    │  │
│  │  Dashboard      │         │  Started: AUTO by Tauri      │  │
│  └─────────────────┘         └──────────────────────────────┘  │
│          │                                                      │
│          │ (for WhatsApp cloud features only)                   │
│          ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │         Cloud Backend (Railway)                             ││
│  │         https://weare-production.up.railway.app             ││
│  │         Handles: WhatsApp queue, webhooks, device reg       ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Desktop Backend (`backend/` folder)

**Entry point:** `backend/desktop_main.py` → imports `backend.api` (which is `backend/api.py`)  
**Runs on:** `http://127.0.0.1:8000` (dev mode) or a random port (production, via Tauri sidecar)  
**Started by:** Tauri automatically on app launch (`lib.rs` line 38-49 calls `start_backend()`)

### All Routers Registered in `backend/api.py`

| Router | Prefix | Purpose |
|---|---|---|
| `auth` | `/api/auth` | **Login, register, /me** — USER AUTH LIVES HERE |
| `dashboard` | `/api` | Dashboard stats |
| `vouchers` | `/api` | Sales/purchase vouchers |
| `ledgers` | `/api` | Ledger search & profiles |
| `customers` | `/api` | Customer 360° profiles |
| `inventory` | `/api` | Stock/inventory |
| `items` | (own paths) | Item 360° profiles |
| `search` | `/api` | Smart search |
| `query` | `/api` | AI query engine |
| `compliance` | `/api` | GST compliance |
| `devices` | `/api/devices` | Device/license management |
| `contacts` | (own paths) | Contact management |
| `reports` | (own paths) | Reports |
| `operations` | (own paths) | Receipt/payment ops |
| `gst` | (own paths) | GST filing |
| `sync` | (own paths) | Tally sync |
| `bills` | (own paths) | Bills/receivables |
| `whatsapp` | (own paths) | WhatsApp (local) |
| `whatsapp_binding` | (own paths) | WhatsApp binding |
| `baileys` | (own paths) | Baileys integration |
| `agent` | (own paths) | AI agent |
| `settings` | (own paths) | User settings |
| `debug` | (own paths) | Debug tools |
| `setup` | (own paths) | Initial setup |

**Plus direct routes in `api.py`:**
- `GET /health` — health check
- `GET /api/health/tally` — Tally connection check
- `POST /api/chat` — AI chat with memory
- `GET /api/chat/{thread_id}/history`
- `GET /audit/run` — audit engine
- `POST /customer-details/`
- `GET /api/reports/outstanding`
- `GET /api/ledgers/search`

### Auth Endpoints (Desktop Only)
```
POST /api/auth/login       ← Login page calls THIS
POST /api/auth/register    ← Registration
GET  /api/auth/me          ← UserContext calls THIS
POST /api/auth/logout
```

---

## 2. Cloud Backend (`cloud-backend/` folder → Railway)

**URL:** `https://weare-production.up.railway.app`  
**Entry point:** `cloud-backend/main.py`

### Routers Registered in Cloud Backend

| Router | Prefix | Purpose |
|---|---|---|
| `devices` | `/api/devices` | Device registration for deep-link activation |
| `whatsapp_cloud` | `/api/whatsapp/cloud` | WhatsApp job queue polling |
| `webhooks` | `/api/webhooks` | Incoming WhatsApp webhooks from Meta |

**Plus direct routes:**
- `GET /` — root info
- `GET /health` — health check

### ⚠️ Auth Router is COMMENTED OUT in Cloud Backend

```python
# cloud-backend/main.py line 83:
# TODO: Uncomment these after extracting shared modules from backend/
# app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
```

**This is why Railway returns 404 for `/api/auth/login` — auth is intentionally disabled on the cloud backend.**

---

## 3. How Tauri Starts the Local Backend

**File:** `frontend/src-tauri/src/lib.rs` (lines 37-49)

```rust
// Auto-start backend on app launch
tauri::async_runtime::spawn(async move {
    match commands::start_backend(handle.clone()).await {
        Ok(result) => {
            log::info!("Backend started: {:?}", result);
            let _ = handle.emit("backend_ready", result);
        }
        Err(e) => {
            log::error!("Failed to start backend: {}", e);
            let _ = handle.emit("backend_error", e);
        }
    }
});
```

**File:** `frontend/src-tauri/src/commands.rs` (lines 50-63)

```rust
#[cfg(debug_assertions)]  // ← DEV MODE
{
    let auth = BackendAuth {
        port: 8000,           // ← Hardcoded to 8000 in dev
        session_token: session_token.clone(),
    };
    *BACKEND_STATE.lock()... = Some(auth);
    // ⚠️ Does NOT actually start any process!
    // Assumes backend is already running at localhost:8000
    return Ok(json!({"port": 8000, "mode": "development"}));
}

#[cfg(not(debug_assertions))]  // ← PRODUCTION MODE
{
    // Spawns k24-backend sidecar (compiled Python binary)
    shell.sidecar("k24-backend").args(["--port", &port, "--token", &token]).spawn()
}
```

**Key insight:** In `npx tauri dev` (debug mode), Tauri does NOT start the Python backend. It just registers port 8000 and assumes you've started it manually. In a production build, it auto-spawns the compiled sidecar.

---

## 4. Correct API URL Configuration

### For Desktop App (Login, Dashboard, AI Chat, Tally)
```
http://localhost:8000
```
This is the local Python backend. The login page MUST call this.

### For Cloud Features (WhatsApp queue polling, device registration)
```
https://weare-production.up.railway.app
```
This is only used by the WhatsApp poller and device activation flow.

---

## 5. The Bug Chain

```
Previous "fix" set:
  NEXT_PUBLIC_API_URL = https://weare-production.up.railway.app

Login page calls:
  POST https://weare-production.up.railway.app/api/auth/login

Cloud backend has NO auth router → 404 Not Found

Result: Login still broken, just with a different error
```

---

## 6. The Correct Fix

### Step 1: Revert `.env.local` to point to localhost
```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BASE_URL=http://localhost:8000
```

### Step 2: Add a separate env var for cloud features
```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BASE_URL=http://localhost:8000
NEXT_PUBLIC_CLOUD_API_URL=https://weare-production.up.railway.app
```

### Step 3: Start the Python backend manually in dev mode
```powershell
# Terminal 1: Start Python backend
cd c:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare
venv\Scripts\activate
uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Start Tauri dev (already running)
cd frontend
npx tauri dev
```

### Step 4: Fix the login page to use `apiRequest()` instead of `apiClient()`
The login page uses the legacy `apiClient()` which bypasses Tauri routing. It should use `apiRequest()` which properly routes through the Tauri Rust layer in production.

---

## 7. Endpoint Ownership Summary

| Endpoint | Desktop Backend | Cloud Backend |
|---|---|---|
| `POST /api/auth/login` | ✅ YES | ❌ NO (commented out) |
| `GET /api/auth/me` | ✅ YES | ❌ NO |
| `POST /api/auth/register` | ✅ YES | ❌ NO |
| `GET /api/devices/register` | ✅ YES | ✅ YES (different purpose) |
| `GET /api/whatsapp/cloud/jobs/{tenant_id}` | ❌ NO | ✅ YES |
| `POST /api/webhooks/whatsapp` | ❌ NO | ✅ YES |
| `POST /api/chat` | ✅ YES | ❌ NO |
| `GET /api/customers/{id}/360` | ✅ YES | ❌ NO |
| `GET /health` | ✅ YES | ✅ YES |

---

## 8. Files That Need Updating

| File | Current Value | Correct Value |
|---|---|---|
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL=https://weare-production.up.railway.app` | `NEXT_PUBLIC_API_URL=http://localhost:8000` |
| `frontend/src/app/login/page.tsx` | Uses `apiClient()` | Should use `apiRequest()` |
| WhatsApp poller config | Should use `NEXT_PUBLIC_CLOUD_API_URL` | Add this env var |
