# Fix: tenant_id Type Bug - Summary

## Problem
`TypeError: 'int' object is not subscriptable` occurred when tenant_id came from Supabase webhook as an integer (bigint type) but the code tried to slice it like a string: `tenant_id[:8]`

## Root Cause
Supabase `presale_orders.id` is a `bigint` column, so webhook payloads send `record["id"]` as an **integer**, not a string.

## Solution
Normalize `tenant_id` to string **immediately** after extraction, then use it consistently throughout.

---

## Changes Made

### 1. **File: `cloud-backend/routers/webhooks.py`**

#### Change 1: Normalize tenant_id to string (lines 103-108)
**Before:**
```python
# Extract tenant_id
tenant_id = record.get("id")
if not tenant_id:
    logger.error("❌ Missing id (tenant_id) in record")
    raise HTTPException(status_code=400, detail="Missing tenant_id in record")
```

**After:**
```python
# Extract tenant_id and normalize to string (may be int from Supabase bigint)
raw_tenant_id = record.get("id")
if not raw_tenant_id:
    logger.error("❌ Missing id (tenant_id) in record")
    raise HTTPException(status_code=400, detail="Missing tenant_id in record")
tenant_id = str(raw_tenant_id)
```

#### Change 2: Fix logging when missing whatsapp_number (lines 111-116)
**Before:**
```python
logger.info(f"✅ Ignoring record with missing whatsapp_number: tenant_id={tenant_id[:8]}...")
```

**After:**
```python
logger.info(
    "✅ Ignoring record with missing whatsapp_number: tenant_id=%s...",
    tenant_id[:8]
)
```

#### Change 3: Fix processing log (lines 123-127)
**Before:**
```python
logger.info(f"📝 Processing tenant sync: tenant_id={tenant_id[:8]}..., whatsapp={masked_whatsapp}")
```

**After:**
```python
logger.info(
    "📝 Processing tenant sync: tenant_id=%s..., whatsapp=%s",
    tenant_id[:8],
    masked_whatsapp
)
```

#### Change 4: Fix success log (lines 184-188)
**Before:**
```python
logger.info(f"✅ Tenant synced successfully: tenant_id={tenant_id[:8]}..., whatsapp={masked_whatsapp}")
```

**After:**
```python
logger.info(
    "✅ Tenant synced successfully: tenant_id=%s..., whatsapp=%s",
    tenant_id[:8],
    masked_whatsapp
)
```

---

### 2. **File: `cloud-backend/tests/test_tenant_sync_webhook.py`**

#### Added: New test case (after line 99)

```python
def test_sync_integer_tenant_id(self, mock_env_webhook_secret, mock_supabase):
    """Test that integer tenant_id (from Supabase bigint) is handled correctly"""
    # Mock k24-main Supabase client
    mock_client = Mock()
    mock_supabase.return_value = mock_client
    
    # Mock select (no existing record)
    mock_select_table = Mock()
    mock_client.table.return_value = mock_select_table
    
    mock_select = Mock()
    mock_select_table.select.return_value = mock_select
    
    mock_eq = Mock()
    mock_select.eq.return_value = mock_eq
    
    mock_eq.execute.return_value = Mock(data=[])  # No existing record
    
    # Mock upsert
    mock_upsert = Mock()
    mock_select_table.upsert.return_value = mock_upsert
    
    mock_upsert.execute.return_value = Mock(data=[{
        "tenant_id": "13",  # Should be string
        "whatsapp_number": TEST_WHATSAPP,
        "user_email": TEST_EMAIL,
        "subscription_status": "trial"
    }])
    
    # Make request with INTEGER tenant_id (like Supabase bigint)
    response = client.post(
        "/api/webhooks/tenant-sync",
        json={
            "type": "INSERT",
            "table": "presale_orders",
            "schema": "public",
            "record": {
                "id": 13,  # INTEGER not string
                "whatsapp_number": TEST_WHATSAPP,
                "email": TEST_EMAIL
            }
        },
        headers={"X-Webhook-Secret": VALID_WEBHOOK_SECRET}
    )
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "synced"
    assert data["tenant_id"] == "13"  # Should be normalized to string
    
    # Verify that upsert was called with STRING tenant_id
    call_args = mock_select_table.upsert.call_args
    upsert_payload = call_args[0][0]
    assert upsert_payload["tenant_id"] == "13"  # Must be string, not int
    assert isinstance(upsert_payload["tenant_id"], str)
```

---

## Benefits of Changes

1. **Type Safety**: tenant_id is now always a string throughout the endpoint
2. **No TypeError**: String slicing `tenant_id[:8]` now works for both int and string inputs
3. **Performance**: Parameterized logging (`logger.info("msg %s", var)`) is faster than f-strings
4. **Consistency**: All logging uses the same parameterized format
5. **Database Compatibility**: Supabase receives consistent string tenant_id in upsert payload

---

## Test Results

### Manual Test (Verified)
```bash
$ python cloud-backend/test_tenant_id_fix.py
✅ Test 1 PASS: tenant_id[:8] = '13'
✅ Test 2 PASS: tenant_id[:8] = 'tenant_a'
INFO:__main__:📝 Processing tenant sync: tenant_id=13..., whatsapp=****7890
✅ Test 3 PASS: Parameterized logging works

🎉 All manual tests passed!
```

### Automated Test
- **New test**: `test_sync_integer_tenant_id` 
- **Verifies**: Integer tenant_id (13) → normalized to string → upsert uses "13"
- **Asserts**: No TypeError, correct type in database payload

---

## Deployment Notes

- **No environment variable changes needed**
- **No database schema changes needed**
- **Backwards compatible**: String tenant_ids still work exactly as before
- **Production safe**: Minimal diff, only fixes the bug

---

## Files Changed

1. `cloud-backend/routers/webhooks.py` - 4 changes (normalization + 3 logging fixes)
2. `cloud-backend/tests/test_tenant_sync_webhook.py` - 1 addition (new test case)

**Total lines changed**: ~30 lines  
**Risk level**: **Low** (defensive fix, backwards compatible)
