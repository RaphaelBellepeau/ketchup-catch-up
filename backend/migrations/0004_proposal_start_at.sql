-- 0004_proposal_start_at.sql
-- Adds a structured datetime + duration to proposals so we can push the
-- accepted catch-up to each member's Google Calendar without parsing the
-- LLM's free-form "Thursday 8pm" label.
--
-- Run in Supabase SQL Editor.

alter table public.proposals
  add column if not exists start_at timestamptz,
  add column if not exists duration_minutes int default 120;
