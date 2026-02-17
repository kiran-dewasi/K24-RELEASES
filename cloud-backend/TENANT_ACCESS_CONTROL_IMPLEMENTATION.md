# Tenant Access Control Implementation

**Date**: 2026-02-17  
**File**: `cloud-backend/routers/whatsapp_cloud.py`  
**Route**: `POST /api/whatsapp/cloud/incoming`

## Summary

Updated the WhatsApp cloud incoming message handler to enforce tenant access control using the `tenant_config` table. The handler now validates business WhatsApp numbers, enforces subscription rules, and scopes customer lookups to the resolved tenant.

## Changes Made

### 1. **New Helper Functions**

#### `normalize_whatsapp_number(phone: str) -> str`
- Removes all non-digit characters from phone numbers
- Ensures consistent lookups across different phone number formats
- Example: `"+1 (555) 123-4567"` → `"15551234567"`

#### `resolve_tenant_from_business_number(business_number: str, supabase) -> Dict[str, Any]`
- Resolves `tenant_id` from business WhatsApp number using `tenant_config` table
- Enforces subscription access control rules
- Returns tenant_id, subscription_status, and trial_ends_at
- **Raises HTTPException if**:
  - No tenant found for business number → `404 TENANT_NOT_FOUND`
  - Subscription is `"expired"` or `"cancelled"` → `403 TENANT_SUBSCRIPTION_EXPIRED`
  - Subscription is `"trial"` and `trial_ends_at` is in the past → `403 TENANT_SUBSCRIPTION_EXPIRED`
  - Subscription status is not `"active"` or `"trial"` → `403 TENANT_SUBSCRIPTION_EXPIRED`

### 2. **Updated Handler Flow**

The `receive_whatsapp_message` function now follows this sequence:

1. **Validate business number**: Ensures `message.to_number` is provided
2. **Resolve tenant**: Uses `resolve_tenant_from_business_number` to:
   - Find tenant by business WhatsApp number in `tenant_config`
   - Enforce subscription rules
   - Return tenant_id and subscription_status
3. **Normalize sender phone**: Applies `normalize_whatsapp_number` to sender phone
4. **Resolve customer**: Queries `whatsapp_customer_mappings` with:
   - **Scoped to resolved `tenant_id`** (prevents cross-tenant access)
   - Tries normalized phone first, then original phone format
   - Returns `user_id` and `customer_name`
5. **Insert to queue**: Adds message to `whatsapp_message_queue` with all fields
6. **Log subscription status**: Includes `subscription_status` in queue success log

## Subscription Rules Enforced

| Subscription Status | Trial Ends At | Allowed? | Error Code |
|---------------------|---------------|----------|------------|
| `active` | (any) | ✅ Yes | - |
| `trial` | `null` or future date | ✅ Yes | - |
| `trial` | past date | ❌ No | `TENANT_SUBSCRIPTION_EXPIRED` |
| `expired` | (any) | ❌ No | `TENANT_SUBSCRIPTION_EXPIRED` |
| `cancelled` | (any) | ❌ No | `TENANT_SUBSCRIPTION_EXPIRED` |
| (other) | (any) | ❌ No | `TENANT_SUBSCRIPTION_EXPIRED` |

## API Contract

### Request Model (Unchanged)
```python
class IncomingWhatsAppMessage(BaseModel):
    from_number: str              # Sender phone (customer)
    to_number: Optional[str]      # Business WhatsApp number
    message_type: str             # text, image, document
    text: Optional[str]
    media_url: Optional[str]
    raw_payload: Optional[Dict[str, Any]]
```

### Success Response (Unchanged)
```json
{
  "message_id": "uuid-string"
}
```
**HTTP Status**: `202 Accepted`

### Error Responses (New)

#### Missing Business Number (`400`)
```json
{
  "error": "MISSING_BUSINESS_NUMBER",
  "detail": "Business WhatsApp number (to_number) is required",
  "timestamp": "ISO 8601 datetime"
}
```

#### Tenant Not Found (`404`)
```json
{
  "error": "TENANT_NOT_FOUND",
  "detail": "No tenant configured for business WhatsApp number",
  "timestamp": "ISO 8601 datetime"
}
```

