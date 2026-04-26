"""Supabase client for database operations."""

import logging

from postgrest.exceptions import APIError

from src.config import settings

logger = logging.getLogger(__name__)

_client = None


def get_client():
    """Get or create the Supabase client singleton."""
    global _client
    if _client is None:
        from supabase import create_client

        _client = create_client(settings.supabase_url, settings.supabase_service_key)
        logger.info("Supabase client initialized")
    return _client


def _maybe_single(query):
    """Execute a maybe_single query, returning dict | None safely."""
    result = query.maybe_single().execute()
    if result is None:
        return None
    return result.data


# ── Users ───────────────────────────────────────────────

async def get_user(user_id: str) -> dict | None:
    client = get_client()
    return _maybe_single(client.table("users").select("*").eq("id", user_id))


async def find_users_by_phones(phones: list[str]) -> list[dict]:
    client = get_client()
    result = client.table("users").select("id, name, phone").in_("phone", phones).execute()
    return result.data or []


async def list_other_users(user_id: str) -> list[dict]:
    """Every user except the caller. Hackathon stand-in for contact sync."""
    client = get_client()
    result = (
        client.table("users")
        .select("id, name, phone")
        .neq("id", user_id)
        .order("name")
        .execute()
    )
    return result.data or []


async def update_user(user_id: str, data: dict) -> dict | None:
    """Update writable fields on a user row. Silently drops unknown keys."""
    allowed = {k: v for k, v in data.items() if k in ("name",)}
    if not allowed:
        return await get_user(user_id)
    client = get_client()
    result = (
        client.table("users").update(allowed).eq("id", user_id).execute()
    )
    return result.data[0] if result.data else None


