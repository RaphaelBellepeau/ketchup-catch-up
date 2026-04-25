"""Catchups CRUD + negotiation / voting / finalize routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from src.deps import get_current_user_id
from src.models.schemas import CreateCatchupRequest, VoteRequest
from src.services import supabase_client as db

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
    user_id: str = Depends(get_current_user_id),
):
    """Launch A2A negotiation between agents."""
    catchup = await db.get_catchup(catchup_id)
    if not catchup:
        raise HTTPException(status_code=404, detail="Catchup not found")

    negotiation = await db.create_negotiation(catchup_id)
    await db.update_catchup_status(catchup_id, "negotiating")

    # TODO: spawn agent negotiation loop in background task
    logger.info("Negotiation %s started for catchup %s", negotiation["id"], catchup_id)
    return negotiation


@router.get("/{catchup_id}/negotiate/stream")
async def negotiate_stream(catchup_id: str):
    """SSE stream of agent dialogue messages — CRITICAL for demo."""
    async def event_generator():
        messages = await db.get_negotiation_messages(catchup_id)
        for msg in messages:
            yield {"data": msg}

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
    """Push event to Google Calendars of all members."""
    await db.update_catchup_status(catchup_id, "done")
    # TODO: push to Google Calendar via gcal_client
    return {"status": "finalized", "catchup_id": catchup_id}
