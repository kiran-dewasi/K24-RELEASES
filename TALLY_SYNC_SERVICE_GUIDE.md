# Tally Background Sync Service - Implementation Guide

## Overview

The Tally Background Sync Service provides **real-time synchronization** between Tally ERP and the K24 Shadow Database. It runs continuously in the background with adaptive intervals based on user activity.

## Features

✅ **Adaptive Sync Intervals**
- Active Mode: Every 5 seconds (when user is active)
- Idle Mode: Every 5 minutes (when user is inactive for >5 min)

✅ **Comprehensive Data Sync**
- Ledgers (basic & complete with contact details)
- Vouchers (incremental & full)
- Stock Items (basic & complete with HSN/GST)
- Outstanding Bills (receivables/payables)
- Stock Movements (optional)

✅ **Resilient & Reliable**
- Automatic retry with exponential backoff
- Error handling and logging
- Health monitoring
- Statistics tracking

✅ **Non-Blocking Async**
- Runs in background without blocking main thread
- Uses thread pool for CPU-intensive Tally operations

---

## Installation

The service is already created at:
```
backend/services/tally_sync_service.py
```

No additional dependencies needed - uses existing `sync_engine` and `tally_connector`.

---

## Usage

### Method 1: Start as Background Service

```python
import asyncio
from backend.services import start_sync_service, stop_sync_service

# Start the service (runs continuously)
async def main():
    # This will run forever until stopped
    await start_sync_service()

# Run it
asyncio.run(main())
```

### Method 2: Manual Sync Triggers

```python
import asyncio
from backend.services import sync_now, get_sync_status

async def manual_sync():
    # Trigger immediate incremental sync (last 24h)
    result = await sync_now(mode="incremental")
    print(result)
    
    # Or full comprehensive sync
    result = await sync_now(mode="full")
    print(result)

asyncio.run(manual_sync())
```

### Method 3: Integrated with FastAPI

Add to your FastAPI app startup:

```python
# backend/api.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.services import tally_sync_service
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start sync service
    sync_task = asyncio.create_task(tally_sync_service.start())
    yield
    # Shutdown: Stop sync service
    await tally_sync_service.stop()
    sync_task.cancel()

app = FastAPI(lifespan=lifespan)
```

---

## API Endpoints (Optional)

Add these endpoints to expose sync service via API:

```python
# backend/routers/sync.py

from fastapi import APIRouter
from backend.services import tally_sync_service, sync_now, get_sync_status

router = APIRouter(prefix="/sync", tags=["Tally Sync"])

@router.post("/trigger")
async def trigger_sync(mode: str = "incremental"):
    """
    Trigger immediate sync
    
    Args:
        mode: "incremental" (default) or "full"
    """
    result = await sync_now(mode=mode)
    return {"status": "success", "result": result}

@router.get("/status")
async def get_status():
    """Get sync service status and statistics"""
    return await get_sync_status()

@router.get("/stats")
async def get_statistics():
    """Get detailed sync statistics"""
    return tally_sync_service.get_stats()

@router.post("/activity")
async def mark_activity():
    """Mark user activity to switch to active sync mode"""
    tally_sync_service.mark_activity()
    return {"status": "Activity marked", "mode": "ACTIVE"}
```

Then add to your main API:

```python
# backend/api.py
from backend.routers import sync

app.include_router(sync.router)
```

---

## Configuration

### Environment Variables

```bash
# .env
TALLY_URL=http://localhost:9000
TALLY_COMPANY=Your Company Name
```

### Customize Intervals

```python
from backend.services.tally_sync_service import TallySyncService

# Create custom service with different intervals
custom_sync = TallySyncService(
    interval_active=10,   # 10 seconds when active
    interval_idle=600     # 10 minutes when idle
)
```

---

## Sync Modes

### Incremental Sync (Default)
- Syncs only last 24 hours of data
- Faster, recommended for continuous background sync
- Updates: Ledgers, Stock Items, Recent Vouchers, Bills

```python
result = await sync_now(mode="incremental")
```

### Full Comprehensive Sync
- Syncs entire financial year
- Includes all masters, transactions, bills
- Slower but complete
- Use for initial setup or periodic deep sync

```python
result = await sync_now(mode="full")
```

---

## Monitoring & Health Checks

### Get Sync Status

```python
from backend.services import get_sync_status

status = await get_sync_status()
print(status)
# {
#   "service_running": True,
#   "tally_online": True,
#   "last_sync": "2026-01-28T06:00:00",
#   "stats": {
#     "total_syncs": 150,
#     "successful_syncs": 148,
#     "failed_syncs": 2,
#     "last_error": None
#   },
#   "mode": "ACTIVE"
# }
```

