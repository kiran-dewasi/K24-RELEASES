# M2 Polling Endpoint Implementation

## ✅ What Was Added

**Endpoint**: `GET /api/whatsapp/jobs/{tenant_id}`

**Location**: `cloud-backend/routers/whatsapp_cloud.py`

**Purpose**: Desktop apps poll this endpoint every 10 seconds to fetch pending WhatsApp messages for their tenant.

---

## 📝 Full Endpoint Code

```python
@router.get("/jobs/{tenant_id}")
async def poll_whatsapp_jobs(
    tenant_id: str,
    limit: int = 10
):
    """
    Poll pending WhatsApp messages for a specific tenant.
    Desktop app uses this to fetch messages from the queue.
    
    Flow:
    1. Desktop app calls GET /api/whatsapp/jobs/{tenant_id}
    2. This endpoint fetches pending messages for that tenant
    3. Atomically updates status to 'processing'
    4. Returns messages to desktop for processing
    5. Desktop processes and calls completion endpoint
    
    Args:
        tenant_id: Tenant ID (from JWT or desktop auth)
        limit: Max messages to fetch (default: 10)
    
    Returns:
        List of pending messages with details
    """
    try:
        logger.info(f"📥 Polling jobs for tenant: {tenant_id}")
        
        supabase = get_supabase_client()
        
        # Step 1: Fetch pending messages for this tenant
        pending_result = supabase.table("whatsapp_message_queue").select(
            "id, tenant_id, user_id, customer_phone, message_type, message_text, media_url, raw_payload, created_at"
        ).eq(
            "tenant_id", tenant_id
        ).eq(
            "status", "pending"
        ).order(
            "created_at", desc=False
        ).limit(
            limit
        ).execute()
        
        if not pending_result.data or len(pending_result.data) == 0:
            logger.info(f"✅ No pending jobs for tenant {tenant_id}")
            return {
                "jobs": [],
                "count": 0,
                "tenant_id": tenant_id
            }
        
        # Step 2: Atomically update fetched messages to 'processing'
        message_ids = [msg["id"] for msg in pending_result.data]
        
        update_result = supabase.table("whatsapp_message_queue").update({
            "status": "processing",
            "processing_started_at": datetime.now(timezone.utc).isoformat()
        }).in_(
            "id", message_ids
        ).execute()
        
        # Step 3: Format response for desktop app
        jobs = []
        for msg in pending_result.data:
            jobs.append({
                "message_id": msg["id"],
                "customer_phone": msg["customer_phone"],
                "message_type": msg["message_type"],
                "text": msg.get("message_text"),
                "media_url": msg.get("media_url"),
                "raw_payload": msg.get("raw_payload", {}),
                "timestamp": msg["created_at"]
            })
        
        logger.info(f"✅ Returned {len(jobs)} jobs for tenant {tenant_id}")
        
        return {
            "jobs": jobs,
            "count": len(jobs),
            "tenant_id": tenant_id
        }
        
    except Exception as e:
        logger.error(f"Error polling jobs for tenant {tenant_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "POLLING_ERROR",
                "detail": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
```

---

## 📤 Expected Response Format

### When Messages Exist
```json
{
  "jobs": [
    {
      "message_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "customer_phone": "+919876543210",
      "message_type": "text",
      "text": "I want to order 10 kg sugar",
      "media_url": null,
      "raw_payload": {},
      "timestamp": "2026-02-12T09:45:23.123456+00:00"
    },
    {
      "message_id": "b2c3d4e5-f678-90ab-cdef-123456789012",
      "customer_phone": "+919988776655",
      "message_type": "image",
      "text": "Here is the bill",
      "media_url": "https://example.com/bill.jpg",
      "raw_payload": {"mimetype": "image/jpeg"},
      "timestamp": "2026-02-12T09:46:15.654321+00:00"
    }
  ],
  "count": 2,
  "tenant_id": "K24-abc123"
}
```

### When Queue is Empty
```json
{
  "jobs": [],
  "count": 0,
  "tenant_id": "K24-abc123"
}
```

### On Error
```json
{
  "detail": {
    "error": "POLLING_ERROR",
    "detail": "Connection timeout to Supabase",
    "timestamp": "2026-02-12T09:47:00.123456+00:00"
  }
}
```

---

## 🧪 Testing with curl

### 1. Test with Empty Queue
```bash
curl -X GET "https://your-cloud-backend.railway.app/api/whatsapp/jobs/K24-test123" \
  -H "Content-Type: application/json"
```

### 2. Insert Test Message First (via Supabase SQL Editor)
```sql
-- Insert a test message
INSERT INTO whatsapp_message_queue (
  tenant_id, 
  customer_phone, 
  message_type, 
  message_text, 
  status
) VALUES (
  'K24-test123',
  '+919876543210',
  'text',
  'Test WhatsApp message',
  'pending'
);
```

### 3. Poll Again (Should Return the Message)
```bash
curl -X GET "https://your-cloud-backend.railway.app/api/whatsapp/jobs/K24-test123" \
  -H "Content-Type: application/json"
```

### 4. Poll Again (Should Be Empty - Message is Now 'processing')
```bash
curl -X GET "https://your-cloud-backend.railway.app/api/whatsapp/jobs/K24-test123" \
  -H "Content-Type: application/json"
```

### 5. Test with Limit Parameter
```bash
curl -X GET "https://your-cloud-backend.railway.app/api/whatsapp/jobs/K24-test123?limit=5" \
  -H "Content-Type: application/json"
```

---

## 🚀 Railway Deployment

### Option 1: Git Push (Automatic)
```bash
cd cloud-backend
git add .
git commit -m "feat: Add GET /api/whatsapp/jobs polling endpoint for M2"
git push origin main
```

Railway will automatically detect the change and redeploy.

### Option 2: Railway CLI
```bash
# Login to Railway
railway login

# Link to your project
railway link

# Deploy
railway up
```

### Option 3: Manual Redeploy via Dashboard
1. Go to https://railway.app/dashboard
2. Select your `cloud-backend` service
3. Click "Deploy" or trigger a manual redeploy

---

## 🔐 Environment Variables Required

Ensure these are set in Railway:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Check in Railway Dashboard → cloud-backend → Variables

---

## ✅ Verification Checklist

- [ ] Endpoint returns `{"jobs": [], "count": 0}` when queue is empty
- [ ] Endpoint returns messages when pending messages exist
- [ ] Messages change from `pending` to `processing` after polling
- [ ] Polling twice does NOT return the same message
- [ ] Multiple tenants get only their own messages
- [ ] Error handling works (test with invalid tenant_id)
- [ ] Limit parameter works (test with `?limit=3`)

---

## 🔜 Next Steps (M2 Continuation)

1. **Add Completion Endpoint**: `POST /api/whatsapp/jobs/{job_id}/complete`
2. **Create Desktop Poller**: `backend/services/whatsapp_poller.py`
3. **Handle Race Conditions**: Upgrade to Supabase RPC with `FOR UPDATE SKIP LOCKED`

---

**Added**: 2026-02-12  
**Status**: ✅ READY FOR TESTING
