-- 0003_google_oauth_tokens.sql
-- Stores per-user Google OAuth tokens so the backend can call Google
-- Calendar on the user's behalf during agent negotiations.
--
-- Run in Supabase SQL Editor.

create table if not exists public.google_oauth_tokens (
  user_id uuid primary key references public.users(id) on delete cascade,
  access_token text not null,
  refresh_token text not null,
  expires_at timestamptz not null,
  scopes text[] not null default '{}',
  updated_at timestamptz not null default now()
);

alter table public.google_oauth_tokens enable row level security;

-- Backend uses the service role key which bypasses RLS, so user-facing
-- policies just keep the row visible to its owner if a Supabase client
-- ever queries it directly.
create policy "Users can read own google tokens"
  on public.google_oauth_tokens for select
  using (auth.uid() = user_id);
