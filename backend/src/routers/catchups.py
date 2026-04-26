"""Catchups CRUD + negotiation / voting / finalize routes."""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from src.agents import negotiation as negotiation_engine
from src.agents.tools.calendar_tool import parse_window
from src.deps import get_current_user_id
from src.models.schemas import CreateCatchupRequest, VoteRequest
from src.services import gcal_client, supabase_client as db

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

@router.post("/{catchup_id}/negotiate", status_code=202)
async def start_negotiation(
    catchup_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Start the multi-agent negotiation. Fires the orchestrator as a
    background asyncio task and returns immediately so the client can
    open the SSE stream and watch it unfold.
    """
    catchup = await db.get_catchup(catchup_id)
    if not catchup:
        raise HTTPException(status_code=404, detail="Catchup not found")

    members = await db.get_group_members(catchup["group_id"])
    member_ctx = [
        {"user_id": m["user_id"], "name": (m.get("users") or {}).get("name") or "Friend"}
        for m in members
    ]
    if len(member_ctx) < 2:
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 members to negotiate (you + at least one friend)",
        )

    negotiation = await db.create_negotiation(catchup_id)
    await db.update_catchup_status(catchup_id, "negotiating")

    window_from_dt, window_until_dt = parse_window(
        str(catchup.get("time_window") or "")
    )

    asyncio.create_task(
        negotiation_engine.run_negotiation(
            negotiation_id=negotiation["id"],
            catchup_id=catchup_id,
            members=member_ctx,
            window_from=window_from_dt,
            window_until=window_until_dt,
            vibe=str(catchup.get("vibe") or ""),
        )
    )

    logger.info("Negotiation %s started for catchup %s", negotiation["id"], catchup_id)
    return negotiation


@router.get("/{catchup_id}/negotiate/stream")
async def negotiate_stream(catchup_id: str):
    """SSE stream of the live negotiation dialogue.

    Replays the in-memory history first so a client connecting after the
    orchestrator started doesn't miss anything, then forwards each new
    message until the orchestrator emits its terminal `done` role.
    """
    neg = await db.get_latest_negotiation(catchup_id)
    if not neg:
        raise HTTPException(status_code=404, detail="No negotiation for this catchup")
    negotiation_id = neg["id"]

    queue, replay = negotiation_engine.subscribe(negotiation_id)

    async def event_generator():
        try:
            for msg in replay:
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "message", "data": msg}),
                }
                if msg.get("role") == "done":
                    yield {"event": "done", "data": json.dumps({"type": "done"})}
                    return
            if negotiation_engine.is_finished(negotiation_id):
                yield {"event": "done", "data": json.dumps({"type": "done"})}
                return
            while True:
                msg = await queue.get()
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "message", "data": msg}),
                }
                if msg.get("role") == "done":
                    yield {"event": "done", "data": json.dumps({"type": "done"})}
                    return
        finally:
            negotiation_engine.unsubscribe(negotiation_id, queue)

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
    catchup = await db.get_catchup(catchup_id)
    if not catchup:
        return vote

    # Reject → re-launch a new negotiation round with the rejection as
    # context. We only re-trigger when the catchup is actually showing a
    # proposal (status == "proposed"); a stray reject during an in-flight
    # negotiation is just noise.
    if body.vote == "reject" and catchup.get("status") == "proposed":
        await _restart_negotiation_after_reject(catchup, user_id, body.reason or "")
        return vote

    # First accept moves the catchup to "accepted" (demo path — Léa/Tom
    # are simulated members so we don't wait for them to vote). The
    # transition is one-shot: subsequent accept votes don't re-trigger
    # the calendar push.
    if (
        body.vote == "accept"
        and catchup.get("status") == "proposed"
    ):
        await db.update_catchup_status(catchup_id, "accepted")
        # Fire-and-forget the calendar push so the vote response stays
        # fast; users without a connected calendar are skipped silently.
        asyncio.create_task(_push_to_calendars_safely(catchup_id))
    return vote


async def _push_to_calendars_safely(catchup_id: str) -> None:
    """Wrapper so a Google API hiccup never crashes the background task."""
    try:
        await gcal_client.push_catchup_to_calendars(catchup_id)
    except Exception:
        logger.exception("Calendar push background task failed")


async def _restart_negotiation_after_reject(
    catchup: dict, voter_id: str, reason: str
) -> None:
    """Build the rejection context and fire a fresh negotiation as a
    background task. The frontend already navigates the user back to
    /catchup/negotiating after voting reject — its SSE stream picks up
    the new negotiation via `get_latest_negotiation`.
    """
    catchup_id = catchup["id"]

    members = await db.get_group_members(catchup["group_id"])
    member_ctx = [
        {
            "user_id": m["user_id"],
            "name": (m.get("users") or {}).get("name") or "Friend",
        }
        for m in members
    ]
    if len(member_ctx) < 2:
        return

    voter = await db.get_user(voter_id)
    voter_name = (voter or {}).get("name") or "A member"

    prior_attempts: list[dict] = []
    last_proposal = await db.get_proposal(catchup_id)
    if last_proposal:
        prior_attempts.append(
            {
                "proposal": {
                    "venue": last_proposal.get("venue"),
                    "time": last_proposal.get("time"),
                    "activity": last_proposal.get("activity"),
                },
                "rejections": [
                    {"by": voter_name, "reason": reason or "no reason given"}
                ],
            }
        )

    negotiation = await db.create_negotiation(catchup_id)
    await db.update_catchup_status(catchup_id, "negotiating")

    window_from_dt, window_until_dt = parse_window(
        str(catchup.get("time_window") or "")
    )

    asyncio.create_task(
        negotiation_engine.run_negotiation(
            negotiation_id=negotiation["id"],
            catchup_id=catchup_id,
            members=member_ctx,
            window_from=window_from_dt,
            window_until=window_until_dt,
            vibe=str(catchup.get("vibe") or ""),
            prior_attempts=prior_attempts,
        )
    )
    logger.info(
        "Restarted negotiation %s for catchup %s after %s rejected",
        negotiation["id"], catchup_id, voter_name,
    )


@router.post("/{catchup_id}/finalize")
async def finalize_catchup(
    catchup_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Push event to Google Calendars of all members."""
    await db.update_catchup_status(catchup_id, "done")
    # TODO (phase 2): push to Google Calendar via gcal_client.create_event
    return {"status": "finalized", "catchup_id": catchup_id}
