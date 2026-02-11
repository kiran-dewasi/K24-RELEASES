# 🚀 Tally Sync - Quick Reference

## Start Background Sync Service

```python
# Add to backend/api.py
from contextlib import asynccontextmanager
from backend.services import tally_sync_service
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    sync_task = asyncio.create_task(tally_sync_service.start())
    yield
    # Shutdown
    await tally_sync_service.stop()
    sync_task.cancel()

app = FastAPI(lifespan=lifespan)
```

## API Endpoints

```bash
# Comprehensive Sync
POST /api/sync/comprehensive
Body: {"mode": "incremental"}  # or "full"

# Status & Health
GET  /api/sync/comprehensive/status
GET  /api/sync/stats
GET  /api/sync/health

# Targeted Syncs
POST /api/sync/ledgers/complete
POST /api/sync/items/complete
POST /api/sync/bills
POST /api/sync/movements/{item_name}

# Activity Tracking
POST /api/sync/activity
```

## Python Usage

```python
from backend.services import sync_now, get_sync_status, tally_sync_service

# Manual sync
result = await sync_now(mode="incremental")  # or "full"

# Get status
status = await get_sync_status()

# Get statistics
stats = tally_sync_service.get_stats()

# Mark activity (switch to 5s interval)
tally_sync_service.mark_activity()
```

## Frontend Integration

```typescript
// Trigger sync
async function syncNow(mode = 'incremental') {
  const res = await fetch('/api/sync/comprehensive', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode })
  });
  return await res.json();
}

// Get status
async function getSyncStatus() {
  const res = await fetch('/api/sync/comprehensive/status');
  return await res.json();
}

// Mark activity on any user interaction
async function markActivity() {
  await fetch('/api/sync/activity', { method: 'POST' });
}

// Auto-mark activity on page interactions
document.addEventListener('click', () => markActivity());
```

## Key Features

✅ **Auto Sync:** 5s (active) / 5min (idle)  
✅ **Retry Logic:** 3 attempts with exponential backoff  
✅ **360° Data:** Ledgers, Items, Bills, Movements  
✅ **Health Monitoring:** Status, stats, error tracking  
✅ **Non-Blocking:** Async operations  

## Files Location

```
backend/
├── tally_connector.py      # 8 new fetch methods
├── sync_engine.py           # 5 new sync methods
├── services/
│   ├── tally_sync_service.py   # Background service (NEW)
│   └── __init__.py              # Service exports
└── routers/
    └── sync.py              # 9 new API endpoints

Documentation:
├── TALLY_SYNC_AUDIT.md
├── TALLY_SYNC_SERVICE_GUIDE.md
└── IMPLEMENTATION_SUMMARY.md
```

## Common Scenarios

### Initial Setup
```python
# Run once to populate all data
await sync_now(mode="full")
```

### Daily Operations
```python
# Background service handles this automatically
# Or trigger manually:
await sync_now(mode="incremental")
```

### Check Health
```python
status = await get_sync_status()
print(f"Tally: {'🟢 Online' if status['tally_online'] else '🔴 Offline'}")
```

### Monitor Performance
```python
stats = tally_sync_service.get_stats()
print(f"Success Rate: {stats['success_rate']:.1f}%")
```

---

**🎯 Everything is ready! Start the background service and enjoy real-time Tally sync.**
