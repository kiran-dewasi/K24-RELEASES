# K24 Authentication Audit Report
> Generated: 2026-02-18 | Auditor: Antigravity

---

## Section 1: Current State of Auth Systems

### System A — Device Licensing (ConnectDevice + DeviceGuard)
**Status: 🟡 ACTIVE but BROKEN end-to-end**

| Component | File | Status |
|---|---|---|
| `DeviceGuard` | `src/components/auth/DeviceGuard.tsx` | ✅ Active, runs on `/` |
| `ConnectDevice` | `src/components/auth/ConnectDevice.tsx` | ✅ Active, renders when no license |
| `POST /api/devices/activate` | `backend/routers/devices.py:110` | 🔴 Broken — calls cloud backend which has no `/activate` endpoint |
| `POST /api/devices/register` | `backend/routers/devices.py:19` | ✅ Exists locally (but wrong target) |
| `GET /api/devices/validate` | `backend/routers/devices.py:223` | ✅ Exists, checks SQLite `DeviceLicense` table |
| Deep link `k24://auth/callback` | `ConnectDevice.tsx:49` | ✅ Listener registered via Tauri plugin |
| `k24_license_key` localStorage | `DeviceGuard.tsx:14` | ✅ Checked on every `/` load |

**Critical Bug:** `POST /api/devices/activate` (desktop backend, `devices.py:110`) calls
`cloud_url/api/devices/activate` on the Railway cloud backend. The cloud backend
(`cloud-backend/main.py`) only has a `/api/devices/register` endpoint — **there is no
`/activate` endpoint on the cloud**. This means the entire browser-based activation flow
will always return a 404/500 from the cloud.

**The web callback page** (`/auth/desktop`) calls `NEXT_PUBLIC_CLOUD_API_URL/api/devices/register`
(cloud backend) ✅ — this part is correct. The cloud backend does have `/api/devices/register`.
The problem is the **second step**: the desktop app's `POST /api/devices/activate` tries to
call a non-existent cloud endpoint.

---

### System B — Login / Signup (JWT Token Auth)
**Status: 🟢 ACTIVE and FUNCTIONAL**

| Component | File | Status |
|---|---|---|
| Login page | `src/app/login/page.tsx` | ✅ Active |
| Signup page | `src/app/signup/page.tsx` | ✅ Active |
| `POST /api/auth/login` | `backend/routers/auth.py:213` | ✅ Working — hybrid Supabase + local |
| `POST /api/auth/register` | `backend/routers/auth.py:56` | ✅ Working — hybrid Supabase + local |
| `GET /api/auth/me` | `backend/routers/auth.py:377` | ✅ Working |
| `k24_token` localStorage | `login/page.tsx:53` | ✅ Stored on login |
| `k24_user` localStorage | `login/page.tsx:55` | ✅ Stored on login |
| Cookie `k24_token` | `login/page.tsx:58` | ✅ Set for server-side guard |
| Token in `apiRequest()` | `src/lib/api.ts:45` | ✅ Sent as `Authorization: Bearer` |

**Login flow works:** Email + password → Supabase auth (primary) → local SQLite sync →
JWT returned → stored in localStorage + cookie → redirect to `/`.

---

### System C — UserContext + AuthGuard
**Status: 🟢 ACTIVE and FUNCTIONAL**

| Component | File | Status |
|---|---|---|
| `UserProvider` | `src/contexts/UserContext.tsx` | ✅ Active, wraps all protected routes |
| `AuthGuard` | `src/components/AuthGuard.tsx` | ✅ Active, redirects to `/login` if no user |
| `GET /api/auth/me` call | `UserContext.tsx:61` | ✅ Called on mount if `k24_token` exists |
| Redirect to `/login` | `AuthGuard.tsx:22` | ✅ Fires when `!loading && !user` |
| Offline cache fallback | `UserContext.tsx:74` | ✅ Falls back to `k24_user` localStorage |

