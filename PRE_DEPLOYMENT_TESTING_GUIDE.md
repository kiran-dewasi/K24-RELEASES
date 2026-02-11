# K24 Pre-Deployment Testing & Complete Process Guide

## 🎯 Overview: What Goes Where

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         YOUR K24 ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    VERCEL (Cloud)                                │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  ✅ Frontend UI (Next.js pages)                                 │    │
│  │  ✅ Server Actions (profile, contacts - using Supabase)         │    │
│  │  ✅ Supabase client connection                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                           │
│                              │ API Calls                                 │
│                              ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                   SUPABASE (Cloud)                              │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  ✅ User Authentication (sign up, login)                        │    │
│  │  ✅ Tenants table                                               │    │
│  │  ✅ Users table (cloud mirror)                                  │    │
│  │  ✅ WhatsApp bindings (phone → tenant mapping)                  │    │
│  │  ✅ Subscriptions & Licensing                                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ═══════════════════════════════════════════════════════════════════    │
│                         CUSTOMER'S COMPUTER                              │
│  ═══════════════════════════════════════════════════════════════════    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │               DESKTOP APP (Tauri .exe)                          │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  ⬇️ Loads UI from Vercel URL                                    │    │
│  │  🔧 Runs local Backend (FastAPI sidecar)                        │    │
│  │  💾 SQLite Database (business data)                             │    │
│  │  🔄 Tally Agent (sync with local Tally)                         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                           │
│                              │ Port 9000                                 │
│                              ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                   TALLY PRIME (Local)                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 PART 1: Pre-Deployment Testing Checklist

### Test 1: Auth System ✅
**Current Implementation:**
- Backend (`auth.py`) handles: Registration, Login, JWT tokens
- Uses HYBRID approach:
  - Supabase for cloud auth (optional)
  - Local SQLite for user storage
  - JWT tokens for session management

**Test Steps:**
```bash
# 1. Start backend
cd backend
python -m uvicorn main:app --reload --port 8000

# 2. Test login API
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=kittu@krishasales.com&password=kittu123"
```

**Expected:** JWT token returned

---

### Test 2: Frontend Loads ✅
```bash
# Start frontend
cd frontend
npm run dev

# Open browser: http://localhost:3000
```

**Check:**
- [ ] Login page loads
- [ ] Can enter credentials
- [ ] Redirects to dashboard after login

---

### Test 3: Dashboard Data ✅
After login:
- [ ] Dashboard shows stats
- [ ] Ledgers load
- [ ] No console errors

---

### Test 4: Tally Push/Pull 🔄

**Pull from Tally:**
```bash
# With Tally running on port 9000
curl http://localhost:8000/api/tally/sync/ledgers
```

**Push to Tally (Invoice):**
```bash
curl -X POST http://localhost:8000/api/tally/push/voucher \
  -H "Content-Type: application/json" \
  -d '{
    "voucher_type": "Sales",
    "party_ledger": "Cash",
    "items": [{"name": "Test Item", "qty": 1, "rate": 100}]
  }'
```

---

### Test 5: Invoice Generation 📄
- [ ] Create new voucher from UI
- [ ] View in invoices list
- [ ] Push to Tally works

---

## 📋 PART 2: Deployment Process (Detailed)

### Phase 1: Deploy Frontend to Vercel

#### Step 1.1: Prepare Code
```bash
cd c:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare

# Ensure all changes committed
git add .
git commit -m "Ready for Vercel deployment"
git push origin main
```

#### Step 1.2: Go to Vercel
1. Open https://vercel.com
2. Sign in with GitHub
3. Click "Add New" → "Project"
4. Find and select your `weare` repository

#### Step 1.3: Configure Project
```
Framework Preset: Next.js (auto-detected)
Root Directory: frontend    ← IMPORTANT!
Build Command: npm run build
Install Command: npm install
Output Directory: (leave blank)
```

#### Step 1.4: Set Environment Variables
Click "Environment Variables" and add:

| Name | Value | Notes |
|------|-------|-------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend runs locally |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://gxukvnoiyzizienswgni.supabase.co` | Your Supabase |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `sb_publishable_xxx` | Your key |

#### Step 1.5: Deploy
Click "Deploy" and wait ~2-3 minutes.

**Result:** Your app is live at `https://your-project.vercel.app`

---

### Phase 2: Build Desktop App

#### Step 2.1: Update Tauri Config
After Vercel deployment, update `frontend/src-tauri/tauri.conf.json`:

```json
{
  "build": {
    "devUrl": "https://your-project.vercel.app",
    "beforeDevCommand": "",
    "beforeBuildCommand": ""
  }
}
```

**OR** for dev/testing, keep `http://localhost:3000`

#### Step 2.2: Build Backend Sidecar
```bash
cd backend
pip install pyinstaller
pyinstaller k24_backend.spec --noconfirm
```

