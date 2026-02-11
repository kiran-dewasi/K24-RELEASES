-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- 1. Users Profile Table
create table public.users_profile (
  id uuid references auth.users on delete cascade not null primary key,
  full_name text,
  whatsapp_number text unique,
  avatar_url text,
  role text default 'owner',
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS for users_profile
alter table public.users_profile enable row level security;

create policy "Users can view their own profile"
  on public.users_profile for select
  using ( auth.uid() = id );

create policy "Users can update their own profile"
  on public.users_profile for update
  using ( auth.uid() = id );

-- 2. Business Profile Table
create table public.business_profile (
  id uuid default uuid_generate_v4() primary key,
  owner_id uuid references public.users_profile(id) on delete cascade not null,
  company_name text,
  gstin text,
  address text,
  tally_license_key text, -- In production, ensure this is handled securely (e.g. Vault) or RLS restricted
  preferences jsonb default '{"auto_sync": false, "notify_whatsapp": false}'::jsonb,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS for business_profile
alter table public.business_profile enable row level security;

create policy "Users can view their own business profile"
  on public.business_profile for select
  using ( auth.uid() = owner_id );

create policy "Users can update their own business profile"
  on public.business_profile for update
  using ( auth.uid() = owner_id );

create policy "Users can insert their own business profile"
  on public.business_profile for insert
  with check ( auth.uid() = owner_id );

-- 3. Contacts Table (Mini-CRM)
create table public.contacts (
  id uuid default uuid_generate_v4() primary key,
  business_id uuid references public.business_profile(id) on delete cascade not null,
  name text not null,
  phone text,
  type text check (type in ('Sundry Debtor', 'Sundry Creditor')),
  current_balance decimal default 0.0,
  tally_ledger_name text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS for contacts
alter table public.contacts enable row level security;

-- Helper function to check if user owns the business for the contact
create or replace function public.is_business_owner(business_id uuid)
returns boolean as $$
begin
  return exists (
    select 1 from public.business_profile
    where id = business_id
    and owner_id = auth.uid()
  );
end;
$$ language plpgsql security definer;

create policy "Users can view contacts of their business"
  on public.contacts for select
  using ( is_business_owner(business_id) );

create policy "Users can insert contacts for their business"
  on public.contacts for insert
  with check ( is_business_owner(business_id) );

create policy "Users can update contacts of their business"
  on public.contacts for update
  using ( is_business_owner(business_id) );

create policy "Users can delete contacts of their business"
  on public.contacts for delete
  using ( is_business_owner(business_id) );
