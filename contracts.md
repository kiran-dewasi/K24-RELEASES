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

**Table**: `whatsapp_message_queue`

**Purpose**: Central queue for incoming WhatsApp messages. Desktop apps poll this table to fetch messages for their tenant.

**Columns**:
- `id` UUID PRIMARY KEY (gen_random_uuid())
- `tenant_id` TEXT NOT NULL – Which business this message belongs to
- `user_id` UUID – Optional FK to auth.users (if customer is known user)
- `customer_phone` TEXT NOT NULL – Sender's WhatsApp number (e.g., "+919876543210")
- `message_type` TEXT DEFAULT 'text' – Type: 'text', 'image', 'document', 'audio'
- `message_text` TEXT – Message body (null for non-text messages)
- `media_url` TEXT – URL to media file (for images/docs)
- `raw_payload` JSONB – Original webhook payload from Baileys
- `status` TEXT DEFAULT 'pending' – Lifecycle: 'pending' → 'processing' → 'delivered' or 'failed'
- `processed_at` TIMESTAMP – When desktop marked this job complete
- `error_message` TEXT – Error details if status='failed'
- `created_at` TIMESTAMP DEFAULT now() – When message arrived

**RLS**: Tenant can only see its own rows (via `tenant_id`).

**Indexes**: `(tenant_id, status)` for fast polling.

**Message TTL**: Messages older than 7 days can be archived or deleted.

### 1.3 Desktop Polling Endpoint

- **Endpoint**: `GET /api/whatsapp/jobs/{tenant_id}`
- **Auth**: Bearer JWT with `tenant_id` claim matching path parameter
- **Query params**:
  - `limit` (optional, default 10, max 50)
- **Behavior**:
  - Query: `SELECT * FROM whatsapp_message_queue WHERE tenant_id = ? AND status = 'pending' LIMIT ?`
  - Atomically updates: `UPDATE ... SET status = 'processing', processed_at = now()`
  - Returns updated rows
- **Response**:

```json
{
  "items": [
    {
      "id": "uuid",
      "tenant_id": "text",
      "user_id": "uuid or null",
      "customer_phone": "text",
      "message_type": "text",
      "message_text": "text or null",
      "media_url": "text or null",
      "raw_payload": {},
      "status": "processing",
      "created_at": "ISO 8601"
    }
  ]
}
```

### 1.4 Desktop Completion Endpoint

- **Endpoint**: `POST /api/whatsapp/jobs/{job_id}/complete`
- **Auth**: Bearer JWT
- **Request**:

```json
{
  "status": "delivered" | "failed",
  "error_message": "string (required if status=failed)",
  "result_summary": "optional string"
}
```

**Behavior**:
- Updates: `UPDATE whatsapp_message_queue SET status = ?, error_message = ?, processed_at = now() WHERE id = ?`
- Validates: `status` must be 'delivered' or 'failed' (not 'pending' or 'processing')
- If `status='failed'`, `error_message` is required

**Response**:

```json
{
  "status": "ok",
  "job_id": "uuid",
  "processed_at": "ISO 8601"
}
```

### 1.5 Customer Phone → Tenant Routing

**Table**: `whatsapp_customer_mappings`

**Purpose**: Maps customer WhatsApp numbers to tenants. Used by cloud webhook to determine which tenant should receive the message.

**Columns**:
- `id` UUID PRIMARY KEY
- `user_id` UUID NOT NULL – FK to auth.users
- `tenant_id` TEXT NOT NULL – Which business owns this customer
- `customer_phone` TEXT NOT NULL – Customer's WhatsApp number
- `customer_name` TEXT – Display name for this customer
- `client_code` TEXT – Optional business-specific identifier
- `notes` TEXT – Internal notes about this customer
- `is_active` BOOLEAN DEFAULT true – Can be disabled without deleting
- `created_at` TIMESTAMP DEFAULT now()
- `updated_at` TIMESTAMP DEFAULT now()

