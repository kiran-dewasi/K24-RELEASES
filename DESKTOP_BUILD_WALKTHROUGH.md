# K24 Desktop App - Production Build Walkthrough

## 📋 Your Architecture (Confirmed)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CLOUD (Vercel + Supabase)                        │
├─────────────────────────────────────────────────────────────────────┤
│  ✅ User Authentication (Supabase Auth)                             │
│  ✅ Subscription & Licensing                                        │
│  ✅ WhatsApp Routing (Tenant ID detection - "Which user messaged?") │
│  ✅ Baileys Listener (Message Queue on VPS)                         │
│  ✅ Multi-tenant user database                                      │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTPS API Calls
┌───────────────────────────▼─────────────────────────────────────────┐
│                 DESKTOP APP (Tauri .exe)                            │
├─────────────────────────────────────────────────────────────────────┤
│  📦 BUNDLED COMPONENTS:                                             │
│    ├── Frontend (Next.js static files)                              │
│    └── Backend Sidecar (k24-backend.exe - FastAPI)                  │
│                                                                      │
│  💾 LOCAL DATA:                                                      │
│    ├── SQLite Database (100% local business data)                   │
│    ├── Tally sync cache                                             │
│    └── User preferences                                             │
│                                                                      │
│  🔧 LOCAL SERVICES:                                                  │
│    ├── Tally Agent (bidirectional sync with local Tally)            │
│    └── AI Orchestrator (Gemini API calls)                           │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ Port 9000 (Tally ODBC)
┌───────────────────────────▼─────────────────────────────────────────┐
│                    TALLY PRIME (Local)                              │
│  - Running on customer's machine                                    │
│  - Real-time XML sync                                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 What Goes Where

| Component | Location | Why |
|-----------|----------|-----|
| User Auth | Supabase (Cloud) | Multi-tenant, secure, managed |
| WhatsApp Tenant Detection | Vercel API (Cloud) | Single shared number, routes to correct user |
| Baileys Listener | VPS (Cloud) | Always-on WhatsApp connection |
| FastAPI Backend | Local Sidecar | Talks to local Tally |
| SQLite Database | Local | Business data stays on user's machine |
| Tally Sync | Local | Direct connection to Tally on same machine |
| AI/Gemini | API calls from local | Processing happens locally, calls Gemini API |

---

## 🚀 Build Steps

### Prerequisites Checklist:
- [ ] Rust installed (`rustc --version`)
- [ ] Node.js 18+ installed
- [ ] Python 3.10+ installed
- [✅] Backend Core Features Verified (Ready for Packaging)
- [ ] Backend sidecar built (`k24-backend.exe`)

### Step 1: Build the Backend Sidecar

The backend needs to be packaged as a single .exe file.

```bash
cd backend
pip install pyinstaller
pyinstaller k24_backend.spec
```

Output: `backend/dist/k24-backend.exe`

### Step 2: Copy Sidecar to Tauri Binaries

```bash
mkdir -p frontend/src-tauri/binaries
copy backend\dist\k24-backend.exe frontend\src-tauri\binaries\k24-backend-x86_64-pc-windows-msvc.exe
```

**Important:** The filename MUST include the target triple for Tauri to find it.

### Step 3: Configure Frontend for Production

Update `frontend/src/lib/api-config.ts`:
```typescript
// For desktop app, backend runs locally
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Cloud services (auth, WhatsApp routing)
const CLOUD_API = 'https://your-vercel-api.vercel.app/api';
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
```

### Step 4: Build Frontend (Static Export)

We need to fix the dynamic routes issue first:

**Option A: Client-Side Only Routing** (Recommended for speed)
- Keep routes as-is
- Use `output: 'standalone'` 
- Bundle Next.js server

**Option B: Convert to Query Params**
- Change `/items/[id]` to `/item?id=123`
- Allows `output: 'export'` for pure static files

### Step 5: Build Tauri App

```bash
cd frontend
npx tauri build
```

