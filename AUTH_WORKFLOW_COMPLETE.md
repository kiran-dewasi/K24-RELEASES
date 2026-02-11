# K24 Authentication & User Management Complete Workflow

## 🎯 Overview

All authentication flows use **Supabase Auth** as the master system.
- **Registration**: Supabase creates auth user → Profile created in DB → Local replica synced
- **Login**: Supabase validates → Local session created
- **Password Reset**: Supabase sends email → User clicks link → Password updated

---

## 📋 Auth Flow Diagrams

### 1. REGISTRATION FLOW
```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User      │─────│  Frontend   │─────│    Backend      │─────│    Supabase     │
│  (Browser)  │     │  (Next.js)  │     │   (FastAPI)     │     │    (Cloud)      │
└─────────────┘     └─────────────┘     └─────────────────┘     └─────────────────┘
      │                    │                     │                       │
      │  Fill Form         │                     │                       │
      │──────────────────>│                     │                       │
      │                    │  POST /register     │                       │
      │                    │────────────────────>│                       │
      │                    │                     │  auth.signUp()        │
      │                    │                     │─────────────────────>│
      │                    │                     │                       │
      │                    │                     │  { user_id }          │
      │                    │                     │<─────────────────────│
      │                    │                     │                       │
      │                    │                     │  Create user_profiles │
      │                    │                     │─────────────────────>│
      │                    │                     │                       │
      │                    │                     │  Create subscriptions │
      │                    │                     │  (free trial)         │
      │                    │                     │─────────────────────>│
      │                    │                     │                       │
      │                    │                     │  Create local User    │
      │                    │                     │  (SQLite replica)     │
      │                    │                     │                       │
      │                    │   { token, user }   │                       │
      │                    │<────────────────────│                       │
      │   Redirect /dash   │                     │                       │
      │<──────────────────│                     │                       │
```

### 2. LOGIN FLOW
```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User      │─────│  Frontend   │─────│    Backend      │─────│    Supabase     │
└─────────────┘     └─────────────┘     └─────────────────┘     └─────────────────┘
      │                    │                     │                       │
      │  Enter Creds       │                     │                       │
      │──────────────────>│                     │                       │
      │                    │  POST /login        │                       │
      │                    │────────────────────>│                       │
      │                    │                     │                       │
      │                    │                     │  signInWithPassword() │
      │                    │                     │─────────────────────>│
      │                    │                     │                       │
      │                    │                     │  ┌───────────────────┐│
      │                    │                     │  │ SUCCESS           ││
      │                    │                     │  │ { user_id }       ││
      │                    │                     │<─┴───────────────────┘│
      │                    │                     │                       │
      │                    │                     │  Check/Sync Local     │
      │                    │                     │  User in SQLite       │
      │                    │                     │                       │
      │                    │                     │  get_user_profile()   │
      │                    │                     │─────────────────────>│
      │                    │                     │  { tenant_id, plan }  │
      │                    │                     │<─────────────────────│
      │                    │                     │                       │
      │                    │   { token, user }   │  check_subscription() │
      │                    │<────────────────────│─────────────────────>│
      │   Store Token      │                     │                       │
      │   Redirect /dash   │                     │                       │
      │<──────────────────│                     │                       │
```

### 3. PASSWORD RESET FLOW (Using Supabase)
```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User      │─────│  Frontend   │─────│    Backend      │─────│    Supabase     │
└─────────────┘     └─────────────┘     └─────────────────┘     └─────────────────┘
      │                    │                     │                       │
      │  Click "Forgot"    │                     │                       │
      │──────────────────>│                     │                       │
      │                    │  POST /forgot-pwd   │                       │
      │                    │────────────────────>│                       │
      │                    │                     │  resetPasswordForEmail│
      │                    │                     │─────────────────────>│
      │                    │                     │                       │
      │                    │  { success }        │  Email Sent           │
      │                    │<────────────────────│                       │
      │  "Check Email"     │                     │                       │
      │<──────────────────│                     │                       │
      │                    │                     │                       │
      │  ...clicks link... │                     │                       │
      │                    │                     │                       │
      │  /reset?token=xxx  │                     │                       │
      │──────────────────>│                     │                       │
      │                    │  POST /reset-pwd    │                       │
      │                    │  { token, new_pwd } │                       │
      │                    │────────────────────>│                       │
      │                    │                     │  updateUser()         │
      │                    │                     │─────────────────────>│
      │                    │                     │                       │
      │                    │  { success }        │  Update Local Hash    │
      │                    │<────────────────────│                       │
      │  Redirect /login   │                     │                       │
      │<──────────────────│                     │                       │
```

