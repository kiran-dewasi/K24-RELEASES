-- ============================================
-- TABLE 1: User Profiles (Extends auth.users)
-- ============================================
CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  tenant_id TEXT UNIQUE NOT NULL,
  full_name TEXT,
  phone TEXT,
  company_name TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast tenant lookup
CREATE INDEX IF NOT EXISTS idx_tenant_id ON user_profiles(tenant_id);

-- ============================================
-- TABLE 2: Subscriptions
-- ============================================
CREATE TABLE IF NOT EXISTS subscriptions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  tenant_id TEXT REFERENCES user_profiles(tenant_id),
  plan TEXT CHECK (plan IN ('free', 'pro', 'enterprise')) DEFAULT 'free',
  status TEXT CHECK (status IN ('active', 'trial', 'expired', 'cancelled')) DEFAULT 'trial',
  valid_from TIMESTAMP DEFAULT NOW(),
  valid_until TIMESTAMP,
  device_limit INTEGER DEFAULT 1,
  features_json JSONB DEFAULT '{}'::jsonb,
  payment_provider TEXT, -- 'razorpay', 'stripe', etc.
  payment_subscription_id TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_tenant ON subscriptions(tenant_id);

-- ============================================
-- TABLE 3: Device Licenses
-- ============================================
CREATE TABLE IF NOT EXISTS device_licenses (
  license_key TEXT PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  tenant_id TEXT REFERENCES user_profiles(tenant_id),
  device_fingerprint TEXT UNIQUE NOT NULL,
  device_name TEXT,
  os_version TEXT,
  app_version TEXT,
  status TEXT CHECK (status IN ('active', 'suspended', 'revoked')) DEFAULT 'active',
  activated_at TIMESTAMP DEFAULT NOW(),
  last_heartbeat TIMESTAMP DEFAULT NOW(),
  grace_period_until TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_licenses_user ON device_licenses(user_id);
CREATE INDEX IF NOT EXISTS idx_licenses_device ON device_licenses(device_fingerprint);

-- ============================================
-- TABLE 4: WhatsApp Bindings
-- ============================================
CREATE TABLE IF NOT EXISTS whatsapp_bindings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  tenant_id TEXT REFERENCES user_profiles(tenant_id),
  whatsapp_number TEXT NOT NULL,
  verified BOOLEAN DEFAULT FALSE,
  verification_code TEXT,
  code_expires_at TIMESTAMP,
  connected_at TIMESTAMP,
  session_status TEXT CHECK (session_status IN ('pending', 'connected', 'disconnected', 'expired')) DEFAULT 'pending',
  last_message_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_user ON whatsapp_bindings(user_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_number ON whatsapp_bindings(whatsapp_number);

-- ============================================
-- TABLE 5: WhatsApp Customer Mappings (Routing)
-- ============================================
CREATE TABLE IF NOT EXISTS whatsapp_customer_mappings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  tenant_id TEXT REFERENCES user_profiles(tenant_id),
  customer_phone TEXT NOT NULL,
  customer_name TEXT NOT NULL,
  client_code TEXT,
  notes TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customer_phone ON whatsapp_customer_mappings(customer_phone);
CREATE INDEX IF NOT EXISTS idx_customer_tenant ON whatsapp_customer_mappings(tenant_id);

-- Row-level security: Users can only see their own mappings
ALTER TABLE whatsapp_customer_mappings ENABLE ROW LEVEL SECURITY;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_policies 
        WHERE tablename = 'whatsapp_customer_mappings' 
        AND policyname = 'Users can manage their own customer mappings'
    ) THEN
        CREATE POLICY "Users can manage their own customer mappings"
          ON whatsapp_customer_mappings
          FOR ALL
          USING (auth.uid() = user_id);
    END IF;
END $$;

-- ============================================
-- TABLE 6: Sync Checkpoints (Backups)
-- ============================================
CREATE TABLE IF NOT EXISTS sync_checkpoints (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  tenant_id TEXT REFERENCES user_profiles(tenant_id),
  device_fingerprint TEXT,
  backup_size_bytes BIGINT,
  backup_url TEXT, -- Supabase Storage URL
  encryption_key_hash TEXT,
  status TEXT CHECK (status IN ('pending', 'completed', 'failed')) DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_user ON sync_checkpoints(user_id);

-- ============================================
-- FUNCTIONS: Auto-generate Tenant ID on User Creation
-- ============================================
CREATE OR REPLACE FUNCTION generate_tenant_id()
RETURNS TRIGGER AS $$
BEGIN
  NEW.tenant_id := 'TENANT-' || UPPER(SUBSTRING(MD5(NEW.id::TEXT || NOW()::TEXT) FROM 1 FOR 8));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_generate_tenant_id ON user_profiles;
CREATE TRIGGER trigger_generate_tenant_id
BEFORE INSERT ON user_profiles
FOR EACH ROW
EXECUTE FUNCTION generate_tenant_id();
