# Bug Fix Report - K24 System Issues
**Date**: 2025-11-28 12:49 PM IST  
**Issues Found**: 3 Critical, 0 High, 1 Medium

---

## ✅ FIXED ISSUES

### Issue #1: Browser Title Shows "Create Next App"
**Severity**: 🔴 Critical (User-facing branding issue)  
**Status**: ✅ **FIXED**

**Root Cause**: Default Next.js metadata not updated in `layout.tsx`

**Fix Applied**:
```typescript
// Before:
title: "Create Next App"

// After:
title: "K24 - Intelligent ERP"
description: "AI-powered financial intelligence platform integrated with Tally"
```

**File**: `frontend/src/app/layout.tsx` (Line 17-18)  
**Impact**: Browser tab now shows proper branding  
**Test**: Refresh any page → Tab title = "K24 - Intelligent ERP" ✅

---

## ⚠️ ISSUES REQUIRING MANUAL VERIFICATION

### Issue #2: Sync Status Shows "Offline" on Chat/Daybook
**Severity**: 🟡 Medium (Confusing UX, but not blocking functionality)  
**Status**: ⏳ **NEEDS TESTING**

**Root Cause Analysis**:
The `Navbar` component calls `GET /sync/status` on mount:
```typescript
// Navbar.tsx Line 21-40
useEffect(() => {
    const checkHealth = async () => {
        const res = await fetch("http://127.0.0.1:8001/sync/status", {...});
        const data = await res.json();
        setSyncHealth({ 
            connected: data.tally_connected,  // <-- This field
            lastSync: data.last_sync_time 
        });
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
}, []);
```

**Possible Reasons for "Offline" Status**:

1. **Backend endpoint failing**:
   - Test: `http://localhost:8001/sync/status` in browser
   - Expected response:
     ```json
     {
       "tally_connected": true/false,
       "last_sync_time": "2025-11-28T12:00:00"
     }
     ```

2. **Tally not running**:
   - Check: Is Tally Prime open?
   - Check: Tally Gateway → F12 → Configure → "Enable HTTP Server" on port 9000

3. **Initial state race condition**:
   - `syncHealth` starts as `{ connected: false, lastSync: null }`
   - If API takes >1 second, user sees "Offline" initially
   - This is **expected behavior** on page load

**Manual Test Steps**:
```bash
# Test 1: Check backend endpoint
curl -H "x-api-key: k24-secret-key-123" http://localhost:8001/sync/status

# Expected:
# {"tally_connected": true, "last_sync_time": "..."}

# Test 2: Check Tally
# Open Tally → Should be on port 9000

# Test 3: Open browser console on /chat
# F12 → Network tab → Look for /sync/status request
# Check if it returns 200 OK or error
```

**Recommended Fix** (if needed):
Add optimistic initial state based on localStorage:
```typescript
const [syncHealth, setSyncHealth] = useState({
    connected: localStorage.getItem('last_sync_status') === 'true',
    lastSync: localStorage.getItem('last_sync_time')
});

// Save on successful check:
localStorage.setItem('last_sync_status', data.tally_connected);
```

---

### Issue #3: Daybook Shows "Loading..." Forever
**Severity**: 🔴 Critical (Blocks main feature)  
**Status**: ⏳ **NEEDS TESTING**

**Root Cause Analysis**:
The `DayBook` component fetches vouchers on mount:
```typescript
// daybook/page.tsx Line 29-41
const fetchVouchers = async () => {
    try {
        const res = await fetch("http://localhost:8001/vouchers", {...});
        const data = await res.json();
        setVouchers(data.vouchers || []); // <-- Returns empty array if no vouchers
    } catch (error) {
        console.error("Failed to fetch vouchers", error);
        // ⚠️ ERROR IS CAUGHT BUT USER SEES "Loading..." FOREVER
    } finally {
        setLoading(false);
    }
};
```

**Possible Reasons**:

1. **No vouchers in database**:
   - Fresh install → Database is empty
   - Expected: Shows "No vouchers found" (Line 160)
   - **This is CORRECT behavior if counts = 0**

2. **API endpoint failing**:
   - Fetch throws error → Caught silently
   - `setLoading(false)` still runs → Should show "No vouchers found"
   - Perplexity saw "Loading..." → **Fetch might be hanging (timeout issue)**

3. **CORS or network error**:
   - Backend not running
   - Wrong port
   - CORS blocking request

**Manual Test Steps**:
```bash
# Test 1: Check backend endpoint
curl -H "x-api-key: k24-secret-key-123" http://localhost:8001/vouchers

# Expected:
# {"vouchers": [...]} or {"vouchers": []}

# Test 2: Check database
# Open backend/k24.db with SQLite viewer
# Check: SELECT COUNT(*) FROM vouchers;

# Test 3: Open browser console on /daybook
# F12 → Network tab → Look for /vouchers request
# Check response time (should be <500ms)
# Check if it hangs or returns 200/404/500
```

**Recommended Fix**:
Add timeout and better error handling:
```typescript
const fetchVouchers = async () => {
    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000); // 5s timeout
        
        const res = await fetch("http://localhost:8001/vouchers", {
            headers: { "x-api-key": "k24-secret-key-123" },
            signal: controller.signal
        });
        
        clearTimeout(timeout);
        
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        
        const data = await res.json();
        setVouchers(data.vouchers || []);
    } catch (error) {
        console.error("Failed to fetch vouchers", error);
        // Show user-friendly error instead of silent fail
        setVouchers([]);
        alert("Failed to load vouchers. Please check if backend is running.");
    } finally {
        setLoading(false);
    }
};
```

