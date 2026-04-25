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
    result = client.table("groups").select("*").in_("id", group_ids).execute()
    return result.data or []


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
        query = query.eq("status", status)
    if group_id:
        query = query.eq("group_id", group_id)
    query = query.order("created_at", desc=True)
    result = query.execute()
    return result.data or []


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
