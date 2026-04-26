"""Catchups CRUD + negotiation / voting / finalize routes."""

import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from src.deps import get_current_user_id
from src.models.schemas import CreateCatchupRequest, VoteRequest
from src.services import supabase_client as db
from src.agents.fake_preferences import get_user_preferences

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catchups", tags=["catchups"])


# ── CRUD ───────────────────────────────────────────────

@router.get("")
async def list_catchups(
    status: str = "",
    group_id: str = "",
    user_id: str = Depends(get_current_user_id),
):
    return await db.get_user_catchups(user_id, status=status, group_id=group_id)


@router.post("", status_code=201)
async def create_catchup(
    body: CreateCatchupRequest,
    user_id: str = Depends(get_current_user_id),
):
    data = body.model_dump(exclude_none=True)
    data["created_by"] = user_id
    catchup = await db.create_catchup(data)
    return catchup


@router.get("/{catchup_id}")
async def get_catchup(catchup_id: str):
    catchup = await db.get_catchup(catchup_id)
    if not catchup:
        raise HTTPException(status_code=404, detail="Catchup not found")
    return catchup


@router.patch("/{catchup_id}")
async def update_catchup(catchup_id: str, body: dict):
    updated = await db.update_catchup(catchup_id, body)
    if not updated:
        raise HTTPException(status_code=404, detail="Catchup not found")
    return updated


@router.delete("/{catchup_id}", status_code=204)
async def delete_catchup(catchup_id: str):
    await db.delete_catchup(catchup_id)


# ── Negotiation ────────────────────────────────────────

@router.post("/{catchup_id}/negotiate")
async def start_negotiation(
    catchup_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
):
    """Launch A2A negotiation between agents (non-blocking).

    Returns immediately with negotiation metadata.
    The actual pipeline runs in a background task and streams via SSE.
    """
    # Fetch catchup
    catchup = await db.get_catchup(catchup_id)
    if not catchup:
        raise HTTPException(status_code=404, detail="Catchup not found")

    # Fetch group members with user details
    raw_members = await db.get_group_members(catchup["group_id"])
    if not raw_members:
        raise HTTPException(status_code=400, detail="Group has no members")

    # Build member list with preferences
    members = []
    for m in raw_members:
        user_data = m.get("users") or {}
        uid = m.get("user_id", "")
        members.append({
            "user_id": uid,
            "name": user_data.get("name") or f"User_{uid[:6]}",
            "preferences": get_user_preferences(uid),
            "history": [],
        })

    # Build catchup context
    catchup_context = {
        "vibe": catchup.get("vibe", "dîner"),
        "time_window": catchup.get("time_window", "next 2 weeks"),
        "location": "Paris",
        "group_members": [m["name"] for m in members],
    }

    # Create negotiation row in DB
    negotiation = await db.create_negotiation(catchup_id)
    await db.update_catchup_status(catchup_id, "negotiating")

    # Import here to avoid circular imports at module level
    from src.agents.negotiation import run_negotiation

    # Spawn negotiation pipeline as a background task
    # The SSE stream will receive all messages via the in-memory queue
    background_tasks.add_task(
        run_negotiation,
        negotiation_id=negotiation["id"],
        catchup_id=catchup_id,
        members=members,
        catchup_context=catchup_context,
    )

    logger.info(
        "Negotiation %s started for catchup %s (%d members)",
        negotiation["id"], catchup_id, len(members),
    )
    return {
        "negotiation_id": negotiation["id"],
        "catchup_id": catchup_id,
        "status": "started",
        "members": [m["name"] for m in members],
    }


@router.get("/{catchup_id}/negotiate/stream")
async def negotiate_stream(catchup_id: str):
    """SSE stream of agent dialogue messages — CRITICAL for demo.

    Reads from the in-memory asyncio.Queue populated by run_negotiation().
    Sends a keepalive comment every 25s to prevent proxy timeouts.
    Stops and cleans up the queue when it receives the 'done' message.
    """
    from src.agents.negotiation import get_or_create_stream, cleanup_stream

    async def event_generator():
        queue = get_or_create_stream(catchup_id)
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=25.0)
                    # Serialize NegotiationMessage to JSON string
                    yield {"data": msg.model_dump_json()}
                    if msg.role == "done":
                        break
                except asyncio.TimeoutError:
                    # SSE keepalive — prevents proxy/browser from closing connection
                    yield {"comment": "keepalive"}
        finally:
            cleanup_stream(catchup_id)

    return EventSourceResponse(event_generator())


# ── Proposal & Voting ──────────────────────────────────

@router.get("/{catchup_id}/proposal")
async def get_proposal(catchup_id: str):
    proposal = await db.get_proposal(catchup_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="No proposal yet")
    return proposal


@router.post("/{catchup_id}/vote")
async def vote_on_proposal(
    catchup_id: str,
    body: VoteRequest,
    user_id: str = Depends(get_current_user_id),
):
    vote = await db.save_vote(catchup_id, user_id, body.vote, body.reason)
    return vote


@router.post("/{catchup_id}/finalize")
async def finalize_catchup(
    catchup_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Mark catchup as done and push to Google Calendar (TODO: real GCal)."""
    await db.update_catchup_status(catchup_id, "done")
    # TODO: push to Google Calendar via gcal_client.create_event()
    return {"status": "finalized", "catchup_id": catchup_id}