Result: `backend/dist/k24-backend.exe`

#### Step 2.3: Copy Sidecar
```bash
mkdir frontend\src-tauri\binaries
copy backend\dist\k24-backend.exe frontend\src-tauri\binaries\k24-backend-x86_64-pc-windows-msvc.exe
```

#### Step 2.4: Build Tauri App
```bash
cd frontend
npx tauri build
```

**Results:**
- `frontend/src-tauri/target/release/K24.exe` - Standalone executable
- `frontend/src-tauri/target/release/bundle/msi/K24_1.0.0_x64.msi` - Windows Installer
- `frontend/src-tauri/target/release/bundle/nsis/K24_1.0.0_x64-setup.exe` - NSIS Installer

---

### Phase 3: Set Up Cloud Services

#### 3.1: Supabase Tables

**A. Users Table (already exists from Supabase Auth)**
Supabase automatically creates `auth.users` table.

**B. Tenants Table**
```sql
CREATE TABLE public.tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  owner_id UUID REFERENCES auth.users(id),
  plan TEXT DEFAULT 'free',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  settings JSONB DEFAULT '{}'
);
```

**C. WhatsApp Bindings Table**
```sql
CREATE TABLE public.whatsapp_bindings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_number TEXT NOT NULL UNIQUE,
  tenant_id UUID REFERENCES public.tenants(id),
  user_id UUID REFERENCES auth.users(id),
  verified_at TIMESTAMPTZ,
  binding_code TEXT,
  code_expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast phone lookup
CREATE INDEX idx_whatsapp_phone ON public.whatsapp_bindings(phone_number);
```

**D. Subscriptions Table**
```sql
CREATE TABLE public.subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES public.tenants(id),
  plan TEXT NOT NULL DEFAULT 'free',
  status TEXT DEFAULT 'active',
  starts_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  features JSONB DEFAULT '{}'
);
```

#### 3.2: Baileys Listener (VPS)

**Deploy to a VPS (DigitalOcean, AWS EC2, etc.):**

```bash
# On your VPS
git clone your-repo
cd weare/baileys-listener
npm install
pm2 start listener.js --name k24-whatsapp
```

**Required Environment:**
```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJxxx
K24_SHARED_WHATSAPP_NUMBER=+91XXXXXXXXXX
```

#### 3.3: WhatsApp Routing Logic

When a message comes in:
```javascript
// baileys-listener/listener.js
async function routeMessage(senderPhone, message) {
  // 1. Look up tenant from phone
  const { data: binding } = await supabase
    .from('whatsapp_bindings')
    .select('tenant_id, user_id')
    .eq('phone_number', senderPhone)
    .single();

  if (!binding) {
    // Unknown user - ask for client code
    return sendReply(senderPhone, "Welcome! Please send your client code to connect.");
  }

  // 2. Get tenant's local backend URL (stored in settings)
  const { data: tenant } = await supabase
    .from('tenants')
    .select('settings')
    .eq('id', binding.tenant_id)
    .single();

  // 3. Queue message for that tenant's desktop app
  await supabase
    .from('message_queue')
    .insert({
      tenant_id: binding.tenant_id,
      sender_phone: senderPhone,
      message: message,
      status: 'pending'
    });

  // 4. Desktop app polls this queue and processes
}
```

---

## 🧪 PART 3: Local Testing Before Deployment

### Run Full Local Test:

**Terminal 1: Backend**
```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

**Terminal 2: Frontend**
```bash
cd frontend
npm run dev
```

**Terminal 3: (Optional) Tally Sync Test**
```bash
cd backend
python -c "from services.tally_connector import TallyConnector; t = TallyConnector(); print(t.test_connection())"
```

### Test Checklist:
- [ ] Backend starts on :8000
- [ ] Frontend starts on :3000
- [ ] Login works
- [ ] Dashboard loads data
- [ ] Can view ledgers
- [ ] Can create voucher
- [ ] Tally sync works (if Tally running)

---

## ❓ Quick Reference: Which API Calls Go Where?

| Action | Goes To | Why |
|--------|---------|-----|
| Login | Local Backend + Supabase | Hybrid auth |
| Get Dashboard Stats | Local Backend | Data from local SQLite |
| Get Ledgers | Local Backend | Synced from Tally |
| Create Voucher | Local Backend | Stored locally, pushed to Tally |
| Tally Sync | Local Backend | Direct connection to Tally |
| WhatsApp Message In | Baileys (VPS) → Supabase Queue | Message routing |
| WhatsApp Processing | Local Backend | Desktop processes messages |

---

## 📞 Ready to Test?

Run these commands to start testing:

```bash
# Terminal 1
cd backend && python -m uvicorn main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

Then open http://localhost:3000 and test everything!

---

*Created: January 29, 2026*
