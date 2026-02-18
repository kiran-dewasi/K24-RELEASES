# K24 Auth Flow Investigation Report
> Generated: 2026-02-18 | Status: Root cause identified

---

## TL;DR — What's Broken and Why

The login button calls `POST /api/auth/login` **directly via `fetch()`** to `http://localhost:8000`.
The "Failed to fetch" error means **the local Python backend at `localhost:8000` is not running** when the user tries to log in.

There is **NO web redirect + deep link pattern** in the login page. That pattern only exists for the separate **device activation flow** (`ConnectDevice.tsx` → browser → `k24://` deep link).

---

## 1. What the Sign In Button Actually Does

**File:** `frontend/src/app/login/page.tsx`

```ts
// Line 27 — the actual call
const response = await apiClient("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
});
```

**`apiClient`** is defined in `frontend/src/lib/api.ts` (line 203):

```ts
export async function apiClient(endpoint: string, options: RequestInit = {}): Promise<Response> {
    const url = endpoint.startsWith('http') ? endpoint : `${DEV_API_URL}${endpoint}`;
    // ...
    const res = await fetch(url, { ...options, headers });
    return res;
}
```

Where `DEV_API_URL` is:
```ts
const DEV_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

### Conclusion
- ✅ It is a **direct POST to `/api/auth/login`** — no browser redirect, no OAuth, no deep link.
- ✅ The target URL is `http://localhost:8000/api/auth/login`.
- ❌ There is **no `window.open()`, no `Tauri shell.open()`, no `k24://` protocol** in the login page.

---

## 2. The Two Separate Auth Flows (They Are Different Things)

### Flow A: Login Page (`/login`) — BROKEN
```
User fills email/password
  → apiClient() → fetch("http://localhost:8000/api/auth/login")
  → Backend returns JWT token
  → Token stored in localStorage + cookie
  → router.push("/")
```
**Status: BROKEN** — `localhost:8000` is not running.

### Flow B: Device Activation (`ConnectDevice.tsx`) — Deep Link
```
User clicks "Connect via Browser"
  → Desktop generates device_id
  → Opens browser to https://k24.ai/auth/desktop?device_id=...
  → Web page calls POST /api/devices/register
  → Web page redirects browser to k24://auth/callback?license_key=...
  → Tauri deep-link plugin intercepts k24:// URL
  → Desktop validates license key with local backend
```
**Status: Separate feature, not related to the login page.**

---

## 3. Exact Error Causing "Failed to fetch"

The error chain is:

```
fetch("http://localhost:8000/api/auth/login")
  → ERR_CONNECTION_REFUSED  (backend not running)
  → fetch() throws TypeError: Failed to fetch
  → catch(err) → setError(err.message)
  → UI shows "Failed to fetch" + infinite spinner
```

The **infinite buffering** is because `setLoading(true)` is set before the call, and when `fetch()` throws (network error, not HTTP error), the `finally` block does set `setLoading(false)` — but the error message "Failed to fetch" is a browser-native `TypeError`, not a user-friendly message.

### Why is `localhost:8000` not running?

Looking at `commands.rs` (the Tauri Rust layer):

```rust
#[cfg(debug_assertions)]  // In DEV mode
{
    let auth = BackendAuth { port: 8000, ... };
    // Just stores port 8000 — does NOT actually start any process
    // Assumes backend is already running externally
}
```

In **development mode** (`npx tauri dev`), Tauri does NOT start the Python backend. It assumes you have manually started it. The Python backend (`uvicorn backend.main:app --port 8000`) must be running separately.

---

## 4. Deep Link Configuration — What IS Configured

**File:** `frontend/src-tauri/tauri.conf.json`

```json
"plugins": {
    "deep-link": {
        "desktop": {
            "schemes": ["k24"]
        }
    },
    "shell": {
        "open": true
    }
}
```

- ✅ `k24://` protocol IS registered as a deep link scheme.
- ✅ `shell.open` is enabled (allows opening browser URLs from Tauri).
- ❌ There is **no deep link handler in the login page** — it's only for device activation.

---

## 5. Backend Auth Endpoint — What It Expects

**File:** `backend/routers/auth.py` — `POST /api/auth/login`

**Request:**
```json
{ "email": "string", "password": "string" }
```

**Response:**
```json
{
    "access_token": "JWT_TOKEN",
    "token_type": "bearer",
    "user": { "id": 1, "email": "...", "username": "...", "tenant_id": "..." }
}
```

**What it does:**
1. Tries Supabase auth first (cloud master)
2. Falls back to local SQLite user check
3. Creates local user stub if Supabase login succeeds but user doesn't exist locally
4. Returns a locally-signed JWT token

