-- 0002_add_onboarded_at.sql
-- Adds an onboarded_at timestamp to public.users so the frontend can gate
-- post-onboarding screens (permissions, home, groups...) until the user has
-- completed the voice onboarding.
--
-- Run in Supabase SQL Editor.

alter table public.users
  add column if not exists onboarded_at timestamptz;

-- Optional convenience: index for "find users still mid-onboarding" queries.
create index if not exists users_onboarded_idx on public.users(onboarded_at);
