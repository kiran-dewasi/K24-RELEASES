# 🔗 K24 Tenant Linking System - Complete Implementation Guide

> **Document Version:** 1.0  
> **Date:** January 30, 2026  
> **Author:** Development Team  
> **Status:** Implementation Plan

---

## 📚 Table of Contents

1. [What is Tenant Linking?](#1-what-is-tenant-linking)
2. [Current Architecture](#2-current-architecture)
3. [What's Missing](#3-whats-missing)
4. [Phase 1: Tenant Sync Service](#phase-1-tenant-sync-service)
5. [Phase 2: Desktop Auth → Tenant Linking](#phase-2-desktop-auth--tenant-linking)
6. [Phase 3: WhatsApp → Tenant Linking](#phase-3-whatsapp--tenant-linking)
7. [Phase 4: Data Isolation Verification](#phase-4-data-isolation-verification)
8. [Flow Diagrams](#flow-diagrams)
9. [Testing Checklist](#testing-checklist)

---

## 1. What is Tenant Linking?

### The Core Concept

A **Tenant** represents a single business/company using K24. Think of it like:

```
Tenant = "Krisha Sales" (Your Company)
├── Users (You, your accountant, etc.)
├── Tally Data (Ledgers, Vouchers, Stock Items)
├── WhatsApp Number (Business WhatsApp)
├── Desktop App (Connected via license key)
└── Subscription (Free/Pro plan)
```

### Why is `tenant_id` Important?

| Without Tenant Linking | With Tenant Linking |
|------------------------|---------------------|
| All users see all data | Each user sees only their company's data |
| WhatsApp messages go nowhere | WhatsApp messages route to correct company |
| Desktop app can't identify owner | Desktop app knows which company it belongs to |
| No subscription tracking | Plans & billing tied to correct company |

### The `tenant_id` Format

```
tenant_id = "TENANT-" + first 8 chars of Supabase user_id

Example:
  user_id = "84f03f7d-1234-5678-abcd-efgh12345678"
  tenant_id = "TENANT-84F03F7D"
```

---

## 2. Current Architecture

### Where Tenant Data Lives

```
┌─────────────────────────────────────────────────────────────────┐
│                      SUPABASE (Cloud)                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  auth.users                                               │  │
│  │    └── id (UUID)  ← Primary identity                      │  │
│  │                                                           │  │
│  │  user_profiles                                            │  │
│  │    ├── id (UUID) → references auth.users                  │  │
│  │    ├── tenant_id → "TENANT-XXXXXXXX"                      │  │
│  │    └── full_name, company_name                            │  │
│  │                                                           │  │
│  │  tenants                                                  │  │
│  │    ├── id → "TENANT-XXXXXXXX"                             │  │
│  │    ├── company_name                                       │  │
│  │    ├── tally_company_name                                 │  │
│  │    └── whatsapp_number                                    │  │
│  │                                                           │  │
│  │  subscriptions                                            │  │
│  │    ├── user_id                                            │  │
│  │    ├── tenant_id → Links to tenants                       │  │
│  │    └── plan, status                                       │  │
│  │                                                           │  │
│  │  device_licenses                                          │  │
│  │    ├── license_key                                        │  │
│  │    ├── tenant_id → Links to tenants                       │  │
│  │    └── device_fingerprint                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ Sync via API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SQLite (Local)                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  tenants                                                  │  │
│  │    ├── id → "TENANT-XXXXXXXX"                             │  │
│  │    ├── company_name                                       │  │
│  │    ├── tally_company_name                                 │  │
│  │    └── whatsapp_number                                    │  │
│  │                                                           │  │
│  │  users (with TenantMixin)                                 │  │
│  │    └── tenant_id → Filter user's data                     │  │
│  │                                                           │  │
│  │  ledgers (with TenantMixin)                               │  │
│  │    └── tenant_id → Each ledger belongs to a tenant        │  │
│  │                                                           │  │
│  │  vouchers (with TenantMixin)                              │  │
│  │    └── tenant_id → Each voucher belongs to a tenant       │  │
│  │                                                           │  │
│  │  items (with TenantMixin)                                 │  │
│  │    └── tenant_id → Each stock item belongs to a tenant    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### TenantMixin - The Magic Filter

Every business table inherits from `TenantMixin`:

```python
class TenantMixin:
    """Mixin to add tenant context to models"""
    tenant_id = Column(String, index=True, nullable=False, default="default")

class Ledger(TenantMixin, Base):  # ← Has tenant_id
class Voucher(TenantMixin, Base):  # ← Has tenant_id
class StockItem(TenantMixin, Base):  # ← Has tenant_id
```

This means every query SHOULD filter by `tenant_id`:
```python
# ✅ Correct - User only sees their data
ledgers = db.query(Ledger).filter(Ledger.tenant_id == current_user.tenant_id).all()

# ❌ Wrong - User sees everyone's data
ledgers = db.query(Ledger).all()
```

---

## 3. What's Missing

### Gap Analysis

| Feature | What Should Happen | Current Status |
|---------|-------------------|----------------|
| **Registration** | Create tenant in Supabase + SQLite | ⚠️ Partially working |
| **Login** | Verify tenant exists locally | ❌ Not checked |
| **Desktop Auth** | Pass `tenant_id` to Tauri app | ⚠️ Needs verification |
| **WhatsApp Routing** | Lookup tenant from phone | ⚠️ Basic implementation |
| **Data Queries** | Filter by `tenant_id` | ⚠️ Some queries missing filter |

### The Problems

1. **Registration creates Supabase user but may not sync tenant to SQLite**
2. **Desktop app connects but tenant might not exist locally**
3. **WhatsApp messages might not find correct tenant**
4. **Some API endpoints don't filter by tenant_id**

---

## Phase 1: Tenant Sync Service & Security Core

### Goal
Create a central service for tenant sync AND a security guard to prevent IDOR attacks.

### Step 1.1: Create TenantService
(Same as before - syncs Supabase ↔ SQLite)

### Step 1.2: Implement TenantGuard (IDOR Protection)
**File:** `backend/middleware/tenant_guard.py`

```python
class TenantGuard:
    """
    Security middleware to prevent IDOR attacks.
    Ensures users can ONLY access their own tenant's data.
    """
    def enforce_tenant_filter(self, query, model, user: User):
        """
        Automatically appends .filter(tenant_id=...) to queries.
        Usage: query = TenantGuard.enforce(db.query(Voucher), Voucher, current_user)
        """
        if hasattr(model, 'tenant_id'):
            return query.filter(model.tenant_id == user.tenant_id)
        return query
```

### Step 1.3: Update Registration & Login
- Ensure `tenant_id` is created/synced on every auth event.

---

## Phase 2: Secure Desktop Auth (Signed JWTs)

### Goal
Connect desktop app SECURELY using signed tokens, not guessable IDs.

### Step 2.1: Secure Device Register
**File:** `backend/routers/devices.py`

```python
@router.post("/register")
async def register_device(request: DeviceRegisterRequest):
    # ... validation ...
    
    # GENERATE SIGNED TOKEN (Not just tenant_id)
    socket_token = jwt.encode({
        "sub": user.id,
        "tenant_id": user.tenant_id,
        "type": "socket_auth",
        "exp": datetime.utcnow() + timedelta(days=365)
    }, SECRET_KEY, algorithm="HS256")
    
    return {
        "license_key": license_key,
        "socket_token": socket_token, # <--- Secure!
        "tenant_id": user.tenant_id
    }
```

### Step 2.2: Secure Socket Connection
**File:** `backend/socket_manager.py`

```python
async def connect(sid, environ, auth):
    token = auth.get('token')
    try:
        # Verify Signature
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        tenant_id = payload['tenant_id']
        # Connection Approved
    except jwt.InvalidTokenError:
        raise ConnectionRefusedError("Invalid Auth")
```

### Expected Outcome After Phase 2

✅ Device registration returns `tenant_id`  
✅ Desktop app receives `tenant_id` via deep link  
✅ Socket connection uses `tenant_id` for identification  
✅ All Tally data synced with correct `tenant_id`  

---

## Phase 3: WhatsApp → Tenant Linking

### Goal
Route incoming WhatsApp messages to the correct tenant's data.

### The WhatsApp Routing Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   WhatsApp      │     │ Baileys Listener│     │   Backend API   │
│   (Customer)    │     │   (Node.js)     │     │   (FastAPI)     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ 1. Sends message      │                       │
         │──────────────────────>│                       │
         │                       │                       │
         │                       │ 2. Lookup tenant by   │
         │                       │    business WA number │
         │                       │──────────────────────>│
         │                       │                       │
         │                       │ 3. Returns tenant_id  │
         │                       │<──────────────────────│
         │                       │                       │
         │                       │ 4. Process message    │
         │                       │    with tenant_id     │
         │                       │──────────────────────>│
         │                       │                       │
         │                       │ 5. AI processes       │
         │                       │    (uses tenant data) │
         │                       │<──────────────────────│
         │                       │                       │
         │ 6. Reply sent         │                       │
         │<──────────────────────│                       │
```

### Step 3.1: Update WhatsApp Binding API

**File:** `backend/routers/whatsapp_binding.py`

```python
@router.post("/bind")
async def bind_whatsapp(request: BindRequest, current_user: User):
    """
    Bind a WhatsApp number to the tenant
    """
    # Update tenant's WhatsApp number
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    tenant.whatsapp_number = request.phone_number
    db.commit()
    
    # Also update in Supabase
    supabase_service.update_tenant(
        tenant_id=current_user.tenant_id,
        whatsapp_number=request.phone_number
    )
    
    return {"status": "bound", "tenant_id": current_user.tenant_id}
```

### Step 3.2: Update Baileys Listener Routing

**File:** `baileys-listener/listener.js`

```javascript
async function handleIncomingMessage(message) {
    const senderPhone = message.key.remoteJid;
    const businessPhone = getOurBusinessNumber();
    
    // 1. Lookup which tenant owns this business number
    const tenant = await lookupTenantByWhatsApp(businessPhone);
    
    if (!tenant) {
        console.log("No tenant found for this WhatsApp number");
        return;
    }
    
    // 2. Forward message with tenant_id
    await forwardToBackend(message, {
        tenant_id: tenant.id,
        sender_phone: senderPhone
    });
}
```

### Step 3.3: Tenant Settings UI

**File:** `frontend/src/app/settings/whatsapp/page.tsx`

Already exists - just ensure it saves to correct tenant.

### Expected Outcome After Phase 3

✅ WhatsApp number saved to tenant record  
✅ Baileys listener resolves tenant from phone number  
✅ All WhatsApp messages tagged with correct `tenant_id`  
✅ AI agent uses correct tenant's Tally data  

---

## Phase 4: Data Isolation Verification

### Goal
Verify that users can ONLY access their own tenant's data.

### Step 4.1: Query Audit

Check all endpoints filter by `tenant_id`:

```python
# ✅ Good - filtered
@router.get("/ledgers")
async def get_ledgers(current_user: User, db: Session):
    return db.query(Ledger).filter(
        Ledger.tenant_id == current_user.tenant_id
    ).all()

# ❌ Bad - not filtered
@router.get("/ledgers")
async def get_ledgers(db: Session):
    return db.query(Ledger).all()  # DANGER: Returns ALL tenants' data!
```

### Step 4.2: API Middleware

Create middleware that injects `tenant_id` from JWT:

```python
@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    # Extract tenant_id from JWT
    token = request.headers.get("Authorization")
    if token:
        payload = decode_jwt(token)
        request.state.tenant_id = payload.get("tenant_id")
    
    return await call_next(request)
```

### Step 4.3: Isolation Test

```python
def test_tenant_isolation():
    # Create two tenants
    tenant_a = create_tenant("Company A")
    tenant_b = create_tenant("Company B")
    
    # Create ledger for tenant A
    ledger = create_ledger(name="Cash", tenant_id=tenant_a.id)
    
    # Login as tenant B
    user_b = login_as(tenant_b)
    
    # Try to access ledgers - should NOT see tenant A's ledger
    ledgers = api.get_ledgers(auth=user_b.token)
    
    assert len(ledgers) == 0  # Tenant B has no ledgers
    assert ledger.name not in [l.name for l in ledgers]  # Can't see Cash
```

### Expected Outcome After Phase 4

✅ All queries filter by `tenant_id`  
✅ JWT contains `tenant_id`  
✅ Users cannot access other tenants' data  
✅ Complete data isolation verified  

---

## Flow Diagrams

### Complete User Journey

```
                          REGISTRATION
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  1. User signs up on web                                       │
│  2. Supabase creates auth.user (UUID)                          │
│  3. Backend generates tenant_id = "TENANT-{first 8 chars}"     │
│  4. Backend creates:                                           │
│     - user_profiles (Supabase) with tenant_id                  │
│     - tenants (Supabase) with company info                     │
│     - tenants (SQLite) with same info                          │
│     - subscriptions (Supabase) with tenant_id                  │
│     - users (SQLite) with tenant_id                            │
│  5. Returns JWT with tenant_id embedded                        │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                         DESKTOP SETUP
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  1. User clicks "Connect Desktop App"                          │
│  2. Frontend calls /api/devices/register                       │
│  3. Backend generates license_key + returns tenant_id          │
│  4. Frontend opens deep link: k24://auth?license=X&tenant=Y    │
│  5. Tauri app receives license + tenant_id                     │
│  6. Tauri connects Socket.IO with auth.token = tenant_id       │
│  7. Backend tracks: tenant_id → socket_id mapping              │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                         TALLY SYNC
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  1. Tauri fetches data from Tally                              │
│  2. Sends via Socket.IO: { data: [...], tenant_id: "..." }     │
│  3. Backend receives, validates tenant_id                      │
│  4. Stores in SQLite with tenant_id column                     │
│  5. User queries via web - filtered by their tenant_id         │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                      WHATSAPP INTEGRATION
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  1. User binds WhatsApp number in settings                     │
│  2. Backend stores: tenants.whatsapp_number = "91XXXXXXX"      │
│  3. Customer sends message to this number                      │
│  4. Baileys receives, looks up tenant by phone                 │
│  5. Forwards to backend with tenant_id                         │
│  6. AI agent queries data filtered by tenant_id                │
│  7. Creates voucher with tenant_id                             │
│  8. Sends to Tally via socket (routed by tenant_id)            │
└────────────────────────────────────────────────────────────────┘
```

---

## Testing Checklist

### Phase 1 Tests
- [ ] New user registration creates tenant in Supabase
- [ ] New user registration creates tenant in SQLite
- [ ] Login syncs missing tenant to SQLite
- [ ] JWT contains tenant_id claim

### Phase 2 Tests
- [ ] Device registration returns tenant_id
- [ ] Deep link contains tenant_id
- [ ] Socket connection uses tenant_id as auth
- [ ] Tally data stored with correct tenant_id

### Phase 3 Tests
- [ ] WhatsApp binding saves to tenant record
- [ ] Baileys can lookup tenant from phone
- [ ] Messages processed with correct tenant context
- [ ] AI agent uses correct tenant's data

### Phase 4 Tests
- [ ] User A cannot see User B's ledgers
- [ ] User A cannot see User B's vouchers
- [ ] User A cannot see User B's stock items
- [ ] API returns 403 if accessing wrong tenant

---

## Summary

| Phase | Creates/Updates | Duration |
|-------|-----------------|----------|
| **Phase 1** | `TenantService`, auth flow | ~30 mins |
| **Phase 2** | Device endpoints, deep link | ~20 mins |
| **Phase 3** | WhatsApp routing | ~20 mins |
| **Phase 4** | Query audit, tests | ~15 mins |

**Total estimated time:** ~1.5 hours

---

## Ready to Start?

The implementation will follow this order:
1. ✨ Phase 1 first (foundation)
2. ✨ Phase 2 next (desktop)
3. ✨ Phase 3 then (WhatsApp)
4. ✨ Phase 4 finally (verification)

Let's begin! 🚀
