# Phase 1: Supabase Schema Setup

This document guides you through setting up the Supabase database schema for the Hybrid Database Architecture.

## 1. SQL Schema

The SQL schema file has been created at:
`backend/database/phase1_schema.sql`

This file contains the definitions for:
- `user_profiles`
- `subscriptions`
- `device_licenses`
- `whatsapp_bindings`
- `whatsapp_customer_mappings`
- `sync_checkpoints`
- Helper functions and triggers for Tenant ID generation.

## 2. How to Apply

Since I cannot access your Supabase Dashboard directly, please follow these steps:

1.  **Open Supabase Dashboard**: Go to [supabase.com/dashboard](https://supabase.com/dashboard) and select your project.
2.  **Go to SQL Editor**: Click on the SQL Editor icon in the left sidebar.
3.  **New Query**: Create a new query.
4.  **Copy & Paste**: Open `backend/database/phase1_schema.sql` in your editor, copy the entire content, and paste it into the Supabase SQL Editor.
5.  **Run**: Click the "Run" button.

## 3. Verification

After running the SQL, you can verify the tables are created by going to the **Table Editor** in Supabase. You should see the new tables listed.

## 4. Backend Integration

The Pydantic models for these new tables have been added to `backend/database/models.py`.
You can now import them in your code:

```python
from backend.database.models import UserProfile, Subscription, DeviceLicense
```

## 5. Next Steps

- **Connect Backend**: Ensure your `.env` file has `SUPABASE_URL` and `SUPABASE_KEY` set correctly.
- **Install Drivers**: If you wish to run migrations programmatically in the future, please install `asyncpg` or `psycopg2-binary`:
  ```bash
  pip install asyncpg
  ```