**Works correctly:** If `k24_token` is missing → `loading=false, user=null` immediately →
`AuthGuard` redirects to `/login`. If token exists → calls `/api/auth/me` → sets user.

---

### System D — Subscription / Tenant Validation
**Status: 🔴 DORMANT — Not enforced anywhere in frontend**

| Component | File | Status |
|---|---|---|
| `GET /api/auth/subscription` | `backend/routers/auth.py:547` | ✅ Endpoint exists |
| Frontend subscription check | anywhere in `src/` | ❌ Never called |
| `trial_ends_at` enforcement | anywhere in `src/` | ❌ Not implemented |
| `subscription_status` check | anywhere in `src/` | ❌ Not implemented |
| `tenant_config` query | anywhere in `src/` | ❌ Not implemented |

The subscription endpoint exists on the backend but **zero frontend components call it**.
Expired subscriptions are not blocked. Any user with a valid JWT can access all features
regardless of subscription status.

---

## Section 2: Execution Order (What Happens When App Opens)

### Route: `/` (Dashboard) — Fresh device, no localStorage

```
1. RootLayout (layout.tsx:17)
   └── ClientLayout (ClientLayout.tsx:12)
       └── pathname = "/" → NOT a public page
       └── UserProvider (UserContext.tsx:44)
           │  → fetchUser() called
           │  → localStorage.getItem("k24_token") → null
           │  → setUser(null), setLoading(false) immediately
           └── AuthGuard (AuthGuard.tsx:14)
               │  → loading=false, user=null
               │  → useEffect fires: router.replace("/login")  ← REDIRECT #1
               └── DeviceGuard (page.tsx:9)  ← NEVER REACHED
                   └── [would check k24_license_key]
```

**Result:** User is redirected to `/login` by `AuthGuard` BEFORE `DeviceGuard` even runs.
The ConnectDevice screen is **never shown** on a fresh device because `AuthGuard` wins first.

---

### Route: `/` (Dashboard) — Has `k24_token` but no `k24_license_key`

```
1. UserProvider → fetchUser()
   → k24_token EXISTS → calls GET /api/auth/me
   → Returns user data → setUser(user), setLoading(false)

2. AuthGuard
   → loading=false, user=user (not null)
   → No redirect. Renders children ✅

3. DeviceGuard (page.tsx:9)
   → checkLicense() → localStorage.getItem("k24_license_key") → null
   → setIsAuthorized(false)
   → Renders <ConnectDevice /> ← DEVICE GATE SHOWN
```

**Result:** ConnectDevice screen is shown. User must activate device.

---

### Route: `/` (Dashboard) — Has both `k24_token` AND `k24_license_key`

```
1. UserProvider → user loaded ✅
2. AuthGuard → user exists, no redirect ✅
3. DeviceGuard → license found → setIsAuthorized(true) ✅
4. DashboardClient renders ✅
```

**Result:** Dashboard loads normally.

---

### Route: `/login` — Any state

```
1. ClientLayout → pathname.startsWith("/login") → isPublicPage = true
2. Returns <>{children}</> directly — NO UserProvider, NO AuthGuard, NO DeviceGuard
3. Login page renders
```

**Result:** Login page always accessible. No auth checks at all.

---

### Conflict Map

```
CONFLICT #1: AuthGuard vs DeviceGuard — ORDER MATTERS
  - AuthGuard runs FIRST (wraps all protected routes via ClientLayout)
  - DeviceGuard runs SECOND (only on "/" via page.tsx)
  - If no JWT token → AuthGuard redirects to /login → DeviceGuard never runs
  - ConnectDevice is UNREACHABLE without a JWT token

CONFLICT #2: Two separate auth tokens
  - k24_token (JWT) → controls UserContext/AuthGuard
  - k24_license_key → controls DeviceGuard
  - They are INDEPENDENT. A user can have one without the other.
  - No code links them together.

CONFLICT #3: /api/devices/activate endpoint mismatch
  - ConnectDevice calls: POST http://127.0.0.1:8000/api/devices/activate
  - That endpoint (devices.py:110) then calls: cloud_url/api/devices/activate
  - Cloud backend has NO /activate endpoint (only /register)
  - Result: Activation always fails with 404/500
```

