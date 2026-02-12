# Domain & URL Audit Report

## 1. Environment Variables (URLs)

| Variable Name | Defined In | Default/Example Value | Used By Code |
| :--- | :--- | :--- | :--- |
| `API_BASE_URL` | `cloud-backend/.env.example` (Line 9) | `https://api.k24.ai` | `cloud-backend` (Internal config) |
| `SUPABASE_URL` | `cloud-backend/.env.example` (Line 12) | `https://your-project.supabase.co` | `cloud-backend/database/supabase_client.py` (Line 32) |
| `SUPABASE_URL` | `backend/.env.example` (Line 8) | `https://your-project.supabase.co` | `backend/services/supabase_service.py` (Line 18) |
| `BACKEND_URL` | `baileys-listener/.env.example` (Line 4) | `http://localhost:8080` | `baileys-listener/listener.js` (Line 30) |
| `BAILEYS_SERVICE_URL` | `cloud-backend/.env.example` (Line 22) | `http://localhost:3000` | `cloud-backend` (Used for health checks/callbacks) |
| `NEXT_PUBLIC_SUPABASE_URL` | `frontend/.env.local` | - | `frontend/src/lib/supabase/client.ts` (Line 6) |

---

## 2. HTTP Calls to Backend/Cloud

| File | Line | Method | URL / Base | Context |
| :--- | :--- | :--- | :--- | :--- |
| `baileys-listener/listener.js` | 67 | POST | `${BACKEND_URL}/api/whatsapp/identify-user` | Phone number User ID Cache |
| `baileys-listener/listener.js` | 358 | POST | `${BACKEND_URL}/api/whatsapp/cloud/incoming` | Cloud Webhook (M1) |
| `baileys-listener/listener.js` | 389 | POST | `${BACKEND_URL}/api/whatsapp/verify-webhook` | QR Code Verification |
| `baileys-listener/listener.js` | 442 | POST | `${BACKEND_URL}/api/query/whatsapp` | Smart AI Query |
| `baileys-listener/listener.js` | 530 | POST | `${BACKEND_URL}/api/baileys/process` | Legacy Process (Fallback) |
| `backend/services/supabase_service.py` | 40 | GET/POST | `${self.url}/rest/v1/...` | Supabase REST API calls (Desktop) |
| `test_batch_processing.py` | 60 | POST | `${BACKEND_URL}/api/baileys/process-batch` | Test Script |

---

## 3. Localhost References (Hardcoded)

| File | Line | Context | Value | Action |
| :--- | :--- | :--- | :--- | :--- |
| `baileys-listener/listener.js` | 30 | Fallback Default | `http://localhost:8000` | Safe (Fallback only) |
| `cloud-backend/.env.example` | 22 | Baileys URL | `http://localhost:3000` | Update in Railway Env Vars |
| `baileys-listener/.env.example` | 4 | Backend URL | `http://localhost:8080` | Update in Railway Env Vars |
| `test_batch_processing.py` | 11 | Test Config | `http://localhost:8000` | Safe (Test only) |

---

## 4. Hardcoded Railway URLs

**Status**: ✅ **CLEAN**
- No active code was found containing `weare-production.up.railway.app` or `artistic-healing`.
- Documentation (`CLOUD_SERVICES_ORGANIZATION.md`) mentions `https://api.k24.ai` as an example.

---

## 5. Custom Domain Readiness Plan

**Target Domain**: `https://api.k24cloud.in`

### ✅ Deployment Checklist

1. **Cloud Backend (Railway)**
   - Set `API_BASE_URL` = `https://api.k24cloud.in`
   - Set `SUPABASE_URL` = `https://[REAL_PROJECT_ID].supabase.co`

2. **Baileys Listener (Railway/VPS)**
   - Set `BACKEND_URL` = `https://api.k24cloud.in`
   - **Limit Re-deploy**: Changing this only requires redeploying the Baileys Listener service.

3. **Desktop App (Tauri)**
   - **Action Needed**: New M4 installer must package a config file or env var that sets `CLOUD_API_URL` to `https://api.k24cloud.in`.
   - **Code Change**: Ensure `backend/services/config_service.py` (M4 task) reads this URL instead of defaulting to localhost.

### ⚠️ Critical Watchlist
- **Supabase Auth**: Ensure "Site URL" and "Redirect URLs" in Supabase Dashboard include `https://api.k24cloud.in` and `k24://*` for deep links.
- **CORS**: Cloud Backend `main.py` must allow `https://tauri.localhost` and `k24://` origins.
