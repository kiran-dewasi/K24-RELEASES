-- ============================================
-- PHASE 4: Performance Indexes for Multi-Tenant Queries
-- ============================================
-- Run these in SQLite (local) and Supabase (cloud)
-- These indexes dramatically speed up tenant-filtered queries

-- ============================================
-- LOCAL SQLite Indexes
-- ============================================

-- Vouchers: tenant + date (for date-range queries like "sales this month")
CREATE INDEX IF NOT EXISTS idx_vouchers_tenant_date 
ON vouchers(tenant_id, date);

-- Vouchers: tenant + party (for party-specific queries like "ABC Corp's invoices")
CREATE INDEX IF NOT EXISTS idx_vouchers_tenant_party 
ON vouchers(tenant_id, party_name);

-- Vouchers: tenant + type (for type-filtered queries like "all purchases")
CREATE INDEX IF NOT EXISTS idx_vouchers_tenant_type 
ON vouchers(tenant_id, voucher_type);

-- Ledgers: tenant + parent (for group-based queries like "all sundry debtors")
CREATE INDEX IF NOT EXISTS idx_ledgers_tenant_parent 
ON ledgers(tenant_id, parent);

-- Ledgers: tenant + type (for type-filtered queries like "all customers")
CREATE INDEX IF NOT EXISTS idx_ledgers_tenant_type 
ON ledgers(tenant_id, ledger_type);

-- Ledgers: tenant + name (for search queries)
CREATE INDEX IF NOT EXISTS idx_ledgers_tenant_name 
ON ledgers(tenant_id, name);

-- Stock Items: tenant + name (for inventory queries)
CREATE INDEX IF NOT EXISTS idx_stock_items_tenant_name 
ON stock_items(tenant_id, name);

-- Stock Movements: tenant + item (for item-specific history)
CREATE INDEX IF NOT EXISTS idx_stock_movements_tenant_item 
ON stock_movements(tenant_id, item_id);

-- Pending Bills: tenant + party + status (for receivables/payables)
CREATE INDEX IF NOT EXISTS idx_pending_bills_tenant_party 
ON pending_bills(tenant_id, party_name);

-- Users: tenant_id (for tenant-based user queries)
CREATE INDEX IF NOT EXISTS idx_users_tenant 
ON users(tenant_id);

-- WhatsApp Customer Mappings: phone + active (for fast routing)
CREATE INDEX IF NOT EXISTS idx_wa_mappings_phone_active 
ON whatsapp_customer_mappings(customer_phone, is_active);

-- ============================================
-- SUPABASE (PostgreSQL) Indexes
-- Run these in Supabase SQL Editor
-- ============================================

-- Uncomment and run in Supabase:
/*
-- Tenants: WhatsApp number lookup
CREATE INDEX IF NOT EXISTS idx_tenants_whatsapp 
ON public.tenants(whatsapp_number) 
WHERE whatsapp_number IS NOT NULL;

-- User Profiles: tenant lookup
CREATE INDEX IF NOT EXISTS idx_user_profiles_tenant 
ON public.user_profiles(tenant_id);

-- Subscriptions: user + status
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status 
ON public.subscriptions(user_id, status);

-- Device Licenses: user + status
CREATE INDEX IF NOT EXISTS idx_device_licenses_user_status 
ON public.device_licenses(user_id, status);

-- WhatsApp Bindings: tenant + verified
CREATE INDEX IF NOT EXISTS idx_wa_bindings_tenant_verified 
ON public.whatsapp_bindings(tenant_id, verified);
*/

-- ============================================
-- Verification Query (SQLite)
-- ============================================
-- Check which indexes exist:
SELECT name, tbl_name FROM sqlite_master 
WHERE type = 'index' 
AND name LIKE 'idx_%'
ORDER BY tbl_name, name;