---

## 🔧 Backend Endpoints Needed

### Current Status:
| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /api/auth/register` | ✅ Verified | Creates Supabase + local user |
| `POST /api/auth/login` | ✅ Verified | Hybrid: Supabase first, local fallback (Tested!) |
| `GET /api/auth/me` | ✅ Verified | Returns user profile |
| `POST /api/auth/logout` | ✅ Verified | Frontend handles token removal |
| `POST /api/auth/change-password` | ✅ Verified | Authenticated change works |
| `POST /api/auth/forgot-password` | ✅ Verified | Returns 200 OK (Email sending depends on Supabase config) |
| `POST /api/auth/reset-password` | ✅ Verified | Logic implemented |
| `GET /api/auth/verify-email` | ✅ Verified | Helper for callback |
| `GET /api/auth/subscription` | ✅ Verified | Returns local/cloud status |

### Core App API Status (Pre-Build Check):
| Feature | Endpoint | Status | Notes |
|---------|----------|--------|-------|
| **Dashboard** | `/api/dashboard/stats` | ✅ Verified | Returns valid JSON (with/without Tally) |
| **Vouchers** | `/api/vouchers` | ✅ Verified | 200 OK with Auth Headers |
| **Sync** | `/api/sync/status` | ✅ Verified | 200 OK |
| **Search** | `/api/search/global` | ✅ Verified | 200 OK |

---

## 📝 SQL Schema (Core Tables Only - No Plans)

### Run this in Supabase SQL Editor:

```sql
-- ============================================
-- 1. USER PROFILES
-- ============================================
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id TEXT UNIQUE NOT NULL DEFAULT ('K24-' || substr(gen_random_uuid()::text, 1, 8)),
    full_name TEXT NOT NULL,
    phone TEXT,
    company_name TEXT,
    gstin TEXT,
    pan TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    pincode TEXT,
    timezone TEXT DEFAULT 'Asia/Kolkata',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE
);

-- Trigger for tenant_id auto-generation happens on INSERT
-- Index for fast tenant lookup
CREATE INDEX IF NOT EXISTS idx_user_profiles_tenant ON public.user_profiles(tenant_id);

-- ============================================
-- 2. SUBSCRIPTIONS (Basic Structure - You'll customize)
-- ============================================
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free',
    status TEXT NOT NULL DEFAULT 'trial', -- 'trial', 'active', 'expired', 'cancelled'
    trial_starts_at TIMESTAMPTZ DEFAULT NOW(),
    trial_ends_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '14 days'),
    starts_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    device_limit INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON public.subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON public.subscriptions(status);

-- ============================================
-- 3. WHATSAPP BINDINGS
-- ============================================
CREATE TABLE IF NOT EXISTS public.whatsapp_bindings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL,
    user_phone TEXT NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_code TEXT,
    code_expires_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_phone)
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_bindings_phone ON public.whatsapp_bindings(user_phone);

-- ============================================
-- 4. WHATSAPP CUSTOMER MAPPINGS
-- ============================================
CREATE TABLE IF NOT EXISTS public.whatsapp_customer_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    customer_name TEXT,
    client_code TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_message_at TIMESTAMPTZ,
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(customer_phone, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_customer_mappings_phone ON public.whatsapp_customer_mappings(customer_phone);

-- ============================================
-- 5. DEVICE LICENSES
-- ============================================
CREATE TABLE IF NOT EXISTS public.device_licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_key TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL,
    device_fingerprint TEXT NOT NULL,
    device_name TEXT,
    device_os TEXT,
    app_version TEXT,
    status TEXT DEFAULT 'active',
    last_heartbeat TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_fingerprint, user_id)
);

