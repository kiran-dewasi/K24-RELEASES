# M5 Task 2 Complete: Smoke Test Implementation

**Created**: 2026-02-14  
**Status**: ✅ COMPLETE

## Summary

Successfully implemented `tests/smoke_test.py` - an end-to-end smoke test script that verifies the complete "WhatsApp → Cloud → Desktop → Tally" pipeline.

## What Was Built

### 1. Core Script: `tests/smoke_test.py`
- **Purpose**: Automated E2E testing of message processing pipeline
- **Lines of Code**: ~300
- **Dependencies**: `supabase` Python library

### 2. Documentation: `tests/README.md`
- Complete usage guide
- Troubleshooting section
- Example outputs (success/failure)
- CI/CD integration examples

## Technical Details

### Table Used
**`whatsapp_message_queue`** (Supabase)

**Key Columns**:
- `id` (UUID) - Job identifier
- `tenant_id` (TEXT) - Tenant owner
- `sender_phone` (TEXT) - "+919999999999" for tests
- `message_content` (TEXT) - "[SMOKE TEST] ..." payload
- `status` (TEXT) - State machine:
  - `pending` → `processing` → `processed` ✅
  - `pending` → `processing` → `failed` ❌
- `error_message` (TEXT) - Failure reason
- `created_at` (TIMESTAMPTZ) - Insertion time

### Status Flow
```
┌─────────┐    Desktop Polls    ┌────────────┐    Processing    ┌───────────┐
│ pending │ ──────────────────→ │ processing │ ───────────────→ │ processed │
└─────────┘                     └────────────┘                  └───────────┘
                                       │
                                       │ Error
                                       ↓
                                  ┌────────┐
                                  │ failed │
                                  └────────┘
```

## How It Works

1. **Insert**: Creates test job with `status='pending'`
2. **Poll**: Checks status every 2 seconds
3. **Track**: Records all status transitions with timestamps
4. **Result**: 
   - Exit 0 if `status='processed'`
   - Exit 1 if `status='failed'` or timeout

## Usage

### Basic Command
```bash
python tests/smoke_test.py --tenant-id K24-abc123
```

### With Custom Timeout
```bash
python tests/smoke_test.py --tenant-id K24-abc123 --timeout-seconds 180
```

### Environment Variables Required
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="eyJ..."
```

## Example SUCCESS Output

```
======================================================================
K24 SMOKE TEST - WhatsApp Pipeline E2E Verification
======================================================================
Start Time: 2026-02-14 19:15:30
Tenant ID: K24-abc123
Timeout: 120s
======================================================================

📤 Step 1: Inserting test job into queue...
✓ Connected to Supabase: https://xyz.supabase.co
✓ Inserted test job: 550e8400-e29b-41d4-a716-446655440000
  Tenant ID: K24-abc123
  Message: [SMOKE TEST] Automated test job created at 2026-02-14...

📥 Step 2: Waiting for desktop poller to process...

🔄 Polling for status changes (timeout: 120s)...
  [2.1s] Status → processing
  [8.5s] Status → processed

✅ Job completed successfully!

======================================================================
SMOKE TEST RESULTS
======================================================================
Job ID: 550e8400-e29b-41d4-a716-446655440000
Tenant ID: K24-abc123
Final Status: processed

Status Transitions:
  [2.1s] 19:15:32 → processing
  [8.5s] 19:15:38 → processed

Total Time: 8.5s

🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 
SMOKE TEST PASS ✅
🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 
```

## Known Limitations / Future TODOs

### 1. No Tally Verification
**Current**: Only verifies database `status='processed'`  
**Future**: Query Tally API to confirm voucher/ledger was actually created  
**Implementation**: Add `--verify-tally` flag that calls Tally XML API

### 2. Hardcoded Test Phone
**Current**: Uses `+919999999999` as sender  
**Issue**: May not have mapping in `whatsapp_customer_mappings`  
**Solution**: Add `--sender-phone` argument or auto-create temp mapping

### 3. Single Environment
**Current**: `--env` flag is cosmetic  
**Future**: Support `STAGING_*` and `PROD_*` env var prefixes

## Testing Checklist

- [x] Script runs without errors (`--help` works)
- [x] Connects to Supabase successfully
- [x] Inserts test job into queue
- [x] Polls for status changes
- [x] Detects status transitions
- [x] Handles timeout gracefully
- [ ] Live test with desktop poller running (requires active desktop)
- [ ] Live test with intentional failure (bad tenant_id)
- [ ] CI/CD integration (future)

## Integration Points

### Before M5 Staging Deployment
```bash
# In your deployment script:
export SUPABASE_URL=$STAGING_SUPABASE_URL
export SUPABASE_SERVICE_KEY=$STAGING_SUPABASE_SERVICE_KEY

python tests/smoke_test.py --tenant-id $TEST_TENANT_ID --timeout-seconds 180

if [ $? -ne 0 ]; then
    echo "Smoke test failed! Aborting deployment."
    exit 1
fi
```

### Cron Job (Hourly Health Check)
```bash
0 * * * * cd /path/to/k24 && python tests/smoke_test.py --tenant-id K24-monitor --timeout-seconds 60 || alert-team
```

## Files Created

1. `tests/smoke_test.py` (300 lines)
2. `tests/README.md` (documentation)
3. This summary: `M5_SMOKE_TEST_SUMMARY.md`

## Next Steps (M5 Remaining Tasks)

1. ✅ Sentry Monitoring - COMPLETE
2. ✅ Smoke Test Script - COMPLETE (this task)
3. ⏳ Staging Environment Setup
4. ⏳ End-to-End Validation (run smoke_test.py in staging)

## How to Run Live Test

Once desktop poller is running:

```bash
# 1. Set environment variables
export SUPABASE_URL="https://tzcgjtcmbmsgrgofkqua.supabase.co"
export SUPABASE_SERVICE_KEY="<your-service-key>"

# 2. Find your tenant_id
# (from Supabase dashboard or user_profiles table)

# 3. Run smoke test
python tests/smoke_test.py --tenant-id K24-abc123

# Expected: Desktop picks up job within 10 seconds, processes it
```

---

**Author**: Claude (Antigravity)  
**Date**: 2026-02-14  
**Milestone**: M5 - Production Hardening
