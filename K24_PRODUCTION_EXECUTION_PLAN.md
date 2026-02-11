# K24 Production Execuction Plan
**Status:** `FINAL_ASSEMBLY`
**Date:** 2026-02-01

## 1. System Health Check
- **Frontend Logic:** ✅ **Fresh** (Rebuilt during Tauri build)
- **Desktop Shell:** ✅ **Fresh** (Code refactored and working)
- **Backend Binary:** ✅ **Verified Fresh** (Rebuilt 16:25).

## 2. Phase 1: The Brain Transplant (Backend Refresh)
**Status:** ✅ **COMPLETE**
**Objective:** Ensure the installer contains the absolute latest Python logic.
**Command:** `python scripts/build_sidecars.py`
**Validation:** Verified `frontend/src-tauri/binaries/k24-backend-*.exe` timestamp.

## 3. Phase 2: The Body Assembly (Final Build)
**Status:** 🔄 **IN PROGRESS**
**Objective:** Package the fresh backend into the installer.
**Command:** `npx tauri build` (in `frontend` dir)
**Output:** `frontend/src-tauri/target/release/bundle/nsis/K24_1.0.0_x64-setup.exe`

## 4. Phase 3: Distribution (The "Web Upload")
How to deliver this to your first user:

### Option A: GitHub Releases (Best for Developers)
1. Push code to GitHub.
2. Go to "Releases" -> "Draft New Release".
3. Tag: `v1.0.0`.
4. Upload the `.exe` file as an asset.
5. Share the "Assets" link.

### Option B: Cloud Storage (Easiest for First User)
1. Upload the `.exe` to Google Drive / OneDrive / Wetransfer.
2. Set permissions to "Anyone with the link".
3. Send the link.

## 5. Phase 4: The Onboarding Flow (User Step-by-Step)
**Step 1: Admin Setup**
- Log into your Super Admin dashboard.
- Create a new **Tenant** for this user (e.g., "Client Alpha").
- Create a **User Account** (email/password) linked to that Tenant.

**Step 2: Installation**
- User downloads and runs `K24_1.0.0_x64-setup.exe`.
- *Note:* Windows SmartScreen will pop up because the app is unsigned. Tell them to click **"More Info" -> "Run Anyway"**.

**Step 3: Activation**
- App opens. User logs in with the credentials you created.
- App Status changes to "Scanning for Tally...".

**Step 4: Connection**
- User opens Tally Prime on their desktop.
- K24 detects it, connects, and starts syncing.
- You see the data appear in your Web Dashboard.

## 6. What's Left?
Just executing **Phase 1** and **Phase 2** now.
