-- ============================================================
-- K24 AUTH & WORKFLOW MIGRATION (Non-Destructive)
-- ============================================================

-- 1. SUBSCRIPTIONS (REQUIRED for Login Flow)
-- We need this so when a user registers, we can start their trial.
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free',
    status TEXT NOT NULL DEFAULT 'trial', -- 'trial', 'active', 'expired'
    trial_starts_at TIMESTAMPTZ DEFAULT NOW(),
    trial_ends_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '14 days'),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
-- Add indexes for speed
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON public.subscriptions(user_id);

-- 2. WHATSAPP BINDINGS (REQUIRED for Verification Flow)
CREATE TABLE IF NOT EXISTS public.whatsapp_bindings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_code TEXT,
    code_expires_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. FUNCTION: Check Subscription (REQUIRED for /api/auth/subscription endpoint)
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
    
    -- Logic: If trial expired
    IF v_sub.status = 'trial' AND v_sub.trial_ends_at < NOW() THEN
        RETURN jsonb_build_object('status', 'trial_expired', 'can_access', FALSE);
    END IF;
    
    RETURN jsonb_build_object(
        'status', v_sub.status,
        'plan', v_sub.plan,
        'can_access', TRUE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. RLS POLICIES (Security)
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsapp_bindings ENABLE ROW LEVEL SECURITY;

-- Allow users to read their own data
DROP POLICY IF EXISTS "Users view own subscription" ON public.subscriptions;
CREATE POLICY "Users view own subscription" ON public.subscriptions FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users view own bindings" ON public.whatsapp_bindings;
CREATE POLICY "Users view own bindings" ON public.whatsapp_bindings FOR SELECT USING (auth.uid() = user_id);

-- 5. FIX USER PROFILES (Ensure compatibility)
-- You have 'users_profile', backend often expects 'user_profiles'. 
-- Let's create a View so backend code works with your existing table OR create the missing one if 'users_profile' was a typo.
-- Assuming 'users_profile' is your master table:

-- (Optional) If you want to sync auth.users to users_profile automatically
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users_profile (id, full_name, tenant_id)
  VALUES (new.id, new.raw_user_meta_data->>'full_name', 'TENANT-' || substr(new.id::text, 1, 8))
  ON CONFLICT (id) DO NOTHING;
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger on Sign Up
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
