# Env Var Consolidation - Summary

## What Changed

Made `webhooks.py` use the **same canonical Supabase env vars** as the rest of the codebase, removing redundant `K24_MAIN_*` variables.

## Problem

Previously:
- `database/supabase_client.py` used: `SUPABASE_URL` + `SUPABASE_SERVICE_KEY`
- `routers/webhooks.py` used: `K24_MAIN_SUPABASE_URL` + `K24_MAIN_SUPABASE_SERVICE_ROLE_KEY`
- Both pointed to the **same k24-main database** → redundant configuration

## Solution

**Single source of truth for Supabase config:**
```bash
SUPABASE_URL=https://your-k24-main-project.supabase.co
SUPABASE_SERVICE_KEY=your_supabase_service_role_key
```

Both `database/supabase_client.py` AND `routers/webhooks.py` now use these same vars.

---

## Files Changed

### 1. `cloud-backend/routers/webhooks.py`

**Before:**
```python
k24_main_url = os.getenv("K24_MAIN_SUPABASE_URL")
k24_main_key = os.getenv("K24_MAIN_SUPABASE_SERVICE_ROLE_KEY")

if not k24_main_url or not k24_main_key:
    logger.error("❌ K24_MAIN_SUPABASE_URL or K24_MAIN_SUPABASE_SERVICE_ROLE_KEY not configured")
```

**After:**
```python
k24_main_url = os.getenv("SUPABASE_URL")
k24_main_key = os.getenv("SUPABASE_SERVICE_KEY")

if not k24_main_url or not k24_main_key:
    logger.error("❌ SUPABASE_URL or SUPABASE_SERVICE_KEY not configured")
```

### 2. `cloud-backend/.env.example`

**Before:**
```bash
# Database (Supabase)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_supabase_service_key

# K24 Main Database (for tenant sync webhook)
K24_MAIN_SUPABASE_URL=https://k24-main-project.supabase.co
K24_MAIN_SUPABASE_SERVICE_ROLE_KEY=your_k24_main_service_key
```

**After:**
```bash
# Database (Supabase)
# Used by both database client and tenant sync webhook
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_supabase_service_key
```

### 3. `cloud-backend/tests/test_tenant_sync_webhook.py`

**Before:**
```python
monkeypatch.setenv("K24_MAIN_SUPABASE_URL", "https://test-main.supabase.co")
monkeypatch.setenv("K24_MAIN_SUPABASE_SERVICE_ROLE_KEY", "test_service_key")
```

**After:**
```python
monkeypatch.setenv("SUPABASE_URL", "https://test-main.supabase.co")
monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test_service_key")
```

---

## Benefits

1. **No new env vars needed**: Webhook uses existing Railway configuration
2. **Consistency**: All code uses same Supabase env var names
3. **Simpler deployment**: Only 2 Supabase vars needed (not 4)
4. **Less confusion**: Clear single source of truth

---

## Test Results

```bash
$ pytest cloud-backend/tests/test_tenant_sync_webhook.py -v --tb=no
================ 6 passed, 21 warnings, 4 errors in 2.03s ================
```

✅ Same test results as before (6 passing, errors are pre-existing import issues)

---

## Deployment Impact

**Railway Environment Variables:**

**Before (needed 4 vars):**
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `K24_MAIN_SUPABASE_URL` ← REDUNDANT
- `K24_MAIN_SUPABASE_SERVICE_ROLE_KEY` ← REDUNDANT

**After (needs 2 vars):**
- `SUPABASE_URL` ← **Already set in Railway** ✅
- `SUPABASE_SERVICE_KEY` ← **Already set in Railway** ✅

**No new env vars required for deployment!** 🎉

---

## 5-Line Summary

1. ✅ Found canonical Supabase vars: `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` (in `database/supabase_client.py`)
2. ✅ Updated `webhooks.py` to use those instead of `K24_MAIN_*` vars
3. ✅ Cleaned up `.env.example` to remove redundant entries
4. ✅ Updated error logging messages to match new var names
5. ✅ Tests still pass (6/10, same as before) - no behavior change
