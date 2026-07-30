-- Farmar / Oryx — Supabase (PostgreSQL) schema
-- Run in Supabase SQL Editor once per project.

-- Profiles (extends auth.users)
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  display_name text,
  username text unique,
  tier text not null default 'free' check (tier in ('free', 'premium')),
  role text not null default 'user' check (role in ('user', 'admin')),
  status text not null default 'active',
  ai_usage_total int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Farm profile synced from device
create table if not exists public.farm_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  farmer_name text,
  farm_name text,
  location text,
  herd_size int,
  livestock_type text,
  farm_size_ha numeric,
  land_tenure text,
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  unique (user_id)
);

-- Chat history (cloud)
create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles (id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  location text,
  agent text,
  mode text,
  tools_used jsonb,
  decision jsonb,
  created_at timestamptz not null default now()
);

create index if not exists chat_messages_user_created_idx
  on public.chat_messages (user_id, created_at desc);

-- Daily usage for freemium (e.g. 10 prompts/day)
create table if not exists public.usage_daily (
  user_id uuid not null references public.profiles (id) on delete cascade,
  usage_date date not null default (timezone('utc', now()))::date,
  prompt_count int not null default 0,
  primary key (user_id, usage_date)
);

-- Cached rangeland snippets synced from devices / backend
create table if not exists public.rangeland_cache (
  id uuid primary key default gen_random_uuid(),
  location_key text not null,
  payload jsonb not null,
  source text default 'dataset',
  updated_at timestamptz not null default now(),
  unique (location_key)
);

-- Device sync queue acknowledgements (optional audit)
create table if not exists public.sync_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles (id) on delete set null,
  device_id text,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, display_name, tier, role)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'name', split_part(new.email, '@', 1)),
    'free',
    'user'
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- RLS
alter table public.profiles enable row level security;
alter table public.farm_profiles enable row level security;
alter table public.chat_messages enable row level security;
alter table public.usage_daily enable row level security;
alter table public.rangeland_cache enable row level security;
alter table public.sync_events enable row level security;

create policy "Profiles are readable by owner"
  on public.profiles for select using (auth.uid() = id);
create policy "Profiles updatable by owner"
  on public.profiles for update using (auth.uid() = id);

create policy "Farm profiles by owner"
  on public.farm_profiles for all using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Chat by owner"
  on public.chat_messages for all using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Usage by owner"
  on public.usage_daily for all using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Rangeland cache readable by authenticated"
  on public.rangeland_cache for select to authenticated using (true);

create policy "Sync events by owner"
  on public.sync_events for insert with check (auth.uid() = user_id);
