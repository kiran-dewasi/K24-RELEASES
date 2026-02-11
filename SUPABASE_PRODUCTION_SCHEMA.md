# K24 Supabase Production Schema

## 📋 Complete Table Schema

### 1. USER_PROFILES (Core User Data)
```sql
CREATE TABLE public.user_profiles (
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
    profile_picture_url TEXT,
    timezone TEXT DEFAULT 'Asia/Kolkata',
    language TEXT DEFAULT 'en',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Index for fast tenant lookup
CREATE INDEX idx_user_profiles_tenant ON public.user_profiles(tenant_id);
```

---

### 2. SUBSCRIPTIONS (Plans & Billing)
```sql
CREATE TABLE public.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL,
    
    -- Plan Details
    plan TEXT NOT NULL DEFAULT 'free', -- 'free', 'starter', 'pro', 'enterprise'
    plan_display_name TEXT,
    
    -- Status
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'cancelled', 'expired', 'paused', 'trial'
    
    -- Dates
    trial_starts_at TIMESTAMPTZ,
    trial_ends_at TIMESTAMPTZ,
    starts_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- NULL = never expires (lifetime/free)
    cancelled_at TIMESTAMPTZ,
    
    -- Billing
    billing_cycle TEXT DEFAULT 'monthly', -- 'monthly', 'yearly', 'lifetime'
    amount_paid DECIMAL(10, 2) DEFAULT 0,
    currency TEXT DEFAULT 'INR',
    payment_method TEXT,
    razorpay_subscription_id TEXT,
    razorpay_customer_id TEXT,
    
    -- Limits
    device_limit INTEGER DEFAULT 1,
    whatsapp_messages_limit INTEGER DEFAULT 100, -- per month
    ai_queries_limit INTEGER DEFAULT 500,       -- per month
    
    -- Usage This Month
    whatsapp_messages_used INTEGER DEFAULT 0,
    ai_queries_used INTEGER DEFAULT 0,
    
    -- Metadata
    features JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_status CHECK (status IN ('active', 'cancelled', 'expired', 'paused', 'trial'))
);

CREATE INDEX idx_subscriptions_user ON public.subscriptions(user_id);
CREATE INDEX idx_subscriptions_tenant ON public.subscriptions(tenant_id);
CREATE INDEX idx_subscriptions_status ON public.subscriptions(status);
CREATE INDEX idx_subscriptions_expires ON public.subscriptions(expires_at);
```

---

### 3. SUBSCRIPTION_PLANS (Plan Definitions)
```sql
CREATE TABLE public.subscription_plans (
    id TEXT PRIMARY KEY, -- 'free', 'starter', 'pro', 'enterprise'
    display_name TEXT NOT NULL,
    description TEXT,
    
    -- Pricing
    price_monthly DECIMAL(10, 2) DEFAULT 0,
    price_yearly DECIMAL(10, 2) DEFAULT 0,
    currency TEXT DEFAULT 'INR',
    
    -- Limits
    device_limit INTEGER DEFAULT 1,
    whatsapp_messages_limit INTEGER DEFAULT 100,
    ai_queries_limit INTEGER DEFAULT 500,
    storage_limit_gb INTEGER DEFAULT 1,
    
    -- Features (JSON)
    features JSONB DEFAULT '{}',
    -- Example: {"tally_sync": true, "whatsapp": true, "ai_assistant": true, "reports": ["basic"]}
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default plans
INSERT INTO public.subscription_plans (id, display_name, price_monthly, price_yearly, device_limit, whatsapp_messages_limit, ai_queries_limit, features) VALUES
('free', 'Free Trial', 0, 0, 1, 50, 100, '{"tally_sync": true, "whatsapp": false, "ai_assistant": true, "reports": ["basic"], "trial_days": 14}'),
('starter', 'Starter', 499, 4999, 1, 500, 1000, '{"tally_sync": true, "whatsapp": true, "ai_assistant": true, "reports": ["basic", "advanced"]}'),
('pro', 'Professional', 999, 9999, 3, 2000, 5000, '{"tally_sync": true, "whatsapp": true, "ai_assistant": true, "reports": ["basic", "advanced", "custom"], "priority_support": true}'),
('enterprise', 'Enterprise', 2499, 24999, 10, -1, -1, '{"tally_sync": true, "whatsapp": true, "ai_assistant": true, "reports": ["all"], "priority_support": true, "dedicated_support": true, "custom_integration": true}');
```

