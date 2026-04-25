-- Catch-Up — Full schema migration
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)

-- ══════════════════════════════════════════════════════════
-- 1. Users (extends Supabase auth.users)
-- ══════════════════════════════════════════════════════════

create table public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  phone text unique not null,
  name text not null default '',
  created_at timestamptz not null default now()
);

alter table public.users enable row level security;

create policy "Users can read own profile"
  on public.users for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.users for update
  using (auth.uid() = id);

-- Auto-create a public.users row when someone signs up via Supabase Auth
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.users (id, phone)
  values (new.id, coalesce(new.phone, ''))
  on conflict (id) do nothing;
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ══════════════════════════════════════════════════════════
-- 2. Preferences
-- ══════════════════════════════════════════════════════════

create table public.preferences (
  id uuid primary key default gen_random_uuid(),
  user_id uuid unique not null references public.users(id) on delete cascade,
  cuisines_liked text[] default '{}',
  cuisines_disliked text[] default '{}',
  budget text default 'medium',
  areas text[] default '{}',
  days text[] default '{}',
  dietary text[] default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.preferences enable row level security;

create policy "Users can read own preferences"
  on public.preferences for select
  using (auth.uid() = user_id);

create policy "Users can upsert own preferences"
  on public.preferences for all
  using (auth.uid() = user_id);

-- ══════════════════════════════════════════════════════════
-- 3. Friends
-- ══════════════════════════════════════════════════════════

create table public.friends (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  friend_id uuid references public.users(id) on delete set null,
  name text not null,
  phone text not null,
  is_on_app boolean default false,
  created_at timestamptz not null default now()
);

create unique index friends_user_phone_idx on public.friends(user_id, phone);

alter table public.friends enable row level security;

create policy "Users can manage own friends"
  on public.friends for all
  using (auth.uid() = user_id);

-- ══════════════════════════════════════════════════════════
-- 4. Groups
-- ══════════════════════════════════════════════════════════

create table public.groups (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_by uuid not null references public.users(id) on delete cascade,
  created_at timestamptz not null default now()
);

alter table public.groups enable row level security;

create table public.group_members (
  group_id uuid not null references public.groups(id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  joined_at timestamptz not null default now(),
  primary key (group_id, user_id)
);

alter table public.group_members enable row level security;

create policy "Members can read own groups"
  on public.groups for select
  using (
    id in (select group_id from public.group_members where user_id = auth.uid())
  );

create policy "Anyone can create groups"
  on public.groups for insert
  with check (auth.uid() = created_by);

create policy "Creator can update group"
  on public.groups for update
  using (auth.uid() = created_by);

create policy "Creator can delete group"
  on public.groups for delete
  using (auth.uid() = created_by);

create policy "Members can read group_members"
  on public.group_members for select
  using (
    group_id in (select group_id from public.group_members where user_id = auth.uid())
  );

create policy "Group creator can manage members"
  on public.group_members for all
  using (
    group_id in (select id from public.groups where created_by = auth.uid())
  );

-- ══════════════════════════════════════════════════════════
-- 5. Catchups
-- ══════════════════════════════════════════════════════════

create table public.catchups (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references public.groups(id) on delete cascade,
  created_by uuid not null references public.users(id),
  type text not null default 'one_shot',
  status text not null default 'pending',
  time_window text default 'next 2 weeks',
  vibe text default '',
  created_at timestamptz not null default now()
);

alter table public.catchups enable row level security;

create policy "Group members can read catchups"
  on public.catchups for select
  using (
    group_id in (select group_id from public.group_members where user_id = auth.uid())
  );

create policy "Group members can create catchups"
  on public.catchups for insert
  with check (
    group_id in (select group_id from public.group_members where user_id = auth.uid())
  );

create policy "Creator can update catchup"
  on public.catchups for update
  using (auth.uid() = created_by);

create policy "Creator can delete catchup"
  on public.catchups for delete
  using (auth.uid() = created_by);

-- ══════════════════════════════════════════════════════════
-- 6. Negotiations
-- ══════════════════════════════════════════════════════════

create table public.negotiations (
  id uuid primary key default gen_random_uuid(),
  catchup_id uuid not null references public.catchups(id) on delete cascade,
  status text not null default 'active',
  started_at timestamptz not null default now(),
  ended_at timestamptz
);

alter table public.negotiations enable row level security;

create policy "Readable by group members"
  on public.negotiations for select
  using (
    catchup_id in (
      select c.id from public.catchups c
      join public.group_members gm on gm.group_id = c.group_id
      where gm.user_id = auth.uid()
    )
  );

-- ══════════════════════════════════════════════════════════
-- 7. Negotiation messages (agent dialogue log)
-- ══════════════════════════════════════════════════════════

create table public.negotiation_messages (
  id uuid primary key default gen_random_uuid(),
  negotiation_id uuid not null references public.negotiations(id) on delete cascade,
  agent_name text not null,
  role text not null,
  content text not null,
  data jsonb default '{}',
  timestamp timestamptz not null default now()
);

create index neg_msg_negotiation_idx on public.negotiation_messages(negotiation_id, timestamp);

alter table public.negotiation_messages enable row level security;

create policy "Readable by group members"
  on public.negotiation_messages for select
  using (
    negotiation_id in (
      select n.id from public.negotiations n
      join public.catchups c on c.id = n.catchup_id
      join public.group_members gm on gm.group_id = c.group_id
      where gm.user_id = auth.uid()
    )
  );

-- ══════════════════════════════════════════════════════════
-- 8. Proposals
-- ══════════════════════════════════════════════════════════

create table public.proposals (
  id uuid primary key default gen_random_uuid(),
  catchup_id uuid not null references public.catchups(id) on delete cascade,
  venue text not null,
  time text not null,
  activity text default '',
  justification text default '',
  created_at timestamptz not null default now()
);

alter table public.proposals enable row level security;

create policy "Readable by group members"
  on public.proposals for select
  using (
    catchup_id in (
      select c.id from public.catchups c
      join public.group_members gm on gm.group_id = c.group_id
      where gm.user_id = auth.uid()
    )
  );

-- ══════════════════════════════════════════════════════════
-- 9. Votes
-- ══════════════════════════════════════════════════════════

create table public.votes (
  id uuid primary key default gen_random_uuid(),
  catchup_id uuid not null references public.catchups(id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  vote text not null,
  reason text default '',
  created_at timestamptz not null default now(),
  unique (catchup_id, user_id)
);

alter table public.votes enable row level security;

create policy "Users can manage own votes"
  on public.votes for all
  using (auth.uid() = user_id);

create policy "Group members can read votes"
  on public.votes for select
  using (
    catchup_id in (
      select c.id from public.catchups c
      join public.group_members gm on gm.group_id = c.group_id
      where gm.user_id = auth.uid()
    )
  );

-- ══════════════════════════════════════════════════════════
-- 10. Feedbacks
-- ══════════════════════════════════════════════════════════

create table public.feedbacks (
  id uuid primary key default gen_random_uuid(),
  catchup_id uuid not null references public.catchups(id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  rating int not null check (rating between 1 and 5),
  tags text[] default '{}',
  liked text[] default '{}',
  disliked text[] default '{}',
  comment text default '',
  created_at timestamptz not null default now()
);

alter table public.feedbacks enable row level security;

create policy "Users can manage own feedbacks"
  on public.feedbacks for all
  using (auth.uid() = user_id);

-- ══════════════════════════════════════════════════════════
-- 11. Memories (agent knowledge per user)
-- ══════════════════════════════════════════════════════════

create table public.memories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  scope text not null default 'general',
  content text not null,
  source text not null default 'onboarding',
  created_at timestamptz not null default now()
);

create index memories_user_scope_idx on public.memories(user_id, scope);

alter table public.memories enable row level security;

create policy "Users can manage own memories"
  on public.memories for all
  using (auth.uid() = user_id);

-- ══════════════════════════════════════════════════════════
-- 12. Enable Realtime on key tables
-- ══════════════════════════════════════════════════════════

alter publication supabase_realtime add table public.catchups;
alter publication supabase_realtime add table public.proposals;
alter publication supabase_realtime add table public.negotiation_messages;
alter publication supabase_realtime add table public.memories;

-- ══════════════════════════════════════════════════════════
-- 13. Service role bypass (backend uses service key)
-- ══════════════════════════════════════════════════════════
-- The backend uses the service_role key which bypasses RLS.
-- RLS policies above protect direct client access (Lovable frontend via anon key).
