# K24 Smoke Tests

## smoke_test.py - End-to-End Pipeline Verification

### Purpose
Verifies the complete "WhatsApp → Cloud → Desktop → Tally" pipeline by:
1. Inserting a test message into the Supabase queue
2. Waiting for the desktop poller to pick it up
3. Verifying it processes successfully

### Schema Details
**Table**: `whatsapp_message_queue`

**Key Columns**:
- `id` (UUID) - Primary key
- `tenant_id` (TEXT) - Tenant identifier
- `sender_phone` (TEXT) - Customer phone number
- `message_content` (TEXT) - Message body
- `status` (TEXT) - Current processing status
  - `pending` - Newly inserted, awaiting pickup
  - `processing` - Desktop poller is working on it
  - `processed` - Successfully completed
  - `failed` - Processing failed
- `error_message` (TEXT) - Error details if failed
- `created_at` (TIMESTAMPTZ) - Insertion timestamp

### Prerequisites

1. **Environment Variables**:
   ```bash
   export SUPABASE_URL="https://your-project.supabase.co"
   export SUPABASE_SERVICE_KEY="your-service-role-key"
   ```

2. **Desktop Poller**: Must be running and configured to poll the same Supabase database

3. **Python Dependencies**:
   ```bash
   pip install supabase
   ```

### Usage

**Basic Usage**:
```bash
python tests/smoke_test.py --tenant-id K24-abc123
```

**With Custom Timeout**:
```bash
python tests/smoke_test.py --tenant-id K24-abc123 --timeout-seconds 180
```

**Help**:
```bash
python tests/smoke_test.py --help
```

### Example Output

**SUCCESS**:
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

**FAILURE**:
```
======================================================================
SMOKE TEST RESULTS
======================================================================
Job ID: 550e8400-e29b-41d4-a716-446655440000
Tenant ID: K24-abc123
Final Status: failed

Status Transitions:
  [2.1s] 19:15:32 → processing
  [5.3s] 19:15:35 → failed

Total Time: 5.3s

❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ 
SMOKE TEST FAIL: Customer mapping not found for phone +919999999999
❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ 
```

### Exit Codes
- `0` - Test passed (status reached `processed`)
- `1` - Test failed (status reached `failed` or timeout)

### Limitations / TODOs

1. **No Tally Verification**: Currently only checks database status transitions. Future version should verify the voucher/ledger was actually created in Tally.

2. **Hardcoded Test Phone**: Uses `+919999999999` as sender. This should match a valid `whatsapp_customer_mappings` entry for the tenant.

3. **Single Environment**: The `--env` flag is informational only. For multi-environment support, you would need separate env var sets like:
   - `STAGING_SUPABASE_URL` / `STAGING_SUPABASE_SERVICE_KEY`
   - `PROD_SUPABASE_URL` / `PROD_SUPABASE_SERVICE_KEY`

### Integration

**CI/CD Pipeline**:
```bash
#!/bin/bash
# Run smoke test in staging before deploying to production

export SUPABASE_URL=$STAGING_SUPABASE_URL
export SUPABASE_SERVICE_KEY=$STAGING_SUPABASE_SERVICE_KEY

python tests/smoke_test.py --tenant-id $STAGING_TENANT_ID --timeout-seconds 180

if [ $? -eq 0 ]; then
    echo "Smoke test passed! Safe to deploy to production."
else
    echo "Smoke test failed! Blocking production deployment."
    exit 1
fi
```

### Troubleshooting

**"Missing Supabase credentials"**:
- Set `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` environment variables

**"Job did not complete within X seconds"**:
- Desktop poller might not be running
- Desktop poller might not be configured for the same database
- Network issues between desktop and Supabase

**"Job failed with error: Customer mapping not found"**:
- The test phone `+919999999999` has no mapping in `whatsapp_customer_mappings`
- Add a test mapping or modify the script to use a real customer phone

**Job stuck in "processing"**:
- Desktop poller crashed during processing
- Desktop poller lost connection to Supabase
- Check desktop logs for errors