---

## Section 3: What Works ✅

| Feature | Endpoint / File | Notes |
|---|---|---|
| **User Login** | `POST /api/auth/login` | Hybrid Supabase + local SQLite. Works offline too. |
| **User Registration** | `POST /api/auth/register` | Creates Supabase user + local replica + tenant_id |
| **JWT Token Auth** | `GET /api/auth/me` | Token validated, user returned |
| **AuthGuard redirect** | `AuthGuard.tsx:22` | Correctly redirects to `/login` when no token |
| **UserContext caching** | `UserContext.tsx:74` | Falls back to `k24_user` localStorage when offline |
| **Login page** | `/login` | Fully functional, stores token + cookie |
| **Signup page** | `/signup` | Fully functional, auto-login after register |
| **DeviceGuard license check** | `DeviceGuard.tsx:14` | Correctly reads `k24_license_key` from localStorage |
| **Periodic validation** | `DeviceGuard.tsx:31` | Calls `/api/devices/validate` every 5 min |
| **Dev reset shortcut** | `DeviceGuard.tsx:67` | `Ctrl+Shift+R` clears activation state |
| **Web callback page** | `/auth/desktop` | Calls cloud `/api/devices/register` correctly |
| **Deep link listener** | `ConnectDevice.tsx:46` | Listens for `k24://auth/callback` |
| **Manual license entry** | `ConnectDevice.tsx:360` | Form works, calls `/api/devices/activate` |
| **Backend health** | `GET /health` | Returns `{"status":"ok"}` |
| **Subscription endpoint** | `GET /api/auth/subscription` | Exists and returns data |

---

## Section 4: What's Broken ❌

### 1. Device Activation End-to-End (Critical)
**File:** `backend/routers/devices.py:110-221`
**Error:** `POST /api/devices/activate` calls `cloud_url/api/devices/activate` which doesn't exist on Railway.
**Symptom:** Clicking "Authenticate via Browser" → browser opens → web registers device → deep link fires → desktop calls `/api/devices/activate` → **503 or 404 from cloud**.

### 2. ConnectDevice Unreachable Without JWT (Design Conflict)
**File:** `src/app/page.tsx:9`, `src/components/AuthGuard.tsx:22`
**Error:** `AuthGuard` redirects to `/login` before `DeviceGuard` can show `ConnectDevice`.
**Symptom:** Fresh device with no token → goes to `/login`, never sees device activation screen.
**Root cause:** The intended flow (device activation → login) is reversed in the code (login → device activation).

### 3. Forgot Password Redirect Hardcoded
**File:** `backend/routers/auth.py:487`
**Error:** `redirect_to: "https://your-app.vercel.app/reset-password"` — placeholder URL never updated.
**Symptom:** Password reset emails link to wrong domain.

### 4. Subscription Not Enforced
**File:** Entire `src/` frontend
**Error:** `GET /api/auth/subscription` is never called from any frontend component.
**Symptom:** Expired/cancelled subscriptions can still access all features.

### 5. `k24_user` localStorage stores Supabase UUID in `google_api_key` field
**File:** `backend/routers/auth.py:177`
**Error:** `google_api_key=user_id` — Supabase UUID is stored in the wrong column.
**Symptom:** Confusing field naming; subscription check uses `current_user.google_api_key` to get Supabase ID (`auth.py:565`).

### 6. `DeviceLicense` table may not exist in SQLite
**File:** `backend/routers/devices.py:8`
**Error:** `from backend.database import get_db, DeviceLicense` — if migration hasn't run, this table is missing.
**Symptom:** `/api/devices/validate` and `/api/devices/register` crash with SQLAlchemy errors.