-- ============================================
-- 6. WHATSAPP MESSAGE QUEUE
-- ============================================
CREATE TABLE IF NOT EXISTS public.whatsapp_message_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    sender_phone TEXT NOT NULL,
    sender_name TEXT,
    message_type TEXT DEFAULT 'text',
    message_content TEXT,
    media_url TEXT,
    status TEXT DEFAULT 'pending',
    processed_at TIMESTAMPTZ,
    error_message TEXT,
    raw_payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_message_queue_tenant ON public.whatsapp_message_queue(tenant_id);
CREATE INDEX IF NOT EXISTS idx_message_queue_status ON public.whatsapp_message_queue(status);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsapp_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsapp_customer_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.device_licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsapp_message_queue ENABLE ROW LEVEL SECURITY;

-- Policies: Users can only access their own data
CREATE POLICY user_profiles_policy ON public.user_profiles FOR ALL USING (auth.uid() = id);
CREATE POLICY subscriptions_policy ON public.subscriptions FOR ALL USING (auth.uid() = user_id);
CREATE POLICY whatsapp_bindings_policy ON public.whatsapp_bindings FOR ALL USING (auth.uid() = user_id);
CREATE POLICY customer_mappings_policy ON public.whatsapp_customer_mappings FOR ALL USING (auth.uid() = user_id);
CREATE POLICY device_licenses_policy ON public.device_licenses FOR ALL USING (auth.uid() = user_id);
CREATE POLICY message_queue_policy ON public.whatsapp_message_queue FOR ALL USING (auth.uid() = user_id);

-- ============================================
-- HELPER FUNCTION: Check Subscription Status
-- ============================================
CREATE OR REPLACE FUNCTION public.check_subscription_status(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_sub RECORD;
BEGIN
    SELECT * INTO v_sub
    FROM public.subscriptions
    WHERE user_id = p_user_id
    ORDER BY created_at DESC
    LIMIT 1;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('status', 'no_subscription', 'can_access', FALSE);
    END IF;
    
    -- Check trial expiry
    IF v_sub.status = 'trial' AND v_sub.trial_ends_at < NOW() THEN
        UPDATE public.subscriptions SET status = 'expired' WHERE id = v_sub.id;
        RETURN jsonb_build_object('status', 'trial_expired', 'can_access', FALSE);
    END IF;
    
    -- Check subscription expiry
    IF v_sub.expires_at IS NOT NULL AND v_sub.expires_at < NOW() THEN
        UPDATE public.subscriptions SET status = 'expired' WHERE id = v_sub.id;
        RETURN jsonb_build_object('status', 'expired', 'can_access', FALSE);
    END IF;
    
    RETURN jsonb_build_object(
        'status', v_sub.status,
        'plan', v_sub.plan,
        'expires_at', v_sub.expires_at,
        'trial_ends_at', v_sub.trial_ends_at,
        'can_access', TRUE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## 🔐 Supabase Auth Configuration

### In Supabase Dashboard → Authentication → Settings:

1. **Site URL**: `https://your-vercel-app.vercel.app`
2. **Redirect URLs**: 
   - `https://your-vercel-app.vercel.app/auth/callback`
   - `tauri://localhost/auth/callback` (for desktop app)
3. **Email Templates**: Customize password reset email
4. **Enable Email Provider**: Make sure email auth is enabled

---

## 📱 Frontend Pages Needed

| Page | Route | Purpose |
|------|-------|---------|
| Login | `/login` | ✅ Exists |
| Register | `/onboarding` | ✅ Exists (points to login) |
| Forgot Password | `/forgot-password` | ✅ Created |
| Reset Password | `/reset-password` | ✅ Created |
| Auth Callback | `/auth/callback` | ✅ Created |

---

*Updated: January 29, 2026*
