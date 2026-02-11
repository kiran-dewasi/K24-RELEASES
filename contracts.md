# K24 System Contracts (Phase 1)

Purpose: Define clear boundaries between cloud, desktop, and Tally so agents do not improvise protocols.

---

## 1. Cloud ↔ Desktop – WhatsApp Message Queue

### 1.1 Baileys → Cloud Webhook

- Endpoint: `POST /api/whatsapp/cloud/incoming`
- Auth: shared secret header `X-Baileys-Secret`.
- Request JSON (simplified):

```json
{
  "from_number": "string",          // customer WhatsApp number
  "to_number": "string",            // our business number
  "message_type": "text|image|doc",
  "text": "optional string",
  "media_url": "optional string",
  "raw_payload": {}
}
```

Response:

- 202 Accepted with `{ "message_id": "uuid" }` for valid messages.
- Standard error format for invalid/missing data.

### 1.2 Cloud Message Queue (Supabase)

Table: `whatsapp_message_queue` (cloud Postgres)

- `id` UUID, primary key.
- `tenant_id` TEXT, FK to `user_profiles.tenant_id`.
- `customer_phone` TEXT.
- `message_type` TEXT (text, image, doc).
- `message_text` TEXT, nullable.
- `media_url` TEXT, nullable.
- `raw_payload` JSONB.
- `status` TEXT enum: `pending`, `processing`, `delivered`, `failed`, `expired`.
- `processed_at` TIMESTAMP, nullable.
- `created_at` TIMESTAMP default now().

RLS: tenant can only see its own rows.

Message TTL:

- Messages remain in the queue for at least 7 days.
- After that they can be moved to an archive or marked expired.

### 1.3 Desktop Polling Endpoint

- Endpoint: `GET /api/whatsapp/jobs/{tenant_id}`
- Auth: Bearer JWT with `tenant_id` claim matching path.
- Query params:
  - `limit` (optional, default 10, max 50).
- Behavior:
  - Returns messages where `tenant_id` matches and `status = 'pending'`.
  - When returned, status is updated to `processing`.
- Response shape:

```json
{
  "items": [
    {
      "id": "uuid",
      "tenant_id": "string",
      "customer_phone": "string",
      "message_type": "string",
      "message_text": "string or null",
      "media_url": "string or null",
      "raw_payload": {},
      "status": "processing"
    }
  ]
}
```

### 1.4 Desktop Completion Endpoint

- Endpoint: `POST /api/whatsapp/jobs/{job_id}/complete`
- Auth: Bearer JWT.
- Request JSON:

```json
{
  "status": "delivered|failed|expired",
  "error_message": "optional string",
  "result_summary": "optional string"
}
```

Behavior:

- Updates `status` and `processed_at`.
- Response: `{ "status": "ok" }` on success.

---

## 2. Auth & Device Activation

These contracts describe cloud-facing APIs, not internal desktop logic.

### 2.1 Device Activation

- Endpoint: `POST /api/devices/activate`
- Request:

```json
{
  "device_fingerprint": "string",
  "license_key": "string"
}
```

- Response:

```json
{
  "access_token": "jwt",
  "refresh_token": "jwt",
  "tenant_id": "string",
  "user_id": "string"
}
```

Notes:

- Subscription / free-trial / message limits are determined in cloud.
- Desktop stores tokens locally and uses `access_token` for cloud calls.

### 2.2 Token Refresh

- Endpoint: `POST /api/auth/refresh`
- Request: `{ "refresh_token": "jwt" }`
- Response: `{ "access_token": "jwt" }`

---

## 3. Desktop ↔ Tally Contracts (High Level)

### 3.1 Tally XML API

- Endpoint: `http://localhost:9000`.
- All request and response formats are defined by:
  - `backend/tally_connector.py`
  - `backend/tally_xml_builder.py`
  - `backend/tally_golden_xml.py`

Rule:

- These files define the canonical Tally contract.
- Any changes require explicit founder approval and manual Tally validation.

### 3.2 Shadow DB Sync

- Entities:
  - Ledgers, vouchers, stock items, bills and other Tally entities are synced into SQLite.
- Sync rules and table structure live in `backend/database/__init__.py` and `backend/sync_engine.py`.

---

## 4. Money & Tenant Rules

### 4.1 Money

Respect existing implementation in Tally XML and financial services.

Rule:

- No changes to money representation or calculations without a dedicated task, tests, and manual check in Tally.

### 4.2 Tenant Isolation

Cloud:

- Supabase uses RLS; all user-accessible tables are tenant-scoped.

Desktop:

- Every SQLAlchemy query must filter by `tenant_id`.
- Current tenant is determined by context middleware and tokens.

---

## 5. Error Contract

Standard HTTP status usage:

- 200/201/202 for success variants.
- 400 for validation errors.
- 401 for invalid or missing auth.
- 403 for wrong tenant or access denied.
- 404 for not found.
- 500 for unexpected server errors.
- 503 for Tally offline or upstream unavailable.

Error response shape:

```json
{
  "error": "SHORT_CODE",
  "detail": "Human-readable explanation",
  "code": "OPTIONAL_MACHINE_CODE",
  "timestamp": "ISO 8601 string"
}
```