**Usage in Flow**:
1. Webhook receives message from `customer_phone`
2. Query: `SELECT tenant_id FROM whatsapp_customer_mappings WHERE customer_phone = ? AND is_active = true`
3. If found: insert message into queue with that `tenant_id`
4. If not found: return 404 or create pending mapping for manual approval

---

## 2. Supabase Schema – Phase 1 Tables

This section documents the core tables used in Phase 1 for auth, licensing, and multi-tenancy.

### 2.1 Tenants Table

**Table**: `tenants`

**Purpose**: Represents each business using K24. Every user, voucher, and message is scoped to a tenant.

**Columns**:
- `id` VARCHAR PRIMARY KEY – Unique tenant identifier (e.g., "TENANT001")
- `company_name` VARCHAR – Business display name
- `tally_company_name` VARCHAR – Exact company name in Tally (case-sensitive)
- `whatsapp_number` VARCHAR UNIQUE – Business WhatsApp number for incoming messages
- `license_key` VARCHAR – License/activation key
- `created_at` TIMESTAMP

**Usage**:
- Every desktop app is tied to one tenant
- Cloud routes WhatsApp messages via `whatsapp_number` → `tenant_id`
- All data tables have `tenant_id` foreign key for isolation

### 2.2 Users & Auth

**Table**: `users_profile` (Supabase public schema)

**Purpose**: User profiles linked to Supabase Auth. Each user belongs to one tenant.

**Columns**:
- `id` UUID PRIMARY KEY (gen_random_uuid())
- `full_name` TEXT NOT NULL
- `whatsapp_number` TEXT UNIQUE – For WhatsApp-based login
- `avatar_url` TEXT
- `role` TEXT DEFAULT 'owner' – Role: 'owner', 'admin', 'accountant', 'viewer'
- `tenant_id` VARCHAR – FK to tenants(id)
- `company_name` TEXT
- `created_at` TIMESTAMP DEFAULT now()

**Linked to**: `auth.users` (Supabase Auth table) via `id`

**Note**: Desktop users also have local records in `public.users` (legacy SQLite schema), but cloud auth uses `auth.users` + `users_profile`.

### 2.3 Device Licenses

**Table**: `device_licenses`

**Purpose**: Tracks desktop app activations. Each license allows one device to access K24.

**Columns**:
- `id` UUID PRIMARY KEY
- `license_key` TEXT UNIQUE NOT NULL – Activation key (e.g., "K24-XXXX-YYYY-ZZZZ")
- `user_id` UUID NOT NULL – FK to auth.users(id)
- `tenant_id` TEXT NOT NULL – Which business this license belongs to
- `device_fingerprint` TEXT NOT NULL – Unique device identifier (machine UUID + MAC)
- `device_name` TEXT – Human-readable device name (e.g., "Desktop-001")
- `status` TEXT DEFAULT 'active' – Status: 'active', 'revoked', 'expired'
- `activated_at` TIMESTAMP DEFAULT now()
- `last_validated_at` TIMESTAMP – Last time desktop checked in
- `created_at` TIMESTAMP DEFAULT now()

**Usage in Flow**:
1. User logs in on web → generates license_key
2. Web sends deep link: `k24://activate?license_key=XXX&tenant_id=YYY`
3. Desktop calls: `POST /api/devices/activate` with license_key + device_fingerprint
4. Cloud verifies, creates device_license record, returns JWT tokens

### 2.4 Subscriptions

**Table**: `subscriptions`

**Purpose**: Manages billing plans and trial periods for tenants.

**Columns**:
- `id` UUID PRIMARY KEY
- `user_id` UUID NOT NULL – FK to auth.users(id)
- `tenant_id` TEXT NOT NULL
- `plan` TEXT DEFAULT 'free' – Plan: 'free', 'pro', 'enterprise'
- `status` TEXT DEFAULT 'trial' – Status: 'trial', 'active', 'expired', 'cancelled'
- `trial_starts_at` TIMESTAMP DEFAULT now()
- `trial_ends_at` TIMESTAMP DEFAULT (now() + 14 days)
- `expires_at` TIMESTAMP – For paid plans, when subscription expires
- `created_at` TIMESTAMP DEFAULT now()
- `updated_at` TIMESTAMP DEFAULT now()