---

### 4. WHATSAPP_BINDINGS (Phone → User Mapping)
```sql
CREATE TABLE public.whatsapp_bindings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL,
    
    -- User's WhatsApp Number (the business owner)
    user_phone TEXT NOT NULL,
    
    -- Verification
    is_verified BOOLEAN DEFAULT FALSE,
    verification_code TEXT,
    code_expires_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_phone)
);

CREATE INDEX idx_whatsapp_bindings_user ON public.whatsapp_bindings(user_id);
CREATE INDEX idx_whatsapp_bindings_phone ON public.whatsapp_bindings(user_phone);
CREATE INDEX idx_whatsapp_bindings_tenant ON public.whatsapp_bindings(tenant_id);
```

---

### 5. WHATSAPP_CUSTOMER_MAPPINGS (Customer Phone → Tenant)
```sql
-- Maps customer phone numbers to their K24 business owner
CREATE TABLE public.whatsapp_customer_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL,
    
    -- Customer details
    customer_phone TEXT NOT NULL,
    customer_name TEXT,
    client_code TEXT,  -- For disambiguation when same customer has multiple suppliers
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_message_at TIMESTAMPTZ,
    message_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(customer_phone, tenant_id)
);

CREATE INDEX idx_customer_mappings_phone ON public.whatsapp_customer_mappings(customer_phone);
CREATE INDEX idx_customer_mappings_tenant ON public.whatsapp_customer_mappings(tenant_id);
```

---

### 6. DEVICE_LICENSES (Multi-Device Management)
```sql
CREATE TABLE public.device_licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_key TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL,
    
    -- Device Info
    device_fingerprint TEXT NOT NULL,
    device_name TEXT,
    device_os TEXT,
    app_version TEXT,
    
    -- Status
    status TEXT DEFAULT 'active', -- 'active', 'revoked', 'expired'
    
    -- Heartbeat
    last_heartbeat TIMESTAMPTZ,
    last_ip_address TEXT,
    
    -- Grace period (offline tolerance)
    grace_period_until TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(device_fingerprint, user_id)
);

CREATE INDEX idx_device_licenses_user ON public.device_licenses(user_id);
CREATE INDEX idx_device_licenses_fingerprint ON public.device_licenses(device_fingerprint);
```

---

### 7. WHATSAPP_MESSAGE_QUEUE (Incoming Message Queue)
```sql
CREATE TABLE public.whatsapp_message_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    
    -- Message Details
    sender_phone TEXT NOT NULL,
    sender_name TEXT,
    message_type TEXT DEFAULT 'text', -- 'text', 'image', 'document', 'audio'
    message_content TEXT,
    media_url TEXT,
    
    -- Processing Status
    status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'processed', 'failed'
    processing_started_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ,
    error_message TEXT,
    
    -- Response
    response_sent BOOLEAN DEFAULT FALSE,
    response_content TEXT,
    
    -- Metadata
    raw_payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_queue_status CHECK (status IN ('pending', 'processing', 'processed', 'failed'))
);

CREATE INDEX idx_message_queue_tenant ON public.whatsapp_message_queue(tenant_id);
CREATE INDEX idx_message_queue_status ON public.whatsapp_message_queue(status);
CREATE INDEX idx_message_queue_created ON public.whatsapp_message_queue(created_at DESC);
```

---

### 8. USAGE_LOGS (Track All Usage)
```sql
CREATE TABLE public.usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    tenant_id TEXT NOT NULL,
    
    -- Usage Type
    usage_type TEXT NOT NULL, -- 'whatsapp_message', 'ai_query', 'tally_sync', 'report_generated'
    
    -- Details
    description TEXT,
    quantity INTEGER DEFAULT 1,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_usage_logs_tenant ON public.usage_logs(tenant_id);
CREATE INDEX idx_usage_logs_type ON public.usage_logs(usage_type);
CREATE INDEX idx_usage_logs_month ON public.usage_logs(date_trunc('month', created_at));
```

---

## 🔧 Business Logic Functions

