# Quick Test Guide - T6 Scenario 1 Device Activation (Dev Mode)

> ⚠️ **FOR LOCAL DEVELOPMENT / QA TESTING ONLY**
> 
> This guide describes dev-only testing procedures and shortcuts.
> Production behavior is different - these dev helpers are NOT available in prod builds.

## Prerequisites ✅
- Desktop backend running on http://127.0.0.1:8000
- Tauri dev app running (npx tauri dev)

## Test Steps

### 1. Reset Device State
**Action**: Press `Ctrl+Shift+R` in the running app

**Expected**:
- Alert message: "✅ Device activation reset! Showing ConnectDevice screen."
- App shows the ConnectDevice activation screen (dark UI with "Connect Device" heading)
- Navbar should show "Live" (green dot) - confirms backend health check works

**If you see**: Dashboard instead of ConnectDevice
- Try `Ctrl+Shift+R` again
- Or manually clear localStorage in DevTools and refresh

---

### 2. Open Manual Entry
**Action**: Click "I have a license key" button

**Expected**:
- Screen slides to manual entry form
- Shows 3 input fields:
  - License Key
  - Tenant ID (optional)
  - User ID (optional)
- Shows yellow "🧪 Use Test Values (Dev Only)" button

---

### 3. Fill Test Credentials
**Action**: Click "🧪 Use Test Values (Dev Only)" button

**Expected**:
- License Key field auto-fills: `TEST_LICENSE_001`
- Tenant ID field auto-fills: `TENANT-e9dbb826`
- User ID field auto-fills: `e9dbb826-5892-43c3-91e6-78900e93f687`

**Alternatively**: Manually type these values if button not visible

---

### 4. Activate Device
**Action**: Click "Verify License" button

**Expected**:
1. Button shows spinning loader: "Validating..."
2. Network request to: `http://127.0.0.1:8000/api/devices/activate`
   - Method: POST
   - Headers: `Content-Type: application/json`, `X-Dev-Mode: true`
   - Body: `{"license_key": "TEST_LICENSE_001", "tenant_id": "TENANT-e9dbb826", "user_id": "e9dbb826-5892-43c3-91e6-78900e93f687"}`

3. **Backend logs (in terminal)** should show:
   ```
   [DEV MODE] Bypassing desktop token validation for /api/devices/activate
   ```

4. Success screen appears:
   - Green checkmark circle
   - "Device Authorized" heading
   - "Starting secure session..." message

5. After 2 seconds:
   - Auto-redirects to dashboard
   - Navbar shows "Live" (green)
   - No "Offline" status

---

## Troubleshooting

### ❌ "Desktop token required" error
**Cause**: Dev mode bypass not working

**Fix**:
- Check backend terminal for DEBUG=true log message
- Restart backend: `python backend/desktop_main.py --port 8000 --token <any-token>`
- Verify DEBUG is auto-set (should see in logs)

---

### ❌ "Subscription expired" or 402 error
**Cause**: Cloud rejects the test license

**Fix**:
- Use different test credentials if available
- Or verify cloud is reachable: https://api.k24.ai/health
- Check backend logs for cloud API response

---

### ❌ Network error / Can't connect
**Cause**: Backend not running or wrong port

**Fix**:
- Verify backend health: http://127.0.0.1:8000/health (should return 200)
- Check if backend terminal is running
- Restart if needed

---

### ❌ Navbar always shows "Offline"
**Cause**: Health check endpoint failing

**Fix**:
- Open browser DevTools → Console
- Look for "Health check failed" errors
- Verify: http://127.0.0.1:8000/health returns 200
- Check CORS if needed

---

### ❌ Can't see "🧪 Use Test Values" button
**Cause**: Not running in development mode

**Fix**:
- Verify you're running `npx tauri dev` (not production build)
- Check console: `process.env.NODE_ENV` should be "development"
- Button only shows in dev mode

---

### ❌ Reset shortcut (Ctrl+Shift+R) not working
**Cause**: Focus not on app window or production build

**Fix**:
- Click inside the app window to focus it
- Try Ctrl+Shift+R again
- Check console for "[DEV] Resetting device activation state..." message
- Shortcut only works in NODE_ENV=development

---

## Success Criteria ✅

**T6 Scenario 1 is complete when**:
- [x] Can press Ctrl+Shift+R to reset and see ConnectDevice screen
- [x] Navbar shows "Live" when backend is running
- [x] Can click "🧪 Use Test Values" to auto-fill credentials
- [x] Activation call includes `X-Dev-Mode: true` header
- [x] Backend logs show "[DEV MODE] Bypassing desktop token validation"
- [x] No "Desktop token required" error (403)
- [x] Activation succeeds (200 from cloud)
- [x] localStorage contains tenant_id and user_id after activation
- [x] UI transitions to dashboard with "Live" status

---

## What NOT to Test
- ❌ PyInstaller builds / installers (M4 T2 - out of scope)
- ❌ Production activation flow (requires real Tauri context)
- ❌ Deep-link activation (different scenario)
- ❌ Other T6 scenarios (stick to Scenario 1 only)

---

## Next Actions After Successful Test
1. Document any issues encountered
2. Verify localStorage state (DevTools → Application → Local Storage)
3. Confirm backend logs show successful activation
4. Take screenshots if needed for documentation
5. **DO NOT** proceed to packaging or other scenarios

---

**Remember**: All changes are DEV MODE ONLY and do not affect production security!