**Usage**:
- Free plan: 50 messages/month limit
- Trial: 14 days, unlimited messages
- Pro: ₹999/month, unlimited
- Cloud enforces limits when inserting into `whatsapp_message_queue`

---

## 3. Auth & Device Activation

These contracts describe cloud-facing APIs for desktop app activation and authentication.

### 3.1 Device Activation

**Endpoint**: `POST /api/devices/activate`

**Purpose**: Activate a desktop app installation. Links a device to a user's license and returns auth tokens.

**Request**:

```json
{
  "license_key": "K24-XXXX-YYYY-ZZZZ",
  "device_fingerprint": "abc123-mac-uuid",
  "device_name": "Desktop-001 (optional)"
}
```

**Process**:
1. Validate `license_key` (not already used by another device, not revoked)
2. Check subscription status (trial active, paid plan valid)
3. Insert into `device_licenses` table with status='active'
4. Generate JWT with claims: `{ user_id, tenant_id, device_id }`
5. Return tokens

**Response** (200 OK):

```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "user_id": "uuid",
  "tenant_id": "text",
  "device_id": "uuid",
  "subscription": {
    "plan": "trial",
    "status": "active",
    "expires_at": "2026-03-01T00:00:00Z"
  }
}
```

**Errors**:
- 400: Invalid license_key format
- 404: License not found or already used
- 403: Subscription expired or device limit reached

**Notes**:
- Desktop stores tokens in `%APPDATA%/K24/auth.json` (encrypted)
- JWT expires after 7 days, must refresh
- Desktop validates token before each cloud API call

### 3.2 Token Refresh

**Endpoint**: `POST /api/auth/refresh`

**Request**:

```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response**:

```json
{
  "access_token": "eyJhbGc...",
  "expires_in": 604800
}
```

**Process**:
- Validates refresh_token signature and expiry
- Updates `device_licenses.last_validated_at = now()`
- Generates new access_token (same claims)

### 3.3 Device Validation (Heartbeat)

**Endpoint**: `GET /api/devices/validate`

**Auth**: Bearer JWT

**Purpose**: Desktop calls this on startup to verify license is still active.

**Response**:

```json
{
  "valid": true,
  "device_id": "uuid",
  "status": "active",
  "subscription_status": "trial",
  "message_limit_remaining": 42
}
```

**If invalid**: Returns 403, desktop shows "License Revoked" error

---

## 4. Desktop ↔ Tally Contracts (High Level)

### 4.1 Tally XML API

- Endpoint: `http://localhost:9000`.
- All request and response formats are defined by:
  - `backend/tally_connector.py`
  - `backend/tally_xml_builder.py`
  - `backend/tally_golden_xml.py`

Rule:

- These files define the canonical Tally contract.
- Any changes require explicit founder approval and manual Tally validation.

### 4.2 Shadow DB Sync

- Entities:
  - Ledgers, vouchers, stock items, bills and other Tally entities are synced into SQLite.
- Sync rules and table structure live in `backend/database/__init__.py` and `backend/sync_engine.py`.

---

## 5. Money & Tenant Rules

### 5.1 Money

Respect existing implementation in Tally XML and financial services.

Rule:

- No changes to money representation or calculations without a dedicated task, tests, and manual check in Tally.

### 5.2 Tenant Isolation

**Cloud (Supabase)**:
- All tables with `tenant_id` column have RLS enabled
- Policy: `WHERE tenant_id = get_current_tenant_id()`
- Tables: `whatsapp_message_queue`, `whatsapp_customer_mappings`, `vouchers`, `ledgers`, `bills`, etc.

**Desktop (SQLite)**:
- Every SQLAlchemy query filters by `tenant_id`
- Current tenant determined by JWT token claims
- Middleware: `backend/middleware/tenant_context.py`

**Critical**: Never allow cross-tenant data access. Test all queries with 2+ tenants.

---

## 6. Error Contract

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
