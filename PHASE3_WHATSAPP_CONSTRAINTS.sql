-- ============================================
-- PHASE 3: WhatsApp Tenant Linking - DB Constraints
-- ============================================
-- Run this in Supabase SQL Editor to add uniqueness constraint
-- This prevents race conditions where two tenants try to claim the same WhatsApp number

-- 1. Add unique constraint on tenants.whatsapp_number
-- Only one tenant can have a specific WhatsApp number (when not null)
ALTER TABLE public.tenants 
ADD CONSTRAINT unique_tenant_whatsapp 
UNIQUE (whatsapp_number);

-- If the above fails because duplicates exist, run this first to find them:
-- SELECT whatsapp_number, COUNT(*) FROM tenants 
-- WHERE whatsapp_number IS NOT NULL 
-- GROUP BY whatsapp_number HAVING COUNT(*) > 1;

-- 2. Add unique constraint on users_profile.whatsapp_number (if exists)
-- This ensures no two users can claim the same WhatsApp number
-- Note: This column may not exist in Supabase if using local SQLite only
-- ALTER TABLE public.users_profile 
-- ADD CONSTRAINT unique_user_whatsapp 
-- UNIQUE (whatsapp_number);

-- 3. Create index for faster WhatsApp lookups
CREATE INDEX IF NOT EXISTS idx_tenants_whatsapp 
ON public.tenants(whatsapp_number) 
WHERE whatsapp_number IS NOT NULL;

-- 4. Verification query
SELECT 
    id as tenant_id,
    company_name,
    whatsapp_number
FROM public.tenants 
WHERE whatsapp_number IS NOT NULL
ORDER BY id;