### Check Subscription Status
```sql
CREATE OR REPLACE FUNCTION check_subscription_status(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_subscription RECORD;
    v_result JSONB;
BEGIN
    SELECT * INTO v_subscription
    FROM public.subscriptions
    WHERE user_id = p_user_id
    ORDER BY created_at DESC
    LIMIT 1;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'status', 'no_subscription',
            'message', 'No subscription found',
            'can_access', FALSE
        );
    END IF;
    
    -- Check if expired
    IF v_subscription.expires_at IS NOT NULL AND v_subscription.expires_at < NOW() THEN
        -- Update status to expired
        UPDATE public.subscriptions SET status = 'expired' WHERE id = v_subscription.id;
        
        RETURN jsonb_build_object(
            'status', 'expired',
            'message', 'Subscription expired on ' || v_subscription.expires_at::date,
            'expired_at', v_subscription.expires_at,
            'can_access', FALSE,
            'plan', v_subscription.plan
        );
    END IF;
    
    -- Check if trial ending soon (< 3 days)
    IF v_subscription.status = 'trial' AND v_subscription.trial_ends_at IS NOT NULL THEN
        IF v_subscription.trial_ends_at < NOW() THEN
            UPDATE public.subscriptions SET status = 'expired' WHERE id = v_subscription.id;
            RETURN jsonb_build_object(
                'status', 'trial_expired',
                'message', 'Free trial ended',
                'can_access', FALSE
            );
        ELSIF v_subscription.trial_ends_at < NOW() + INTERVAL '3 days' THEN
            RETURN jsonb_build_object(
                'status', 'trial_ending_soon',
                'message', 'Trial ends in ' || EXTRACT(DAY FROM v_subscription.trial_ends_at - NOW()) || ' days',
                'trial_ends_at', v_subscription.trial_ends_at,
                'can_access', TRUE,
                'plan', v_subscription.plan
            );
        END IF;
    END IF;
    
    -- Active subscription
    RETURN jsonb_build_object(
        'status', v_subscription.status,
        'plan', v_subscription.plan,
        'expires_at', v_subscription.expires_at,
        'can_access', TRUE,
        'limits', jsonb_build_object(
            'devices', v_subscription.device_limit,
            'whatsapp_messages', v_subscription.whatsapp_messages_limit,
            'whatsapp_used', v_subscription.whatsapp_messages_used,
            'ai_queries', v_subscription.ai_queries_limit,
            'ai_used', v_subscription.ai_queries_used
        )
    );
END;
$$ LANGUAGE plpgsql;
```

---

### Check & Increment Usage
```sql
CREATE OR REPLACE FUNCTION increment_usage(
    p_user_id UUID,
    p_usage_type TEXT,
    p_quantity INTEGER DEFAULT 1
)
RETURNS JSONB AS $$
DECLARE
    v_subscription RECORD;
    v_limit INTEGER;
    v_used INTEGER;
    v_allowed BOOLEAN := FALSE;
BEGIN
    -- Get active subscription
    SELECT * INTO v_subscription
    FROM public.subscriptions
    WHERE user_id = p_user_id AND status IN ('active', 'trial')
    ORDER BY created_at DESC
    LIMIT 1;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('allowed', FALSE, 'reason', 'No active subscription');
    END IF;
    
    -- Check limits based on usage type
    IF p_usage_type = 'whatsapp_message' THEN
        v_limit := v_subscription.whatsapp_messages_limit;
        v_used := v_subscription.whatsapp_messages_used;
        
        IF v_limit = -1 OR v_used + p_quantity <= v_limit THEN
            v_allowed := TRUE;
            UPDATE public.subscriptions 
            SET whatsapp_messages_used = whatsapp_messages_used + p_quantity
            WHERE id = v_subscription.id;
        END IF;
        
    ELSIF p_usage_type = 'ai_query' THEN
        v_limit := v_subscription.ai_queries_limit;
        v_used := v_subscription.ai_queries_used;
        
        IF v_limit = -1 OR v_used + p_quantity <= v_limit THEN
            v_allowed := TRUE;
            UPDATE public.subscriptions 
            SET ai_queries_used = ai_queries_used + p_quantity
            WHERE id = v_subscription.id;
        END IF;
    ELSE
        v_allowed := TRUE; -- No limit for other types
    END IF;
    
    -- Log usage
    IF v_allowed THEN
        INSERT INTO public.usage_logs (user_id, tenant_id, usage_type, quantity)
        VALUES (p_user_id, v_subscription.tenant_id, p_usage_type, p_quantity);
    END IF;
    
    RETURN jsonb_build_object(
        'allowed', v_allowed,
        'limit', v_limit,
        'used', v_used + p_quantity,
        'remaining', CASE WHEN v_limit = -1 THEN 'unlimited' ELSE (v_limit - v_used - p_quantity)::text END
    );
END;
$$ LANGUAGE plpgsql;
```