#### Subscription Expired (`403`)
```json
{
  "error": "TENANT_SUBSCRIPTION_EXPIRED",
  "detail": "Tenant subscription is expired. Please renew to continue receiving messages.",
  "timestamp": "ISO 8601 datetime"
}
```

#### Unknown Customer (`404`)
```json
{
  "error": "UNKNOWN_CUSTOMER",
  "detail": "Phone number {from_number} is not registered with this tenant",
  "timestamp": "ISO 8601 datetime"
}
```

## Database Tables Used

### `tenant_config`
**Query**: Lookup by `whatsapp_number`  
**Fields Used**:
- `tenant_id` (PK)
- `whatsapp_number` (indexed for lookup)
- `subscription_status` (enum: active, trial, expired, cancelled)
- `trial_ends_at` (timestamp)

### `whatsapp_customer_mappings`
**Query**: Lookup by `tenant_id` + `customer_phone` + `is_active=true`  
**Fields Used**:
- `tenant_id` (FK, scoped to resolved tenant)
- `customer_phone` (indexed)
- `user_id`
- `customer_name`
- `is_active` (boolean filter)

### `whatsapp_message_queue`
**Insert**: All fields including resolved `tenant_id`  
**Fields Inserted**:
- `id` (message_id, UUID)
- `tenant_id` (from tenant_config)
- `user_id` (from customer mapping)
- `customer_phone` (from request)
- `message_type`, `message_text`, `media_url`, `raw_payload`
- `status` (default: "pending")
- `created_at` (timestamp)

## Logging & Observability

All log messages now include:
- Masked tenant_id (first 8 chars) for privacy
- Subscription status for audit trails
- Clear emoji indicators for success/failure states

Example logs:
```
✅ Tenant access granted: tenant_id=a40e34f2..., subscription_status=active
✅ Customer resolved: phone=+1234567890, user_id=123, tenant_id=a40e34f2...
✅ Message queued: message_id=..., tenant_id=a40e34f2..., subscription_status=active
🚫 Blocked incoming message: tenant_id=a40e34f2..., subscription_status=expired
```

## Security Improvements

1. **Tenant Isolation**: Customer lookups are now scoped to the resolved tenant_id, preventing cross-tenant data access
2. **Subscription Enforcement**: Expired/cancelled tenants cannot receive messages
3. **Business Number Validation**: Ensures messages are only processed for configured business numbers
4. **Normalized Lookups**: Reduces false negatives from phone number format variations

## Backward Compatibility

✅ **API contract unchanged for successful requests**
- Request shape identical
- Response shape identical on success (202 + message_id)

⚠️ **New error responses**
- `400 MISSING_BUSINESS_NUMBER` (new validation)
- `404 TENANT_NOT_FOUND` (new tenant resolution step)
- `403 TENANT_SUBSCRIPTION_EXPIRED` (new subscription enforcement)
- `404 UNKNOWN_CUSTOMER` (updated error message to clarify tenant scope)

## Testing Recommendations

### Unit Tests
- [ ] Test `normalize_whatsapp_number` with various formats
- [ ] Test `resolve_tenant_from_business_number` with all subscription statuses
- [ ] Test trial expiration logic (past, future, null)
- [ ] Test tenant not found scenario
- [ ] Test customer not found for tenant scenario

### Integration Tests
- [ ] Test end-to-end with active subscription
- [ ] Test end-to-end with trial (valid)
- [ ] Test rejection with expired subscription
- [ ] Test rejection with cancelled subscription
- [ ] Test rejection with expired trial
- [ ] Test normalized vs original phone number lookups

### Manual Tests
- [ ] Verify logs include subscription_status
- [ ] Verify error responses match documented format
- [ ] Verify existing integrations still work (Baileys listener)

## Dependencies

- **New Import**: `import re` (for phone normalization)
- **Existing Dependencies**: No changes
- **Database Schema**: Assumes `tenant_config` table exists with documented fields

## Next Steps

1. **Test the implementation** with real/staging data
2. **Update Baileys listener** to always include `to_number` in webhook payload
3. **Monitor logs** for subscription_status distribution
4. **Add metrics** for blocked requests by subscription status
5. **Consider** adding retry logic for transient tenant_config lookup failures