---

## Section 5: Recommendations

### Simplest Path to Working Auth (Minimal Changes)

**Goal:** User can login → see dashboard → no device activation required yet.

The login/JWT system already works. The only blocker is that `DeviceGuard` on the dashboard
requires a `k24_license_key`. **Bypass it temporarily:**

```tsx
// DeviceGuard.tsx — TEMPORARY DEV BYPASS
// Change line 17-25 to always authorize in dev mode:
if (process.env.NODE_ENV === 'development') {
    setIsAuthorized(true);
    return;
}
```

This lets you test the full login → dashboard flow without fixing the broken activation.

---

### What to Disable Temporarily

| System | Action | Reason |
|---|---|---|
| `DeviceGuard` license check | Bypass in dev mode | Activation endpoint broken |
| Subscription enforcement | Leave as-is (already disabled) | Not implemented yet |
| Forgot password redirect | Fix placeholder URL | Low priority |

---

### What to Fix First (Priority Order)

**P1 — Fix `/api/devices/activate` endpoint (2 hours)**
The desktop backend's `activate` endpoint should NOT proxy to the cloud. Instead, it should:
1. Accept `license_key` from the frontend
2. Store it locally in `DeviceLicense` table
3. Return `{success: true, tenant_id: ..., user_id: ...}`

The cloud registration (`/auth/desktop` web page → cloud `/api/devices/register`) already
works. The desktop just needs to accept the license key that comes back via deep link.

**P2 — Fix execution order conflict (1 hour)**
`DeviceGuard` should run BEFORE `AuthGuard`, or the device activation screen should be
accessible without a JWT. Options:
- Move `DeviceGuard` to `ClientLayout.tsx` before `UserProvider`
- Make `/` a public page and handle auth inside `DashboardClient`

**P3 — Fix forgot password redirect (5 minutes)**
`backend/routers/auth.py:487` — replace `your-app.vercel.app` with actual domain.

**P4 — Add subscription enforcement (4 hours)**
Call `GET /api/auth/subscription` in `UserContext` after login and store result.
Block access in `AuthGuard` if `can_access === false`.

---

### Hybrid Model Feasibility

**Recommended architecture:**

```
App Launch
    │
    ├── No JWT token → /login (email + password)
    │       └── Login success → JWT stored → redirect to /
    │
    └── Has JWT token → /  (dashboard)
            │
            └── DeviceGuard checks k24_license_key
                    │
                    ├── Has license → Dashboard ✅
                    │
                    └── No license → ConnectDevice
                            │
                            └── Browser auth → deep link → activate → Dashboard ✅
```

**This is already the intended design.** The only things broken are:
1. The activation endpoint proxy (P1)
2. The execution order (P2 — AuthGuard fires before DeviceGuard)

Fix those two and the hybrid model works as designed.

---

## Quick Reference: localStorage Keys

| Key | Set By | Read By | Purpose |
|---|---|---|---|
| `k24_token` | `login/page.tsx:53` | `api.ts:26`, `UserContext.tsx:51` | JWT for API auth |
| `k24_user` | `login/page.tsx:55` | `UserContext.tsx:75` | Cached user object |
| `k24_license_key` | `ConnectDevice.tsx:145` | `DeviceGuard.tsx:14,32` | Device activation gate |
| `k24_device_id` | `ConnectDevice.tsx:192` | `DeviceGuard.tsx:33` | Hardware fingerprint |
| `k24_tenant_id` | `ConnectDevice.tsx:140` | nowhere in frontend | Tenant routing |
| `k24_user_id` | `ConnectDevice.tsx:143` | nowhere in frontend | User reference |
| `k24_backend_port` | `ConnectDevice.tsx:201` | `DeviceGuard.tsx:38` | Dynamic port |
