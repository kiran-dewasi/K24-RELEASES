# Quick Start Guide: Real Tally Integration

## 1. Setup

### Environment Variables
Ensure your `.env` file has the following configurations:
```
TALLY_COMPANY=Krishasales
TALLY_URL=http://localhost:9000
TALLY_TIMEOUT=30
```

### Tally Configuration
1. Open Tally ERP 9 or TallyPrime.
2. Open the company "Krishasales" (or match `TALLY_COMPANY`).
3. Go to **F12: Configure > Advanced Configuration**.
4. Set "Enable ODBC Server" to **Yes**.
5. Set "Port" to **9000**.
6. Restart Tally.

## 2. Diagnostics & Health Check

### Health Endpoint
Navigate to `http://localhost:8000/debug/api/health/tally` to run a full diagnostic scan.

**Expected Output (Healthy):**
```json
{
  "tally_running": true,
  "timestamp": "2024-12-07T12:00:00.000000",
  "diagnostics": [
    {
      "check": "Tally Running Check",
      "status": "OK",
      "details": "Tally responding at http://localhost:9000",
      "remediation": null
    },
    {
      "check": "Company Krishasales Check",
      "status": "OK",
      "details": "Company accessible",
      "remediation": null
    }
  ]
}
```

**If Unhealthy:**
Check the `remediation` field in the response for specific instructions (e.g., "Start Tally ERP/Prime", "Open company 'Krishasales' in Tally").

## 3. Testing Operations

### Create Ledger
You can trigger a ledger creation via the chat interface or directly call the Celery task (for dev):
1. Ask the agent: "Create a customer ledger for 'Test Client' with GSTIN '27AAAAA0000A1Z5'"
2. Verify in Tally: Go to **Gateway of Tally > Accounts Info > Ledgers > Display**.

### Create Voucher
1. Ask the agent: "Record a sale of 5000 to Test Client"
2. Verify in Tally: Go to **Gateway of Tally > Display > Day Book**.

## 4. Monitoring & Troubleshooting

### Operations Log (Supabase)
Check the `tally_operations_log` table in Supabase for a history of all attempts.
- `operation_status`: SUCCESS, FAILED
- `error_decoded`: Human-readable cause and solution.

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| **Connection Refused** | Tally not running or Port 9000 closed | Start Tally, Check Port 9000 in Tally Config. |
| **Company Not Found** | Wrong company open in Tally | Open the correct company specified in `.env`. |
| **Ledger Already Exists** | Duplicate name | Use a unique name or update existing. |
| **Invalid GST** | Wrong format | Ensure GST is 15 chars, starts with state code. |

For detailed error codes, refer to `backend/tally_troubleshoot.py`.
