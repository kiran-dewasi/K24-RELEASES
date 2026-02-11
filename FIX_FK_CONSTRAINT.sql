-- ============================================================
-- FIX FOREIGN KEY CONSTRAINT ON users_profile
-- Run this in Supabase SQL Editor
-- ============================================================

-- Check existing constraints
SELECT
    tc.constraint_name, 
    tc.table_name, 
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.table_name = 'users_profile' 
    AND tc.constraint_type = 'FOREIGN KEY';

-- DROP the foreign key constraint on tenant_id (it was linking to tenants table)
ALTER TABLE public.users_profile 
DROP CONSTRAINT IF EXISTS users_profile_tenant_id_fkey;

-- Now tenant_id is just a TEXT column with no constraint
-- The trigger will auto-create both the profile AND the tenant

-- Verify it worked
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'users_profile'
ORDER BY ordinal_position;