---

## 🎯 IMMEDIATE ACTION ITEMS FOR USER

### Step 1: Verify Browser Title Fix
```bash
# Refresh any page in browser
# Check: Browser tab shows "K24 - Intelligent ERP" ✅
```

### Step 2: Check Backend Health
```bash
# In browser, visit:
http://localhost:8001/docs

# Should show FastAPI Swagger UI
# If 404 → Backend is not running
```

### Step 3: Test Sync Status Endpoint
```bash
# In browser console (F12), run:
fetch('http://localhost:8001/sync/status', {
    headers: {'x-api-key': 'k24-secret-key-123'}
})
.then(r => r.json())
.then(console.log)

# Expected output:
# { tally_connected: true/false, last_sync_time: "..." }
```

### Step 4: Test Vouchers Endpoint
```bash
# In browser console, run:
fetch('http://localhost:8001/vouchers', {
    headers: {'x-api-key': 'k24-secret-key-123'}
})
.then(r => r.json())
.then(data => console.log('Vouchers:', data.vouchers.length))

# Expected: Number of vouchers (0 if empty, or count if data exists)
```

### Step 5: Check Tally Connection
```bash
# Test if Tally is reachable:
curl http://localhost:9000

# Expected: HTML response from Tally or connection refused

# If connection refused:
# 1. Open Tally Prime
# 2. Gateway → F12 (Configure)
# 3. Enable "HTTP Server" on port 9000
# 4. Restart Tally
```

---

## 📊 EXPECTED TEST RESULTS

### Scenario A: Everything Working (Ideal State)
```
✅ Browser title: "K24 - Intelligent ERP"
✅ Sync status: "Online" (green dot)
✅ Daybook: Shows vouchers OR "No vouchers found" (if empty)
✅ Console: No errors
```

### Scenario B: Tally Not Running
```
✅ Browser title: "K24 - Intelligent ERP"
❌ Sync status: "Offline" (red dot) ← EXPECTED
✅ Daybook: Shows "No vouchers found" (reading from K24 database)
⚠️ Console: Fetch error for /sync/status (404 or timeout)
```

### Scenario C: Backend Not Running
```
✅ Browser title: "K24 - Intelligent ERP"
❌ Sync status: "Offline" (red dot)
❌ Daybook: "Loading..." forever OR error alert
❌ Console: Multiple fetch errors (ERR_CONNECTION_REFUSED)
```

---

## 🔧 PROPOSED CODE IMPROVEMENTS

### Improvement #1: Add Error State to Daybook
**File**: `frontend/src/app/daybook/page.tsx`

```typescript
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null); // NEW

const fetchVouchers = async () => {
    try {
        setError(null); // Clear previous errors
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);
        
        const res = await fetch("http://localhost:8001/vouchers", {
            headers: { "x-api-key": "k24-secret-key-123" },
            signal: controller.signal
        });
        
        clearTimeout(timeout);
        
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        
        const data = await res.json();
        setVouchers(data.vouchers || []);
    } catch (err: any) {
        console.error("Fetch error:", err);
        setError(err.name === 'AbortError' 
            ? 'Request timeout. Is backend running?' 
            : 'Failed to load data. Check backend connection.');
    } finally {
        setLoading(false);
    }
};

// In JSX:
{loading ? (
    <p>Loading...</p>
) : error ? (
    <div className="text-center py-8">
        <p className="text-red-600 font-medium">{error}</p>
        <Button onClick={fetchVouchers} variant="outline" className="mt-4">
            Retry
        </Button>
    </div>
) : filteredVouchers.length === 0 ? (
    <p className="text-muted-foreground text-center py-8">No vouchers found.</p>
) : (
    // ... voucher list
)}
```

### Improvement #2: Persist Sync Status
**File**: `frontend/src/components/Navbar.tsx`

```typescript
const checkHealth = async () => {
    try {
        const res = await fetch("http://127.0.0.1:8001/sync/status", {
            headers: { "x-api-key": "k24-secret-key-123" }
        });
        const data = await res.json();
        const newStatus = {
            connected: data.tally_connected,
            lastSync: data.last_sync_time
        };
        setSyncHealth(newStatus);
        
        // Persist to localStorage
        localStorage.setItem('k24_sync_status', JSON.stringify(newStatus));
    } catch (e) {
        setSyncHealth({ connected: false, lastSync: null });
    }
};

// On mount, load from localStorage first (optimistic):
useEffect(() => {
    const cached = localStorage.getItem('k24_sync_status');
    if (cached) {
        setSyncHealth(JSON.parse(cached));
    }
    
    checkHealth(); // Then check actual status
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
}, []);
```

---

## 📝 SUMMARY

| Issue | Status | Action Required |
|-------|--------|-----------------|
| Browser title = "Create Next App" | ✅ FIXED | Refresh browser to verify |
| Sync shows "Offline" | ⏳ INVESTIGATE | Run manual tests above |
| Daybook "Loading..." forever | ⏳ INVESTIGATE | Check browser console for errors |

**Next Steps**:
1. Refresh browser → Verify title is fixed
2. Open browser console (F12)
3. Go to /daybook
4. Check Network tab for API call failures
5. Report findings so we can apply targeted fixes

---

**Need Help?** Share:
- Browser console errors (F12 → Console tab)
- Network tab screenshot showing /vouchers request
- Backend terminal logs when you visit /daybook