**CORS:** The backend is FastAPI. CORS is configured in `backend/main.py` — needs to be checked, but since it's `localhost:8000` → `localhost:3000`, CORS should be fine if configured correctly.

---

## 6. API URL Configuration

| Location | Variable | Value |
|---|---|---|
| `frontend/src/lib/api.ts` | `DEV_API_URL` | `process.env.NEXT_PUBLIC_API_URL \|\| 'http://localhost:8000'` |
| Root `.env` | `NEXT_PUBLIC_API_URL` | **NOT SET** (no such variable in `.env`) |
| Root `.env` | `NEXT_PUBLIC_SUPABASE_URL` | `https://gxukvnoiyzizienswgni.supabase.co` |
| `frontend/.env` | — | **File does not exist** |

**Critical finding:** `NEXT_PUBLIC_API_URL` is **not set** in any `.env` file. This means the frontend always falls back to `http://localhost:8000`. This is correct for local dev, but the backend must be running.

---

## 7. The `apiRequest` vs `apiClient` Split (Important!)

There are **two different code paths** in `api.ts`:

### `apiRequest()` — Used by `UserContext` (for `/api/auth/me`)
```ts
if (isTauri()) {
    // Uses Tauri invoke('backend_request') → Rust → localhost:8000
} else {
    // Direct fetch to localhost:8000
}
```

### `apiClient()` — Used by the Login Page (for `/api/auth/login`)
```ts
// ALWAYS does direct fetch — does NOT check isTauri()
const res = await fetch(url, { ...options, headers });
```

**This is a bug in the login page.** The login page uses the legacy `apiClient()` which always does a direct `fetch()` even inside Tauri. It should use `apiRequest()` instead, which would route through the Tauri Rust layer (`invoke('backend_request')`).

However, even with `apiRequest()`, in dev mode the Rust layer just points to `localhost:8000`, so the backend still needs to be running.

---

## 8. Original Design vs Current Implementation

### Original Design (per `DOCS_WEB_AUTH_SPEC.md` and `DOCS_DEVICE_AUTH_FLOW.md`)

The **web redirect + deep link** pattern was designed for **device activation only**:
```
Desktop App → Opens browser to https://k24.ai/auth/desktop?device_id=...
  → User logs in on web
  → Web calls POST /api/devices/register
  → Web redirects to k24://auth/callback?license_key=...
  → Desktop receives license key
```

The **login page** was always designed as a **direct API login** to the local backend.

### Current Implementation

The login page correctly implements direct API login. The problem is purely operational:
- The Python backend at `localhost:8000` is not running when `npx tauri dev` is started.

---

## 9. Summary of Issues

| Issue | Severity | Root Cause |
|---|---|---|
| "Failed to fetch" on login | 🔴 Critical | `localhost:8000` Python backend not running |
| Login uses `apiClient()` not `apiRequest()` | 🟡 Medium | Legacy function bypasses Tauri routing |
| `NEXT_PUBLIC_API_URL` not in `.env` | 🟡 Medium | Falls back to localhost correctly, but undocumented |
| No `.env` file in `frontend/` directory | 🟡 Medium | Next.js won't pick up root `.env` for `NEXT_PUBLIC_*` vars |

---

## 10. How to Fix "Failed to fetch" Right Now

### Option A: Start the backend manually (quickest)
```powershell
# In a separate terminal, from the project root:
cd c:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare
venv\Scripts\activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Then the login page will work.

### Option B: Create `frontend/.env.local` with the API URL
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```
This doesn't fix the backend not running, but documents the config properly.

### Option C: Fix the login page to use `apiRequest()` instead of `apiClient()`
Change `login/page.tsx` line 27:
```ts
// Before (uses legacy fetch):
const response = await apiClient("/api/auth/login", { method: "POST", ... });

// After (uses Tauri-aware routing):
const data = await apiRequest("/api/auth/login", "POST", { email, password });
```
This is cleaner but still requires the backend to be running in dev mode.

---

## 11. Is There a Web Redirect + Deep Link for Login?

**No.** The `/auth/desktop` page (the web redirect + deep link flow) is:
- A **separate route** (`/auth/desktop/page.tsx`) — but it may not even exist yet (it's documented in `DOCS_WEB_AUTH_SPEC.md` as a spec, not necessarily implemented)
- Used for **device activation**, not for regular login
- Requires the web platform to be deployed at `https://k24.ai`

The regular login page (`/login`) is a **standard email/password form** that POSTs directly to the local Python backend.