---

### Reset Monthly Usage (Run via Cron)
```sql
CREATE OR REPLACE FUNCTION reset_monthly_usage()
RETURNS void AS $$
BEGIN
    UPDATE public.subscriptions
    SET 
        whatsapp_messages_used = 0,
        ai_queries_used = 0,
        updated_at = NOW()
    WHERE status IN ('active', 'trial');
    
    RAISE NOTICE 'Monthly usage reset completed at %', NOW();
END;
$$ LANGUAGE plpgsql;
```

---

## 🔐 Row Level Security (RLS)

```sql
-- Enable RLS on all tables
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsapp_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsapp_customer_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.device_licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsapp_message_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_logs ENABLE ROW LEVEL SECURITY;

-- User can only access their own data
CREATE POLICY user_profiles_policy ON public.user_profiles
    FOR ALL USING (auth.uid() = id);

CREATE POLICY subscriptions_policy ON public.subscriptions
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY whatsapp_bindings_policy ON public.whatsapp_bindings
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY customer_mappings_policy ON public.whatsapp_customer_mappings
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY device_licenses_policy ON public.device_licenses
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY message_queue_policy ON public.whatsapp_message_queue
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY usage_logs_policy ON public.usage_logs
    FOR ALL USING (auth.uid() = user_id);
```

---

## 📊 Useful Views

### Active Subscribers
```sql
CREATE VIEW active_subscribers AS
SELECT 
    u.id,
    u.full_name,
    u.company_name,
    u.tenant_id,
    s.plan,
    s.status,
    s.expires_at,
    s.whatsapp_messages_limit,
    s.whatsapp_messages_used,
    ROUND((s.whatsapp_messages_used::decimal / NULLIF(s.whatsapp_messages_limit, 0)) * 100, 1) as usage_percent
FROM public.user_profiles u
JOIN public.subscriptions s ON u.id = s.user_id
WHERE s.status IN ('active', 'trial')
ORDER BY s.expires_at ASC NULLS LAST;
```

### Expiring Soon (Next 7 Days)
```sql
CREATE VIEW expiring_soon AS
SELECT 
    u.full_name,
    u.company_name,
    up.tenant_id,
    s.plan,
    s.expires_at,
    s.expires_at - NOW() as time_remaining
FROM auth.users u
JOIN public.user_profiles up ON u.id = up.id
JOIN public.subscriptions s ON u.id = s.user_id
WHERE s.expires_at IS NOT NULL
  AND s.expires_at BETWEEN NOW() AND NOW() + INTERVAL '7 days'
  AND s.status = 'active'
ORDER BY s.expires_at ASC;
```

---

## 🔑 Key Queries for Backend

### 1. On Login - Get Full User Context
```sql
SELECT 
    u.id,
    up.tenant_id,
    up.full_name,
    up.company_name,
    s.plan,
    s.status as subscription_status,
    s.expires_at,
    s.device_limit,
    (SELECT COUNT(*) FROM device_licenses dl WHERE dl.user_id = u.id AND dl.status = 'active') as active_devices,
    wb.is_verified as whatsapp_verified
FROM auth.users u
LEFT JOIN user_profiles up ON u.id = up.id
LEFT JOIN subscriptions s ON u.id = s.user_id AND s.status IN ('active', 'trial')
LEFT JOIN whatsapp_bindings wb ON u.id = wb.user_id AND wb.is_active = TRUE
WHERE u.id = $1;
```

### 2. On WhatsApp Message - Route to Tenant
```sql
SELECT 
    wcm.tenant_id,
    wcm.user_id,
    wcm.customer_name,
    s.status as subscription_status,
    (s.status IN ('active', 'trial')) as can_process
FROM whatsapp_customer_mappings wcm
JOIN subscriptions s ON wcm.user_id = s.user_id
WHERE wcm.customer_phone = $1
  AND wcm.is_active = TRUE
  AND s.status IN ('active', 'trial');
```

---

## 📅 Scheduled Jobs (Supabase Edge Functions or External Cron)

1. **Daily: Check Expired Subscriptions**
2. **Daily: Send Expiry Warnings (3 days, 1 day before)**
3. **Monthly: Reset Usage Counters**
4. **Hourly: Check Device Heartbeats (revoke inactive)**

---

*Created: January 29, 2026*
*For: K24 Production Supabase Schema*
