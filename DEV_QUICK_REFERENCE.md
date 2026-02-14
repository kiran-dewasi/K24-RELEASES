# 🚀 Quick Dev Reference - K24 Desktop

## Starting Local Dev

### 1. Backend
```bash
# Copy env template (first time only)
cp backend/.env.example backend/.env

# Edit backend/.env and set:
# DEBUG=true
# GOOGLE_API_KEY=your_key_here

# Start backend
python backend/desktop_main.py --port 8000 --token test-token-123
```

**Expected**: Logs show "Running in development mode (no token validation)"

---

### 2. Frontend
```bash
cd frontend
npx tauri dev
```

**Expected**: 
- App opens
- Navbar shows "Live" (green) if backend is healthy
- If stuck on Dashboard, use reset shortcut below

---

## Dev-Only Shortcuts & Helpers

### Reset Activation (Ctrl+Shift+R)
**What**: Clears all activation state, shows ConnectDevice screen  
**When**: App is focused  
**Works**: Only in development (`NODE_ENV=development`)  
**Alert**: "✅ Device activation reset! Showing ConnectDevice screen."

---

### Test Credentials Auto-Fill
**Where**: ConnectDevice → "I have a license key" → Yellow button  
**Button**: "🧪 Use Test Values (Dev Only)"  
**Fills**:
- License: `TEST_LICENSE_001`
- Tenant: `TENANT-e9dbb826`  
- User: `e9dbb826-5892-43c3-91e6-78900e93f687`

**Works**: Only when `NODE_ENV=development`

---

### Backend Dev Bypass
**How**: Set `DEBUG=true` in `backend/.env`  
**Effect**: Backend accepts `X-Dev-Mode: true` header from frontend  
**Security**: Only works when running from source (not frozen exe)

**Logs**: 
```
[DEV MODE] Bypassing desktop token validation for /api/devices/activate
```

---

## Testing Activation Flow

1. **Reset** (if needed): `Ctrl+Shift+R`
2. Click **"I have a license key"**
3. Click **"🧪 Use Test Values (Dev Only)"**
4. Click **"Verify License"**
5. **Expected**:
   - "Device Authorized" success screen
   - Redirects to Dashboard after 2s
   - Navbar shows "Live" (green)
   - No console errors

---

## Troubleshooting

### ❌ "Desktop token required" error
**Cause**: Dev bypass not active  
**Fix**: 
1. Check `backend/.env` has `DEBUG=true`
2. Confirm backend logs show "Running in development mode"
3. Restart backend if needed

---

### ❌ Backend shows "Offline" in Navbar
**Cause**: Backend not running or port mismatch  
**Fix**:
1. Visit http://127.0.0.1:8000/health in browser
2. Should return `{"status":"healthy"}`
3. If 404, restart backend

---

### ❌ Can't see "🧪 Use Test Values" button
**Cause**: Not in development mode  
**Fix**: Ensure running `npx tauri dev` (not production build)

---

### ❌ Ctrl+Shift+R doesn't work
**Cause**: App window not focused, or production build  
**Fix**: 
1. Click inside app window first
2. Confirm running in development mode
3. Alternative: Manually clear localStorage in DevTools

---

## Production Behavior (FYI)

When running from **packaged exe** or **production frontend**:
- ❌ No Ctrl+Shift+R shortcut
- ❌ No test credentials button
- ❌ No X-Dev-Mode header sent
- ❌ Backend dev bypass never active (even if DEBUG=true)
- ✅ Full security enforcement
- ✅ Token validation required

---

## Files Changed for T6

See `T6_CLEANUP_SUMMARY.md` for complete details.

**Backend**:
- `backend/middleware/desktop_security.py` - Dev bypass (triple-guarded)
- `backend/desktop_main.py` - Removed auto-DEBUG

**Frontend**:
- `frontend/src/components/Navbar.tsx` - Quiet health logs
- `frontend/src/components/auth/ConnectDevice.tsx` - Dev helpers
- `frontend/src/components/auth/DeviceGuard.tsx` - Reset shortcut

**Docs**:
- `T6_CLEANUP_SUMMARY.md` - Full cleanup report
- `T6_DEV_MODE_IMPLEMENTATION.md` - Dev features (labeled dev-only)
- `T6_TEST_GUIDE.md` - Testing guide (labeled dev-only)

---

## Need Help?

- Full cleanup details: `T6_CLEANUP_SUMMARY.md`
- Test instructions: `T6_TEST_GUIDE.md`
- Implementation notes: `T6_DEV_MODE_IMPLEMENTATION.md`
