# K24 Cloud Services Organization

## Overview

The K24 codebase has been reorganized to separate **cloud services** from **desktop services**.

## Directory Structure

```
weare/
├── cloud-backend/          # ☁️ Cloud-hosted FastAPI service (Railway/Cloud)
│   ├── routers/
│   │   ├── auth.py        # User authentication & JWT
│   │   ├── whatsapp.py    # Customer mapping CRUD
│   │   ├── whatsapp_cloud.py # NEW: Incoming webhook from Baileys
│   │   ├── baileys.py     # Baileys message processing
│   │   ├── devices.py     # Desktop device registration
│   │   ├── query.py       # Smart query orchestrator
│   │   └── __init__.py
│   ├── models/            # Pydantic models (to be added)
│   ├── services/          # Business logic services (to be added)
│   ├── main.py            # FastAPI app entry point
│   ├── requirements.txt   # Cloud-only Python dependencies
│   ├── Dockerfile         # Container for Railway deployment
│   ├── .env.example       # Environment variables template
│   ├── .gitignore
│   └── README.md
│
├── baileys-listener/       # 📱 WhatsApp listener (Node.js + Baileys)
│   ├── listener.js        # Main WhatsApp event handler
│   ├── batch-handler.js   # Smart message batching
│   ├── auth/              # WhatsApp session credentials (gitignored)
│   ├── temp/              # Temporary files
│   ├── package.json       # Node dependencies
│   ├── Dockerfile         # Container for cloud deployment
│   ├── .env.example       # Environment variables template
│   ├── .gitignore
│   └── README.md
│
└── backend/               # 🖥️ Desktop sidecar (runs locally with Tauri)
    ├── routers/
    │   ├── sync.py        # Tally sync operations
    │   ├── dashboard.py   # Dashboard data (from local Tally)
    │   ├── ledgers.py     # Ledger operations (local Tally)
    │   ├── vouchers.py    # Voucher CRUD (local Tally)
    │   ├── inventory.py   # Inventory operations (local Tally)
    │   └── ... (other Tally-dependent routers)
    └── ... (Tally connectors, loaders, etc.)
```

## Cloud vs Desktop Services

### ☁️ Cloud Backend (cloud-backend/)

**Runs on:** Railway/Cloud Platform  
**Purpose:** Multi-tenant API, message routing, authentication

**Handles:**
- ✅ User authentication (JWT tokens)
- ✅ WhatsApp message routing (from Baileys → desktops)
- ✅ Customer-to-tenant mapping
- ✅ Device registration & management
- ✅ Message queue for offline desktops
- ✅ Smart query processing

**Does NOT handle:**
- ❌ Direct Tally integration (Tally is local-only)
- ❌ Desktop-specific features
- ❌ Local file operations

**Key Endpoints:**
- `POST /api/auth/login` - User login
- `POST /api/whatsapp/incoming` - Webhook from Baileys (NEW)
- `POST /api/whatsapp/identify-user` - Tenant routing
- `GET /api/whatsapp/jobs` - Desktop polling (Phase 3)
- `POST /api/devices/activate` - Device registration

---

### 📱 Baileys Listener (baileys-listener/)

**Runs on:** Cloud VM with persistent storage  
**Purpose:** WhatsApp Web connection handler

**Handles:**
- ✅ Maintains 24/7 WhatsApp connection
- ✅ Receives incoming WhatsApp messages
- ✅ Routes messages to cloud backend webhook
- ✅ Sends replies back to customers
- ✅ Smart batching for bulk image uploads

**Configuration:**
- `BACKEND_URL` → Points to cloud-backend API
- `BAILEYS_SECRET` → Shared secret with cloud backend
- `auth/` → WhatsApp session data (mounted volume)

**Flow:**
```
WhatsApp Servers ←→ Baileys ──HTTP──→ Cloud Backend
```

---

### 🖥️ Desktop Backend (backend/)

**Runs on:** Customer's Windows machine (Tauri sidecar)  
**Purpose:** Local Tally ERP integration

**Handles:**
- ✅ Connects to local Tally (port 9000)
- ✅ Syncs Tally data to cloud
- ✅ Processes vouchers/ledgers locally
- ✅ Reads dashboard metrics from Tally

**Configuration:**
- Runs on dynamic port (e.g., 24286)
- Only accessible from localhost
- Uses desktop token authentication

---

## Migration from Old Structure

### Files Copied to cloud-backend/

The following routers were **copied** (not moved) from `backend/routers/` to `cloud-backend/routers/`:

1. ✅ `auth.py` - User authentication
2. ✅ `whatsapp.py` - Customer mappings
3. ✅ `baileys.py` - Message processing
4. ✅ `devices.py` - Device registration
5. ✅ `query.py` - Smart queries

### New Files Created

1. ✅ `cloud-backend/routers/whatsapp_cloud.py` - Cloud webhook endpoint
2. ✅ `cloud-backend/main.py` - Cloud FastAPI app
3. ✅ `cloud-backend/Dockerfile` - Cloud container
4. ✅ `baileys-listener/Dockerfile` - Baileys container
5. ✅ READMEs and documentation

### Files That Stayed in backend/

The following routers remain **desktop-only** because they require local Tally:

- ❌ `sync.py` - Tally sync service
- ❌ `dashboard.py` - Reads from Tally
- ❌ `ledgers.py` - Tally ledger operations
- ❌ `vouchers.py` - Tally voucher CRUD
- ❌ `inventory.py` - Tally stock items
- ❌ `reports.py` - Tally reports
- ❌ `operations.py` - Tally operations

---

## Next Steps (Phase-by-Phase)

### Phase 1: Deploy to Cloud ✅ (Prepared)
- [x] Separate cloud/desktop codebases
- [ ] Deploy cloud-backend to Railway
- [ ] Deploy baileys-listener to cloud VM
- [ ] Test end-to-end message flow

### Phase 2: Implement Tenant Routing
- [ ] Migrate customer mappings to Supabase
- [ ] Implement message queue table
- [ ] Complete `/api/whatsapp/incoming` webhook
- [ ] Add tenant_id routing logic

### Phase 3: Desktop Polling
- [ ] Desktop app polls `/api/whatsapp/jobs`
- [ ] Process jobs locally via Tally
- [ ] Report completion to cloud
- [ ] Send WhatsApp replies via cloud

### Phase 4: Production Hardening
- [ ] API key authentication
- [ ] Tenant isolation tests
- [ ] Sentry monitoring
- [ ] Load testing

---

## Important Notes

⚠️ **Both codebases exist side-by-side:**
- `backend/` is for **desktop Tauri sidecar**
- `cloud-backend/` is for **cloud deployment**

⚠️ **Do NOT delete backend/ folder:**
- Desktop app still needs it for local Tally integration

⚠️ **Auth folder security:**
- `baileys-listener/auth/` contains WhatsApp credentials
- Must be on persistent volume in cloud
- Already gitignored

---

## Deployment Commands

### Cloud Backend (Railway)
```bash
cd cloud-backend
railway login
railway up
```

### Baileys Listener
```bash
cd baileys-listener
docker build -t k24-baileys .
docker run -v /path/to/auth:/app/auth -e BACKEND_URL=https://api.k24.ai k24-baileys
```

### Desktop Backend (unchanged)
```bash
# Starts automatically with Tauri app
cd frontend
npm run tauri dev
```