### Get Statistics

```python
from backend.services import tally_sync_service

stats = tally_sync_service.get_stats()
print(stats)
# {
#   "total_syncs": 150,
#   "successful_syncs": 148,
#   "failed_syncs": 2,
#   "last_error": None,
#   "last_sync_time": "2026-01-28T06:00:00",
#   "is_running": True,
#   "success_rate": 98.67
# }
```

---

## Running as Standalone Service

You can run the sync service as a standalone process:

```bash
# From project root
python -m backend.services.tally_sync_service
```

Output:
```
🚀 Starting Tally Background Sync Service
Press Ctrl+C to stop
🔄 Tally Sync Service Started
🔄 Sync Mode: ACTIVE (interval: 5s)
✅ Sync complete in 2.3s
🔄 Sync Mode: ACTIVE (interval: 5s)
✅ Sync complete in 1.8s
...
```

---

## Logging

The service uses Python's standard logging. Configure in your app:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Log output:
```
2026-01-28 06:00:00 - backend.services.tally_sync_service - INFO - 🔄 Tally Sync Service Started
2026-01-28 06:00:02 - backend.services.tally_sync_service - INFO - ✅ Sync complete in 2.1s
2026-01-28 06:00:02 - backend.sync_engine - DEBUG - 📊 Ledgers synced: {'synced': 150, 'errors': 0}
```

---

## Error Handling

The service automatically handles errors:

1. **Tally Offline**: Waits 30 seconds, then retries
2. **Network Issues**: Automatic retry with exponential backoff
3. **Database Errors**: Logged, sync continues
4. **Unexpected Errors**: Caught, logged, service keeps running

---

## Performance Considerations

### Active Mode (5s interval)
- Suitable for real-time usage
- Low overhead (~1-2s per sync)
- Ideal for dashboard views

### Idle Mode (5min interval)
- Reduces load when user is inactive
- Automatically switches based on last activity

### Mark User Activity

Call `mark_activity()` whenever user interacts:

```python
from backend.services import tally_sync_service

# On any user action (API call, page load, etc.)
tally_sync_service.mark_activity()
```

---

## Advanced Usage

### Custom Sync Logic

```python
from backend.services import tally_sync_service

# Sync only specific data
async def sync_only_ledgers():
    result = await tally_sync_service.sync_ledgers_complete()
    return result

# Sync stock movements for specific item
async def sync_item_movements(item_name: str):
    result = await tally_sync_service.sync_stock_movements(item_name)
    return result
```

### Conditional Sync

```python
from datetime import datetime
from backend.services import tally_sync_service

# Only sync during business hours
async def smart_sync():
    now = datetime.now()
    if 9 <= now.hour <= 18:  # 9 AM to 6 PM
        await tally_sync_service.sync_all(mode="incremental")
    else:
        await tally_sync_service.sync_all(mode="full")
```

---

## Integration Examples

### Frontend Integration

```typescript
// React/Next.js example
async function triggerSync() {
  const response = await fetch('/api/sync/trigger', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: 'incremental' })
  });
  const result = await response.json();
  console.log('Sync result:', result);
}

// Get sync status for UI
async function getSyncStatus() {
  const response = await fetch('/api/sync/status');
  const status = await response.json();
  return status;
}
```

### Celery Background Task

```python
# backend/tasks.py
from celery import shared_task
import asyncio
from backend.services import sync_now

@shared_task
def periodic_tally_sync():
    """Celery task for periodic sync"""
    asyncio.run(sync_now(mode="full"))
```

---

## Troubleshooting

### Service Not Starting

1. Check Tally is running and accessible
2. Verify TALLY_URL in .env
3. Check logs for errors

### Sync Failing

```python
from backend.services import get_sync_status

status = await get_sync_status()
print(status['stats']['last_error'])
```

### Performance Issues

- Reduce sync frequency
- Use incremental mode instead of full
- Check Tally server performance

---

## Summary

✅ **Created**: `backend/services/tally_sync_service.py`  
✅ **Features**: Real-time sync, adaptive intervals, health monitoring  
✅ **Modes**: Incremental (24h) & Full (complete)  
✅ **Integration**: FastAPI, Standalone, or Manual triggers  
✅ **Monitoring**: Status checks, statistics, error tracking  

The background sync service is production-ready and can be started immediately!