Output: 
- `frontend/src-tauri/target/release/K24.exe`
- `frontend/src-tauri/target/release/bundle/msi/K24_1.0.0_x64.msi`
- `frontend/src-tauri/target/release/bundle/nsis/K24_1.0.0_x64-setup.exe`

---

## ⚠️ Known Issues & Solutions

### Issue 1: Dynamic Routes + Static Export
**Problem:** Next.js routes like `/items/[id]` don't work with `output: 'export'` when using `'use client'`

**Solution Options:**

**A) Use Standalone Mode (Current approach)**
- Keep `output: 'standalone'` in next.config.ts
- Bundle the Next.js server alongside the app
- Requires a bit more complexity but works with all routes

**B) Host Frontend on Vercel** 
- Desktop app loads from `https://app.k24.ai`
- Simplest, but requires internet for UI

**C) Convert Routes to Query Params**
- `/items?id=123` instead of `/items/[id]`
- Works with static export
- Requires refactoring

### Issue 2: Backend Sidecar Not Starting
**Problem:** Tauri can't find or start the backend

**Solution:**
1. Ensure filename matches: `k24-backend-x86_64-pc-windows-msvc.exe`
2. Check permissions in `capabilities/default.json`
3. Add startup code in Tauri:

```rust
// In src/lib.rs
use tauri_plugin_shell::ShellExt;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let sidecar = app.shell().sidecar("k24-backend").unwrap();
            tauri::async_runtime::spawn(async move {
                let (mut rx, _child) = sidecar.spawn().unwrap();
                while let Some(event) = rx.recv().await {
                    // Handle sidecar output
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error running app");
}
```

### Issue 3: Tally Connection Fails
**Problem:** Backend can't connect to Tally on customer's machine

**Solution:**
1. Ensure Tally is running with ODBC server enabled
2. Check port 9000 is open
3. Add connection status UI in app

### Issue 4: WhatsApp Tenant Routing
**Problem:** Cloud needs to know which local app to send messages to

**Solution:**
The cloud Baileys listener:
1. Receives WhatsApp message
2. Looks up sender's phone number in Supabase → Gets tenant_id
3. Stores message in Supabase queue
4. Local desktop app polls for new messages (or uses WebSocket)

---

## 📦 Distribution to Customers

### Option 1: Direct Download
1. Upload MSI to your website/Google Drive
2. Send link to customers
3. They download and install

**Pros:** Simple, immediate
**Cons:** Windows SmartScreen warning (no code signing)

### Option 2: Code Signed Installer
1. Purchase code signing certificate (~$100-400/year)
2. Sign the MSI with your certificate
3. No security warnings

**Pros:** Professional, trusted
**Cons:** Cost, setup time

### Option 3: Auto-Updates
Configure Tauri's built-in updater:
```json
{
  "plugins": {
    "updater": {
      "endpoints": ["https://update.k24.ai/{{target}}/{{arch}}/{{current_version}}"],
      "pubkey": "YOUR_PUBLIC_KEY"
    }
  }
}
```

---

## 🧪 Testing Before Distribution

### Local Testing:
1. Build the app
2. Install on your own Windows machine
3. Test all features:
   - [ ] Login works
   - [ ] Dashboard loads
   - [ ] Tally sync works
   - [ ] Reports generate
   - [ ] WhatsApp messages received

### Customer Testing:
1. Send to 1-2 beta customers
2. Get feedback on:
   - Installation issues
   - Tally connection
   - Performance
   - Missing features

---

## 📞 Next Immediate Steps

1. **Deploy Cloud Services:**
   - Set up Supabase project (if not done)
   - Deploy WhatsApp routing API to Vercel
   - Set up Baileys on VPS

2. **Build Desktop App:**
   - Build backend sidecar
   - Build frontend
   - Build Tauri app
   - Test installer

3. **Customer Delivery:**
   - Create installation guide
   - Record demo video
   - Prepare support process

---

*Last Updated: January 28, 2026*
