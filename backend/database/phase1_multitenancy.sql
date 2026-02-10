-- 1. Create Tenants Table with VARCHAR id
CREATE TABLE IF NOT EXISTS public.tenants (
  id VARCHAR(50) DEFAULT gen_random_uuid()::text PRIMARY KEY,
  name text NOT NULL,
  subscription_plan text DEFAULT 'free',
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;

-- 2. Add tenant_id to users_profile
ALTER TABLE public.users_profile 
ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) REFERENCES public.tenants(id);

-- 3. Sync to JWT
CREATE OR REPLACE FUNCTION public.sync_tenant_to_auth_metadata()
RETURNS trigger AS $$
BEGIN
  UPDATE auth.users
  SET raw_app_meta_data = 
    coalesce(raw_app_meta_data, '{}'::jsonb) || 
    jsonb_build_object('tenant_id', NEW.tenant_id)
  WHERE id = NEW.id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_user_tenant_change ON public.users_profile;
CREATE TRIGGER on_user_tenant_change
AFTER INSERT OR UPDATE OF tenant_id ON public.users_profile
FOR EACH ROW EXECUTE FUNCTION public.sync_tenant_to_auth_metadata();

-- 4. Helper function
CREATE OR REPLACE FUNCTION public.get_current_tenant_id()
RETURNS text AS $$
BEGIN
  RETURN (auth.jwt() -> 'app_metadata' ->> 'tenant_id');
END;
$$ LANGUAGE plpgsql STABLE;

-- 5. Add to feature tables
DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['vouchers', 'stock_items', 'whatsapp_logs']
  LOOP
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = t) THEN
      IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_schema = 'public' AND table_name = t AND column_name = 'tenant_id') THEN
        EXECUTE format('ALTER TABLE public.%I ADD COLUMN tenant_id VARCHAR(50) REFERENCES public.tenants(id)', t);
      END IF;
      EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
      BEGIN
        EXECUTE format('DROP POLICY IF EXISTS "Tenant Isolation Policy" ON public.%I', t);
      EXCEPTION WHEN OTHERS THEN NULL; END;
      EXECUTE format('
        CREATE POLICY "Tenant Isolation Policy" ON public.%I
        USING (tenant_id = public.get_current_tenant_id())
        WITH CHECK (tenant_id = public.get_current_tenant_id())
      ', t);
    END IF;
  END LOOP;
END;
$$;
