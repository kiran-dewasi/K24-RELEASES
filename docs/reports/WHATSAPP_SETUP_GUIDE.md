# WhatsApp Integration Setup Guide

## 1. Meta Business Suite Setup

1.  **Create App**: Go to [Meta Developers](https://developers.facebook.com/), create a new app type **Business**.
2.  **Add Product**: Select **WhatsApp** > **Set up**.
3.  **API Setup**:
    *   **Phone Number**: Adds your testing number (or use provided Test Number).
    *   **Phone ID**: Copy `Phone Request ID` -> Set as `WHATSAPP_BUSINESS_PHONE_ID`.
    *   **Token**: Copy `Temporary Access Token` (24h) or configured System User Token -> Set as `WHATSAPP_API_TOKEN`.
    *   **Account ID**: Copy `WhatsApp Business Account ID` -> Set as `WHATSAPP_BUSINESS_ACCOUNT_ID` (optional for sending, good for analytics).

## 2. Environment Configuration

Update your `.env` file with credentials from Step 1:

```ini
WHATSAPP_BUSINESS_PHONE_ID=1234567890
WHATSAPP_API_TOKEN=EAAB...
WHATSAPP_APP_SECRET=a1b2c3... (From App Dashboard > Settings > Basic)
WHATSAPP_VERIFY_TOKEN=k24_verify_token (Arbitrary, must match Step 3)
```

## 3. Webhook Configuration

### 3a. Local Testing (ngrok)
1.  Install ngrok and expose port 8000:
    ```bash
    ngrok http 8000
    ```
2.  Copy the HTTPS URL (e.g., `https://abc-123.ngrok-free.app`).

### 3b. Meta Dashboard
1.  Go to **WhatsApp** > **Configuration**.
2.  Click **Edit** button under Webhook.
3.  **Callback URL**: `https://your-ngrok-url/api/whatsapp/webhook`
4.  **Verify Token**: `k24_verify_token` (Matches `.env`).
5.  Click **Verify and Save**. Ee sure your backend is RUNNING (`uvicorn backend.api:app --reload`).

### 3c. Subscribe to Fields
1.  Under "Webhook fields", click **Manage**.
2.  Subscribe to `messages`.

## 4. Database Setup

Run the migration script `backend/database/whatsapp_migrations.sql` in Supabase SQL Editor.
This creates `whatsapp_raw_messages`, `user_whatsapp_mapping` and adds columns to `messages`.

## 5. Verification

1.  **Send Message**: Send "Hello" to the WhatsApp Test Number.
2.  **Check Tally**: The agent should respond. If the agent knows Tally tools, ask "Create a ledger for Test User".
3.  **Check Logs**: Look at `whatsapp_raw_messages` table in Supabase.
4.  **Debug Endpoint**: Check `http://localhost:8000/docs`.

## 6. Common Issues

*   **403 Verification Failed**: Check `WHATSAPP_VERIFY_TOKEN` matches in `.env` and Meta Dashboard.
*   **401 Invalid Signature**: Check `WHATSAPP_APP_SECRET`.
*   **No Response**: Check Celery worker logs. Ensure `process_whatsapp_message` task is registered and running.
