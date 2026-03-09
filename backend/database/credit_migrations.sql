-- ============================================================
-- K24 CREDIT & USAGE SYSTEM — MIGRATION v1
-- Run this in your Supabase SQL Editor
-- Safe: Uses IF NOT EXISTS throughout. Non-destructive.
-- ============================================================
-- Tables created:
--   plans, tenant_plans, billing_cycles,
--   credit_rules, usage_events,
--   tenant_usage_summary, llm_calls
-- Plus: increment_usage_atomic() Postgres function for concurrency safety
-- ============================================================

-- ─── 1. PLANS ───────────────────────────────────────────────
-- Defines pricing tiers. Admin-managed, rarely changes.
CREATE TABLE IF NOT EXISTS public.plans (
    id                      TEXT PRIMARY KEY,         -- 'starter', 'pro', 'enterprise'
    display_name            TEXT NOT NULL,             -- 'Starter', 'Pro', 'Enterprise'
    price_monthly_paise     INTEGER NOT NULL DEFAULT 0,-- Price in paise (₹1299 = 129900)
    max_credits_per_cycle   INTEGER NOT NULL,          -- 500, 2500, 10000
    max_companies           INTEGER NOT NULL DEFAULT 1,
    enforcement_mode        TEXT NOT NULL DEFAULT 'HARD_CAP', -- HARD_CAP | SOFT_CAP | NO_CAP_LOG_ONLY
    features_json           JSONB NOT NULL DEFAULT '{}',
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 2. TENANT_PLANS ─────────────────────────────────────────
-- Links a tenant to their active plan. Separate from the legacy
-- 'subscriptions' table to avoid breaking existing auth flows.
CREATE TABLE IF NOT EXISTS public.tenant_plans (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               TEXT NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    plan_id                 TEXT NOT NULL REFERENCES public.plans(id),
    status                  TEXT NOT NULL DEFAULT 'trial', -- trial | active | suspended | cancelled
    trial_ends_at           TIMESTAMPTZ,
    current_period_start    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_period_end      TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '1 month'),
    notes                   TEXT,                      -- Enterprise custom terms
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tenant_plans_tenant ON public.tenant_plans(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_plans_status ON public.tenant_plans(status);

-- Ensure only one active plan per tenant at a time
CREATE UNIQUE INDEX IF NOT EXISTS idx_tenant_plans_active_unique
    ON public.tenant_plans(tenant_id)
    WHERE status IN ('active', 'trial');

-- ─── 3. BILLING_CYCLES ───────────────────────────────────────
-- One row per tenant per billing period (monthly by default).
-- Closed at end of period; a new one is opened on next usage.
CREATE TABLE IF NOT EXISTS public.billing_cycles (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               TEXT NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    plan_id                 TEXT NOT NULL REFERENCES public.plans(id),
    cycle_start             TIMESTAMPTZ NOT NULL,
    cycle_end               TIMESTAMPTZ NOT NULL,
    status                  TEXT NOT NULL DEFAULT 'active', -- active | closed | grace
    -- Snapshot of plan limit at cycle creation (in case plan changes mid-year)
    max_credits             INTEGER NOT NULL,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_billing_cycles_tenant ON public.billing_cycles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_billing_cycles_status ON public.billing_cycles(status);

-- Only one ACTIVE cycle per tenant
CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_cycles_active_unique
    ON public.billing_cycles(tenant_id)
    WHERE status = 'active';

-- ─── 4. CREDIT_RULES ─────────────────────────────────────────
-- The configurable rating table. Controls how many credits each
-- event type consumes. Change values here — never in business code.
CREATE TABLE IF NOT EXISTS public.credit_rules (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type              TEXT NOT NULL,  -- VOUCHER | DOCUMENT | MESSAGE
    event_subtype           TEXT NOT NULL,  -- created | updated | page_processed | action | info_query
    credits                 NUMERIC(10, 4) NOT NULL DEFAULT 0,
    -- Future: JSON conditions like {"page_count": {"gte": 5}, "multiply_by": "page_count"}
    conditions_json         JSONB DEFAULT '{}',
    description             TEXT,
    effective_from          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effective_to            TIMESTAMPTZ,   -- NULL = forever
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credit_rules_lookup
    ON public.credit_rules(event_type, event_subtype, is_active);

-- ─── 5. USAGE_EVENTS ─────────────────────────────────────────
-- Immutable append-only log. One row per business event.
-- DO NOT update rows here — only INSERT.
CREATE TABLE IF NOT EXISTS public.usage_events (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               TEXT NOT NULL REFERENCES public.tenants(id),
    company_id              INTEGER,                   -- FK to local companies table (nullable)
    billing_cycle_id        UUID REFERENCES public.billing_cycles(id),
    event_type              TEXT NOT NULL,             -- VOUCHER | DOCUMENT | MESSAGE
    event_subtype           TEXT NOT NULL,             -- created | updated | page_processed | action | info_query
    credits_consumed        NUMERIC(10, 4) NOT NULL DEFAULT 0,
    source                  TEXT DEFAULT 'api',        -- whatsapp | kittu | api | web | tally_sync
    -- Contextual data (voucher_id, voucher_type, page_count, message_id, etc.)
    metadata_json           JSONB DEFAULT '{}',
    -- Decision outcome from credit engine
    status                  TEXT NOT NULL DEFAULT 'ALLOWED', -- ALLOWED | NEAR_LIMIT | OVER_LIMIT | BLOCKED
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_events_tenant ON public.usage_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_cycle ON public.usage_events(billing_cycle_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_type ON public.usage_events(event_type);
CREATE INDEX IF NOT EXISTS idx_usage_events_created ON public.usage_events(created_at DESC);

-- ─── 6. TENANT_USAGE_SUMMARY ─────────────────────────────────
-- Materialized running totals per billing cycle.
-- NEVER write directly — only updated via increment_usage_atomic().
-- This is the fast path for "how many credits used?" queries.
CREATE TABLE IF NOT EXISTS public.tenant_usage_summary (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               TEXT NOT NULL REFERENCES public.tenants(id),
    billing_cycle_id        UUID NOT NULL REFERENCES public.billing_cycles(id),
    -- Running credit totals
    credits_used_total      NUMERIC(10, 4) NOT NULL DEFAULT 0,
    credits_used_voucher    NUMERIC(10, 4) NOT NULL DEFAULT 0,
    credits_used_document   NUMERIC(10, 4) NOT NULL DEFAULT 0,
    credits_used_message    NUMERIC(10, 4) NOT NULL DEFAULT 0,
    -- Running event counts
    events_count_total      INTEGER NOT NULL DEFAULT 0,
    events_count_voucher    INTEGER NOT NULL DEFAULT 0,
    events_count_document   INTEGER NOT NULL DEFAULT 0,
    events_count_message    INTEGER NOT NULL DEFAULT 0,
    updated_at              TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT tenant_usage_summary_cycle_unique UNIQUE(billing_cycle_id)
);

CREATE INDEX IF NOT EXISTS idx_usage_summary_tenant ON public.tenant_usage_summary(tenant_id);

-- ─── 7. LLM_CALLS ────────────────────────────────────────────
-- Cost analytics only — never used for billing.
-- Tracks every LLM API call per tenant for cost optimization.
CREATE TABLE IF NOT EXISTS public.llm_calls (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               TEXT NOT NULL,
    usage_event_id          UUID REFERENCES public.usage_events(id), -- nullable link
    model                   TEXT NOT NULL,             -- gemini-2.0-flash | deepseek-v3 etc.
    workflow                TEXT,                      -- bill_extraction | voucher_creation | kittu_query
    tokens_input            INTEGER NOT NULL DEFAULT 0,
    tokens_output           INTEGER NOT NULL DEFAULT 0,
    tokens_total            INTEGER GENERATED ALWAYS AS (tokens_input + tokens_output) STORED,
    cost_estimated_usd      NUMERIC(12, 8) NOT NULL DEFAULT 0,
    duration_ms             INTEGER,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_calls_tenant ON public.llm_calls(tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_cycle_lookup
    ON public.llm_calls(tenant_id, created_at DESC);

-- ============================================================
-- ATOMIC INCREMENT FUNCTION
-- Called whenever a usage event is recorded.
-- Uses a single UPDATE so concurrent requests cannot cause
-- double-counting or negative counts (no read-modify-write).
-- ============================================================
CREATE OR REPLACE FUNCTION public.increment_usage_atomic(
    p_tenant_id             TEXT,
    p_billing_cycle_id      UUID,
    p_event_type            TEXT,           -- VOUCHER | DOCUMENT | MESSAGE
    p_credits               NUMERIC(10, 4)
)
RETURNS public.tenant_usage_summary
LANGUAGE plpgsql
AS $$
DECLARE
    v_result public.tenant_usage_summary;
BEGIN
    -- Upsert the summary row (create on first usage in a cycle)
    INSERT INTO public.tenant_usage_summary (tenant_id, billing_cycle_id)
    VALUES (p_tenant_id, p_billing_cycle_id)
    ON CONFLICT (billing_cycle_id) DO NOTHING;

    -- Atomically increment the correct bucket
    UPDATE public.tenant_usage_summary
    SET
        credits_used_total    = credits_used_total    + p_credits,
        events_count_total    = events_count_total    + 1,

        credits_used_voucher  = credits_used_voucher  +
            CASE WHEN p_event_type = 'VOUCHER'   THEN p_credits ELSE 0 END,
        credits_used_document = credits_used_document +
            CASE WHEN p_event_type = 'DOCUMENT'  THEN p_credits ELSE 0 END,
        credits_used_message  = credits_used_message  +
            CASE WHEN p_event_type = 'MESSAGE'   THEN p_credits ELSE 0 END,

        events_count_voucher  = events_count_voucher  +
            CASE WHEN p_event_type = 'VOUCHER'   THEN 1 ELSE 0 END,
        events_count_document = events_count_document +
            CASE WHEN p_event_type = 'DOCUMENT'  THEN 1 ELSE 0 END,
        events_count_message  = events_count_message  +
            CASE WHEN p_event_type = 'MESSAGE'   THEN 1 ELSE 0 END,

        updated_at            = NOW()
    WHERE billing_cycle_id = p_billing_cycle_id
    RETURNING * INTO v_result;

    RETURN v_result;
END;
$$;

-- ============================================================
-- RLS POLICIES
-- Credit data is admin-only from the client side.
-- All writes happen via service_role from the backend.
-- ============================================================

-- plans: publicly readable (tenants can see plan info), admin writes
ALTER TABLE public.plans ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read plans" ON public.plans;
CREATE POLICY "Public read plans" ON public.plans FOR SELECT USING (true);
DROP POLICY IF EXISTS "Service role writes plans" ON public.plans;
CREATE POLICY "Service role writes plans" ON public.plans FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role')
    WITH CHECK (auth.jwt() ->> 'role' = 'service_role');

-- tenant_plans: tenant can read own, service_role writes
ALTER TABLE public.tenant_plans ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Tenant reads own plan" ON public.tenant_plans;
CREATE POLICY "Tenant reads own plan" ON public.tenant_plans FOR SELECT
    USING (tenant_id IN (SELECT tenant_id FROM public.users_profile WHERE id = auth.uid()));
DROP POLICY IF EXISTS "Service role writes tenant_plans" ON public.tenant_plans;
CREATE POLICY "Service role writes tenant_plans" ON public.tenant_plans FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role')
    WITH CHECK (auth.jwt() ->> 'role' = 'service_role');

-- billing_cycles: tenant readable, service_role writes
ALTER TABLE public.billing_cycles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Tenant reads own cycles" ON public.billing_cycles;
CREATE POLICY "Tenant reads own cycles" ON public.billing_cycles FOR SELECT
    USING (tenant_id IN (SELECT tenant_id FROM public.users_profile WHERE id = auth.uid()));
DROP POLICY IF EXISTS "Service role writes cycles" ON public.billing_cycles;
CREATE POLICY "Service role writes cycles" ON public.billing_cycles FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role')
    WITH CHECK (auth.jwt() ->> 'role' = 'service_role');

-- credit_rules: publicly readable, service_role writes
ALTER TABLE public.credit_rules ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read credit rules" ON public.credit_rules;
CREATE POLICY "Public read credit rules" ON public.credit_rules FOR SELECT USING (true);
DROP POLICY IF EXISTS "Service role writes credit_rules" ON public.credit_rules;
CREATE POLICY "Service role writes credit_rules" ON public.credit_rules FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role')
    WITH CHECK (auth.jwt() ->> 'role' = 'service_role');

-- usage_events: service_role only (internal logging)
ALTER TABLE public.usage_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role usage_events" ON public.usage_events;
CREATE POLICY "Service role usage_events" ON public.usage_events FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role')
    WITH CHECK (auth.jwt() ->> 'role' = 'service_role');

-- tenant_usage_summary: tenant can read own
ALTER TABLE public.tenant_usage_summary ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Tenant reads own summary" ON public.tenant_usage_summary;
CREATE POLICY "Tenant reads own summary" ON public.tenant_usage_summary FOR SELECT
    USING (tenant_id IN (SELECT tenant_id FROM public.users_profile WHERE id = auth.uid()));
DROP POLICY IF EXISTS "Service role writes summary" ON public.tenant_usage_summary;
CREATE POLICY "Service role writes summary" ON public.tenant_usage_summary FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role')
    WITH CHECK (auth.jwt() ->> 'role' = 'service_role');

-- llm_calls: service_role only
ALTER TABLE public.llm_calls ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role llm_calls" ON public.llm_calls;
CREATE POLICY "Service role llm_calls" ON public.llm_calls FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role')
    WITH CHECK (auth.jwt() ->> 'role' = 'service_role');

-- ============================================================
-- SEED DATA — Plans
-- ============================================================
INSERT INTO public.plans (id, display_name, price_monthly_paise, max_credits_per_cycle, max_companies, enforcement_mode, features_json)
VALUES
    ('starter',    'Starter',    129900,  500,   1,  'HARD_CAP',         '{"whatsapp_enabled": true,  "kittu_enabled": true,  "bulk_import": false}'),
    ('pro',        'Pro',        399900,  2500,  3,  'SOFT_CAP',         '{"whatsapp_enabled": true,  "kittu_enabled": true,  "bulk_import": true}'),
    ('enterprise', 'Enterprise', 0,       10000, 10, 'NO_CAP_LOG_ONLY',  '{"whatsapp_enabled": true,  "kittu_enabled": true,  "bulk_import": true, "dedicated_support": true}')
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- SEED DATA — Credit Rules (V1)
-- These are THE source of truth for credit costs.
-- Change here, not in application code.
-- ============================================================
INSERT INTO public.credit_rules (event_type, event_subtype, credits, description)
VALUES
    ('VOUCHER',  'created',        1.0, 'One credit per voucher successfully created in Tally'),
    ('VOUCHER',  'updated',        1.0, 'One credit per voucher successfully updated in Tally'),
    ('DOCUMENT', 'page_processed', 1.0, 'One credit per document page processed (image/PDF → structured data)'),
    ('MESSAGE',  'action',         0.0, 'No credit cost for message-triggered actions (tracked for analytics only)'),
    ('MESSAGE',  'info_query',     0.0, 'No credit cost for informational queries (e.g. show sales, GST due)')
ON CONFLICT DO NOTHING;

-- ============================================================
-- MIGRATION COMPLETE
-- ============================================================
-- Summary:
--   ✅ 7 new tables created
--   ✅ increment_usage_atomic() function created
--   ✅ RLS policies applied (service_role for writes, tenant for reads)
--   ✅ Plans seeded: Starter / Pro / Enterprise
--   ✅ Credit rules seeded: V1 rules (voucher=1cr, doc=1cr, message=0cr)
--
-- AFTER RUNNING THIS:
--   1. Run backend/credit_engine/ Python module
--   2. Wire record_event() into tally_live_update.py, extraction/, whatsapp.py
-- ============================================================
