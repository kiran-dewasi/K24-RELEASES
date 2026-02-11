---
description: Start the Celery Worker for Background Tasks
---

To process the Task Queue (Create Ledger, Vouchers, etc.) asynchronously, you need to run a Celery Worker.

## Prerequisites
1. Ensure **Redis** is running (default `localhost:6379`).
2. Ensure `.env` has `REDIS_URL` (optional, defaults to local).
3. Ensure `.env` has `SUPABASE_URL` and `SUPABASE_KEY`.

## Command (Windows)
Since you are on Windows, use `pool=solo` or `threads` to avoid forking issues.

```bash
celery -A backend.celery_app worker --loglevel=info --pool=solo
```

## Verifying
- You should see `[tasks]` listing `backend.tasks.create_ledger_task` and `backend.tasks.create_voucher_task`.
- Logs will show "Connected to redis".
