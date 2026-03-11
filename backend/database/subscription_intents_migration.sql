-- ============================================================
-- K24 SUBSCRIPTION INTENTS — MIGRATION v2
-- Append to credit_migrations.sql or run separately in Supabase SQL Editor
-- ============================================================

CREATE TABLE IF NOT EXISTS public.subscription_intents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Plan selected
    plan_id             TEXT NOT NULL REFERENCES public.plans(id),
    amount_paise        INTEGER NOT NULL,           -- snapshot at time of intent

    -- User info (collected on form)
    name                TEXT NOT NULL,
    company_name        TEXT NOT NULL,
    email               TEXT NOT NULL,
    phone               TEXT NOT NULL,
    gst_number          TEXT,                        -- optional

    -- UPI payment proof (filled in step 2)
    upi_ref             TEXT,                        -- UTR / transaction ref
    screenshot_url      TEXT,                        -- storage URL (optional)

    -- Lifecycle status
    -- pending_payment → awaiting_verification → activated | rejected
    status              TEXT NOT NULL DEFAULT 'pending_payment',

    -- Admin
    admin_note          TEXT,
    activated_tenant_id TEXT,                        -- set on activation
    activated_at        TIMESTAMPTZ,

    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sub_intents_status    ON public.subscription_intents(status);
CREATE INDEX IF NOT EXISTS idx_sub_intents_email     ON public.subscription_intents(email);
CREATE INDEX IF NOT EXISTS idx_sub_intents_created   ON public.subscription_intents(created_at DESC);

-- RLS: service_role only (no client-side reads for privacy)
ALTER TABLE public.subscription_intents ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role subscription_intents" ON public.subscription_intents;
CREATE POLICY "Service role subscription_intents" ON public.subscription_intents FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role')
    WITH CHECK (auth.jwt() ->> 'role' = 'service_role');

-- ============================================================
-- MIGRATION v2 COMPLETE
-- ============================================================
