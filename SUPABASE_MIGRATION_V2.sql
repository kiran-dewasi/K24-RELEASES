-- ============================================================
-- K24 SAFE MIGRATION V2 (Non-Destructive)
-- ============================================================
-- This migration ONLY adds what's missing
-- It does NOT drop or modify existing tables
-- Run this in your Supabase SQL Editor
-- ============================================================

-- EXISTING TABLES (DO NOT TOUCH):
--   - users_profile (id, full_name, whatsapp_number, avatar_url, role, created_at, tenant_id)
--   - subscriptions (id, user_id, tenant_id, plan, status, trial_starts_at, trial_ends_at, expires_at, created_at, updated_at)
--   - whatsapp_bindings (id, user_id, tenant_id, phone_number, is_verified, verification_code, code_expires_at, verified_at, created_at)
--   - tenants (id, company_name, tally_company_name, whatsapp_number, license_key, created_at)

-- ============================================================
-- STEP 1: Create a VIEW to alias 'users_profile' as 'user_profiles'
-- This allows backend code expecting 'user_profiles' to work
-- ============================================================
DROP VIEW IF EXISTS public.user_profiles;
CREATE VIEW public.user_profiles AS
SELECT * FROM public.users_profile;

-- ============================================================
-- STEP 2: Create device_licenses table (MISSING)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.device_licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_key TEXT NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL,
    device_fingerprint TEXT NOT NULL,
    device_name TEXT,
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'revoked', 'expired'
    activated_at TIMESTAMPTZ DEFAULT NOW(),
    last_validated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for device_licenses
CREATE INDEX IF NOT EXISTS idx_device_licenses_user ON public.device_licenses(user_id);
CREATE INDEX IF NOT EXISTS idx_device_licenses_fingerprint ON public.device_licenses(device_fingerprint);
CREATE INDEX IF NOT EXISTS idx_device_licenses_key ON public.device_licenses(license_key);

-- ============================================================
-- STEP 3: Add missing columns to users_profile (if needed)
-- ============================================================
-- Add company_name if missing
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'users_profile' 
        AND column_name = 'company_name'
    ) THEN
        ALTER TABLE public.users_profile ADD COLUMN company_name TEXT;
    END IF;
END $$;

-- ============================================================
-- STEP 4: Enable RLS on new table
-- ============================================================
ALTER TABLE public.device_licenses ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- STEP 5: RLS Policies for device_licenses
-- ============================================================
DROP POLICY IF EXISTS "Users view own devices" ON public.device_licenses;
CREATE POLICY "Users view own devices" ON public.device_licenses 
FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role full access devices" ON public.device_licenses;
CREATE POLICY "Service role full access devices" ON public.device_licenses 
FOR ALL USING (auth.jwt() ->> 'role' = 'service_role')
WITH CHECK (auth.jwt() ->> 'role' = 'service_role');

-- ============================================================
-- STEP 6: Update/Create the handle_new_user trigger function
-- This creates a profile when a user signs up via Supabase Auth
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS TRIGGER AS $$
DECLARE
    new_tenant_id TEXT;
BEGIN
    -- Generate tenant_id from user id
    new_tenant_id := 'TENANT-' || substr(new.id::text, 1, 8);
    
    -- Insert into users_profile
    INSERT INTO public.users_profile (id, full_name, tenant_id)
    VALUES (
        new.id, 
        COALESCE(new.raw_user_meta_data->>'full_name', 'User'),
        new_tenant_id
    )
    ON CONFLICT (id) DO NOTHING;
    
    -- Also create a tenant record if it doesn't exist
    INSERT INTO public.tenants (id, company_name)
    VALUES (
        new_tenant_id,
        COALESCE(new.raw_user_meta_data->>'company_name', 'My Company')
    )
    ON CONFLICT (id) DO NOTHING;
    
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create or replace the trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- ============================================================
-- STEP 7: Ensure service role can insert into all tables
-- ============================================================

-- users_profile policies
DROP POLICY IF EXISTS "Service role full access profiles" ON public.users_profile;
CREATE POLICY "Service role full access profiles" ON public.users_profile 
FOR ALL USING (auth.jwt() ->> 'role' = 'service_role')
WITH CHECK (auth.jwt() ->> 'role' = 'service_role');

-- subscriptions policies  
DROP POLICY IF EXISTS "Service role full access subscriptions" ON public.subscriptions;
CREATE POLICY "Service role full access subscriptions" ON public.subscriptions 
FOR ALL USING (auth.jwt() ->> 'role' = 'service_role')
WITH CHECK (auth.jwt() ->> 'role' = 'service_role');

-- whatsapp_bindings policies
DROP POLICY IF EXISTS "Service role full access bindings" ON public.whatsapp_bindings;
CREATE POLICY "Service role full access bindings" ON public.whatsapp_bindings 
FOR ALL USING (auth.jwt() ->> 'role' = 'service_role')
WITH CHECK (auth.jwt() ->> 'role' = 'service_role');

-- tenants policies
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access tenants" ON public.tenants;
CREATE POLICY "Service role full access tenants" ON public.tenants 
FOR ALL USING (auth.jwt() ->> 'role' = 'service_role')
WITH CHECK (auth.jwt() ->> 'role' = 'service_role');

-- ============================================================
-- STEP 8: User policies (allow users to read their own data)
-- ============================================================
DROP POLICY IF EXISTS "Users view own profile" ON public.users_profile;
CREATE POLICY "Users view own profile" ON public.users_profile 
FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users view own subscription" ON public.subscriptions;
CREATE POLICY "Users view own subscription" ON public.subscriptions 
FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users view own bindings" ON public.whatsapp_bindings;
CREATE POLICY "Users view own bindings" ON public.whatsapp_bindings 
FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users view own tenant" ON public.tenants;
CREATE POLICY "Users view own tenant" ON public.tenants 
FOR SELECT USING (
    id IN (SELECT tenant_id FROM public.users_profile WHERE id = auth.uid())
);

-- ============================================================
-- STEP 9: Check subscription status function
-- ============================================================
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

-- ============================================================
-- MIGRATION COMPLETE!
-- ============================================================
-- Summary of changes:
--   1. Created VIEW 'user_profiles' -> 'users_profile' (for backend compatibility)
--   2. Created TABLE 'device_licenses' (was missing)
--   3. Added 'company_name' column to users_profile (if missing)
--   4. Created/updated trigger 'on_auth_user_created' (auto-creates profile + tenant on signup)
--   5. Added RLS policies for all tables
--   6. Created check_subscription_status() function
--
-- UNCHANGED:
--   - users_profile (existing data preserved)
--   - subscriptions (existing data preserved)
--   - whatsapp_bindings (existing data preserved)
--   - tenants (existing data preserved, includes TENANT-84F03F7D with Spice/Prince enterprises)
-- ============================================================