async def mark_user_onboarded(user_id: str) -> dict | None:
    """Set users.onboarded_at = now() for the given user.

    Idempotent — calling twice just refreshes the timestamp, which is fine.
    """
    client = get_client()
    result = (
        client.table("users")
        .update({"onboarded_at": "now()"})
        .eq("id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


# ── Google OAuth tokens ────────────────────────────────

async def get_calendar_tokens(user_id: str) -> dict | None:
    client = get_client()
    return _maybe_single(
        client.table("google_oauth_tokens").select("*").eq("user_id", user_id)
    )


async def save_calendar_tokens(
    user_id: str,
    access_token: str,
    refresh_token: str,
    expires_at: str,
    scopes: list[str],
) -> dict | None:
    client = get_client()
    payload = {
        "user_id": user_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "scopes": scopes,
        "updated_at": "now()",
    }
    result = (
        client.table("google_oauth_tokens")
        .upsert(payload, on_conflict="user_id")
        .execute()
    )
    return result.data[0] if result.data else None


async def update_calendar_access_token(
    user_id: str, access_token: str, expires_at: str,
) -> dict | None:
    client = get_client()
    result = (
        client.table("google_oauth_tokens")
        .update({
            "access_token": access_token,
            "expires_at": expires_at,
            "updated_at": "now()",
        })
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


async def delete_calendar_tokens(user_id: str) -> None:
    client = get_client()
    client.table("google_oauth_tokens").delete().eq("user_id", user_id).execute()


# ── Friends ─────────────────────────────────────────────

async def get_friends(user_id: str) -> list[dict]:
    client = get_client()
    result = client.table("friends").select("*").eq("user_id", user_id).execute()
    return result.data or []


async def add_friend(user_id: str, phone: str, name: str) -> dict:
    client = get_client()

    existing_user = _maybe_single(
        client.table("users").select("id").eq("phone", phone)
    )
    is_on_app = existing_user is not None
    friend_id = existing_user["id"] if existing_user else None

    data = {
        "user_id": user_id,
        "phone": phone,
        "name": name,
        "is_on_app": is_on_app,
        "friend_id": friend_id,
    }
    result = client.table("friends").insert(data).execute()
    return result.data[0] if result.data else {}


async def delete_friend(user_id: str, friend_id: str) -> bool:
    client = get_client()
    result = (
        client.table("friends")
        .delete()
        .eq("id", friend_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(result.data)


# ── Groups ──────────────────────────────────────────────

async def get_user_groups(user_id: str) -> list[dict]:
    """List groups the user belongs to, enriched with member_count and the
    timestamp of the most recent catchup activity (used by the Home page
    to show an Active/Idle pill).
    """
    client = get_client()
    memberships = (
        client.table("group_members")
        .select("group_id")
        .eq("user_id", user_id)
        .execute()
    )
    group_ids = [m["group_id"] for m in (memberships.data or [])]
    if not group_ids:
        return []
    groups = client.table("groups").select("*").in_("id", group_ids).execute().data or []
    if not groups:
        return []

    members = (
        client.table("group_members")
        .select("group_id, user_id")
        .in_("group_id", group_ids)
        .execute()
        .data
        or []
    )
    counts: dict[str, int] = {}
    for m in members:
        counts[m["group_id"]] = counts.get(m["group_id"], 0) + 1

    catchups = (
        client.table("catchups")
        .select("group_id, status, created_at")
        .in_("group_id", group_ids)
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )
    last_activity: dict[str, str] = {}
    has_open: dict[str, bool] = {}
    for c in catchups:
        gid = c["group_id"]
        if gid not in last_activity:
            last_activity[gid] = c["created_at"]
        if c["status"] not in ("done", "cancelled") and gid not in has_open:
            has_open[gid] = True

    for g in groups:
        g["member_count"] = counts.get(g["id"], 0)
        g["last_activity_at"] = last_activity.get(g["id"])
        g["has_open_catchup"] = has_open.get(g["id"], False)

    return groups


async def create_group(created_by: str, name: str, member_ids: list[str]) -> dict:
    client = get_client()
    result = client.table("groups").insert({"name": name, "created_by": created_by}).execute()
    group = result.data[0]

    all_members = list(set([created_by] + member_ids))
    rows = [{"group_id": group["id"], "user_id": uid} for uid in all_members]
    client.table("group_members").insert(rows).execute()

    group["members"] = all_members
    return group


async def get_group(group_id: str) -> dict | None:
    client = get_client()
    group = _maybe_single(client.table("groups").select("*").eq("id", group_id))
    if not group:
        return None
    members = (
        client.table("group_members")
        .select("user_id")
        .eq("group_id", group_id)
        .execute()
    )
    group["members"] = [m["user_id"] for m in (members.data or [])]
    return group


async def get_group_members(group_id: str) -> list[dict]:
    client = get_client()
    result = (
        client.table("group_members")
        .select("user_id, users(id, name, phone)")
        .eq("group_id", group_id)
        .execute()
    )
    return result.data or []


async def update_group(group_id: str, data: dict) -> dict | None:
    client = get_client()
    allowed = {k: v for k, v in data.items() if k in ("name",)}
    if not allowed:
        return await get_group(group_id)
    result = client.table("groups").update(allowed).eq("id", group_id).execute()
    return result.data[0] if result.data else None


async def delete_group(group_id: str) -> None:
    client = get_client()
    client.table("group_members").delete().eq("group_id", group_id).execute()
    client.table("groups").delete().eq("id", group_id).execute()


# ── Catchups ────────────────────────────────────────────

async def get_user_catchups(
    user_id: str, status: str = "", group_id: str = ""
) -> list[dict]:
    """List catchups visible to a user, enriched with the parent group's
    name and the most recent proposal (if any) — so the Home screen can
    render upcoming items in one round-trip.

    Status filter accepts either a single value (`?status=proposed`) or a
    comma-separated list (`?status=proposed,accepted`).
    """
    client = get_client()
    group_ids_result = (
        client.table("group_members")
        .select("group_id")
        .eq("user_id", user_id)
        .execute()
    )
    group_ids = [m["group_id"] for m in (group_ids_result.data or [])]
    if not group_ids:
        return []

    query = client.table("catchups").select("*").in_("group_id", group_ids)
    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        if len(statuses) == 1:
            query = query.eq("status", statuses[0])
        else:
            query = query.in_("status", statuses)
    if group_id:
        query = query.eq("group_id", group_id)
    query = query.order("created_at", desc=True)
    catchups = query.execute().data or []
    if not catchups:
        return []

    # Bulk-load related groups and proposals so we don't N+1.
    needed_group_ids = list({c["group_id"] for c in catchups})
    catchup_ids = [c["id"] for c in catchups]

    groups_data = (
        client.table("groups")
        .select("id, name")
        .in_("id", needed_group_ids)
        .execute()
        .data
        or []
    )
    groups_by_id = {g["id"]: g for g in groups_data}

    proposals_data = (
        client.table("proposals")
        .select("*")
        .in_("catchup_id", catchup_ids)
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )
    latest_proposal: dict[str, dict] = {}
    for p in proposals_data:
        cid = p["catchup_id"]
        if cid not in latest_proposal:
            latest_proposal[cid] = p

    # "Has the caller debriefed yet?" — used by the Home page to surface
    # pending feedback prompts on past events.
    feedbacks_data = (
        client.table("feedbacks")
        .select("catchup_id")
        .eq("user_id", user_id)
        .in_("catchup_id", catchup_ids)
        .execute()
        .data
        or []
    )
    feedback_catchup_ids = {f["catchup_id"] for f in feedbacks_data}

    for c in catchups:
        c["group"] = groups_by_id.get(c["group_id"])
        c["proposal"] = latest_proposal.get(c["id"])
        c["has_my_feedback"] = c["id"] in feedback_catchup_ids

    return catchups


async def create_catchup(data: dict) -> dict:
    client = get_client()
    result = client.table("catchups").insert(data).execute()
    return result.data[0] if result.data else {}


async def get_catchup(catchup_id: str) -> dict | None:
    client = get_client()
    return _maybe_single(client.table("catchups").select("*").eq("id", catchup_id))


async def update_catchup(catchup_id: str, data: dict) -> dict | None:
    client = get_client()
    allowed = {k: v for k, v in data.items() if k in ("status", "time_window", "vibe")}
    if not allowed:
        return await get_catchup(catchup_id)
    result = client.table("catchups").update(allowed).eq("id", catchup_id).execute()
    return result.data[0] if result.data else None


async def update_catchup_status(catchup_id: str, status: str) -> None:
    client = get_client()
    client.table("catchups").update({"status": status}).eq("id", catchup_id).execute()


async def delete_catchup(catchup_id: str) -> None:
    client = get_client()
    client.table("catchups").delete().eq("id", catchup_id).execute()


# ── Negotiations ───────────────────────────────────────

async def create_negotiation(catchup_id: str) -> dict:
    client = get_client()
    result = (
        client.table("negotiations")
        .insert({"catchup_id": catchup_id, "status": "active"})
        .execute()
    )
    return result.data[0] if result.data else {}


async def get_latest_negotiation(catchup_id: str) -> dict | None:
    """Return the most recent negotiation row for a catchup."""
    client = get_client()
    return _maybe_single(
        client.table("negotiations")
        .select("*")
        .eq("catchup_id", catchup_id)
        .order("started_at", desc=True)
        .limit(1)
    )


async def get_negotiation_messages(catchup_id: str) -> list[dict]:
    client = get_client()
    neg = _maybe_single(
        client.table("negotiations")
        .select("id")
        .eq("catchup_id", catchup_id)
        .order("started_at", desc=True)
        .limit(1)
    )
    if not neg:
        return []
    result = (
        client.table("negotiation_messages")
        .select("*")
        .eq("negotiation_id", neg["id"])
        .order("timestamp", desc=False)
        .execute()
    )
    return result.data or []


async def save_negotiation_message(negotiation_id: str, message: dict) -> None:
    client = get_client()
    data = {"negotiation_id": negotiation_id, **message}
    client.table("negotiation_messages").insert(data).execute()


# ── Proposals ──────────────────────────────────────────

async def get_proposal(catchup_id: str) -> dict | None:
    client = get_client()
    return _maybe_single(
        client.table("proposals")
        .select("*")
        .eq("catchup_id", catchup_id)
        .order("created_at", desc=True)
        .limit(1)
    )


async def save_proposal(catchup_id: str, proposal: dict) -> dict:
    client = get_client()
    data = {"catchup_id": catchup_id, **proposal}
    result = client.table("proposals").insert(data).execute()
    return result.data[0] if result.data else {}


# ── Votes ──────────────────────────────────────────────

async def save_vote(catchup_id: str, user_id: str, vote: str, reason: str) -> dict:
    client = get_client()
    data = {
        "catchup_id": catchup_id,
        "user_id": user_id,
        "vote": vote,
        "reason": reason,
    }
    result = client.table("votes").upsert(data, on_conflict="catchup_id,user_id").execute()
    return result.data[0] if result.data else {}


async def get_votes(catchup_id: str) -> list[dict]:
    client = get_client()
    result = (
        client.table("votes")
        .select("*")
        .eq("catchup_id", catchup_id)
        .execute()
    )
    return result.data or []


async def clear_votes(catchup_id: str) -> None:
    """Wipe all votes for a catchup — called when we kick off a new
    negotiation round so stale accepts from the prior proposal don't
    auto-confirm the next one.
    """
    client = get_client()
    client.table("votes").delete().eq("catchup_id", catchup_id).execute()


# ── Memories ───────────────────────────────────────────

async def get_memories(user_id: str, scope: str = "") -> list[dict]:
    client = get_client()
    query = client.table("memories").select("*").eq("user_id", user_id)
    if scope:
        query = query.eq("scope", scope)
    result = query.order("created_at", desc=True).execute()
    return result.data or []


async def create_memory(user_id: str, content: str, scope: str = "general", source: str = "onboarding") -> dict:
    client = get_client()
    data = {"user_id": user_id, "content": content, "scope": scope, "source": source}
    result = client.table("memories").insert(data).execute()
    return result.data[0] if result.data else {}


async def update_memory(memory_id: str, data: dict) -> dict | None:
    client = get_client()
    allowed = {k: v for k, v in data.items() if k in ("content", "scope")}
    if not allowed:
        return None
    result = client.table("memories").update(allowed).eq("id", memory_id).execute()
    return result.data[0] if result.data else None


async def delete_memory(memory_id: str) -> None:
    client = get_client()
    client.table("memories").delete().eq("id", memory_id).execute()


# ── Feedbacks ──────────────────────────────────────────

async def save_feedback(data: dict) -> dict:
    client = get_client()
    result = client.table("feedbacks").insert(data).execute()
    return result.data[0] if result.data else {}


async def get_feedbacks(user_id: str, catchup_id: str = "") -> list[dict]:
    client = get_client()
    query = client.table("feedbacks").select("*").eq("user_id", user_id)
    if catchup_id:
        query = query.eq("catchup_id", catchup_id)
    result = query.order("created_at", desc=True).execute()
    return result.data or []
