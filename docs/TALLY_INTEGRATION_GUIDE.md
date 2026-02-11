# K24 Tally Integration - Quick Start & Troubleshooting

## Quick Start: Testing Tally Connection

To verify that the K24 backend can talk to your running Tally ERP 9 instance:

1. **Ensure Tally is Running:**
   - Open Tally ERP 9 or TallyPrime.
   - Load the company named `Krishasales` (or whatever is set in your `.env`).
   - Enable ODBC Server / HTTP Port:
     - Go to **F12: Configure** > **Advanced Configuration**.
     - Set **Enable ODBC Server** to **Yes**.
     - Set **Port** to `9000`.

2. **Check Health Endpoint:**
   - Open your browser or Postman.
   - Navigate to: `http://localhost:8000/api/health/tally`
   - You should see:
     ```json
     {
       "status": "online",
       "tally_running": true,
       "url": "http://localhost:9000",
       "code": 200,
       "timestamp": "..."
     }
     ```

3. **Run a Test Chat Command:**
   - In the K24 Chat: "Create a customer named IntegrationTestCorp"
   - Confirm with "Yes".
   - Watch the Celery terminal logs for `🚀 Pushing to Tally: IntegrationTestCorp`.
   - Check Tally to see if the ledger appeared.

## Troubleshooting Common Errors

### 1. Connection Refused / "Offline" Status
**Error:** `requests.exceptions.ConnectionError` or `/api/health/tally` returns `offline`.
**Cause:** Tally is not running, or not listening on port 9000.
**Fix:**
   - Check if Tally is open.
   - Verify port in **F12 > Advanced Config**.
   - If port 9000 is blocked, change to 9001 in Tally and update `.env`: `TALLY_URL=http://localhost:9001`.

### 2. "Tally Ignored the Update"
**Error:** `TallyIgnoredError` or status `IGNORED`.
**Cause:**
   - You are trying to create a master that already exists (e.g., Ledger name duplicate).
   - You are trying to modify a record without providing the original Name/GUID.
   - The Tally company is closed or in a menu that blocks import.
**Fix:**
   - Check Tally's "Calculator Panel" (Ctrl+N) at the bottom for specific error messages (e.g., "Name already exists").
   - Ensure you are on the "Gateway of Tally" screen.

### 3. "Tally Rejected: Line Error"
**Error:** `TallyXMLValidationError` or `TallyAPIError` with details like "Line Error".
**Cause:**
   - Missing mandatory field (e.g., Parent Group).
   - Invalid Date format (Must be YYYYMMDD).
   - Totals do not match (Dr != Cr) in a voucher.
**Fix:**
   - Check the `celery` logs. We print detailed error messages returned by Tally.
   - Ensure `Date` is passed correctly.

### 4. "No such company"
**Cause:**
   - The company name in `.env` (`TALLY_COMPANY`) does not match the open company in Tally.
**Fix:**
   - Update `.env` to match exactly (case-sensitive sometimes).
