"""Demo router — auth-free endpoints for hackathon demo.

POST /demo/negotiate        — start the demo negotiation (Phase 1: calendars + Gemini slot)
GET  /demo/negotiate/stream — SSE stream of agent messages
GET  /demo/status           — health check
"""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/negotiate")
async def start_demo_negotiation(background_tasks: BackgroundTasks):
    """Launch the Phase-1 demo A2A negotiation (no auth, no DB).

    Three fake agents (Raphaël, Marie, Thomas) share their calendar schedules,
    then the Gemini orchestrator finds the best common time slot and streams
    every step over SSE.

    Always resets the queue so re-triggering is safe.
    Returns immediately — stream via GET /demo/negotiate/stream.
    """
    from src.agents.demo_negotiation import (
        run_demo_negotiation,
        reset_demo_stream,
        DEMO_MEMBERS,
    )

    # Always start with a fresh queue — no stale messages from a previous run
    reset_demo_stream("demo")

    background_tasks.add_task(run_demo_negotiation, "demo")

    logger.info("Demo negotiation started (Phase 1 only)")
    return {
        "session_id": "demo",
        "status": "started",
        "phase": "calendar_sharing_and_slot_finding",
        "stream_url": "/demo/negotiate/stream",
        "members": [m["name"] for m in DEMO_MEMBERS],
    }


@router.get("/negotiate/stream")
async def demo_negotiate_stream():
    """SSE stream for the demo negotiation session.

    Reads from the in-memory asyncio.Queue populated by run_demo_negotiation().
    Sends a keepalive comment every 25 s to prevent proxy/browser timeouts.
    Stops automatically when it receives the 'done' role message.
    """
    from src.agents.demo_negotiation import get_or_create_demo_stream, cleanup_demo_stream

    async def event_generator():
        queue = get_or_create_demo_stream("demo")
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield {"data": msg.model_dump_json()}
                    if msg.role == "done":
                        break
                except asyncio.TimeoutError:
                    # SSE keepalive — prevents proxy / browser from closing
                    yield {"comment": "keepalive"}
        finally:
            cleanup_demo_stream("demo")

    return EventSourceResponse(event_generator())


@router.get("/status")
async def demo_status():
    """Quick health-check: confirms the demo router is alive."""
    return {"status": "ok", "phase": "1 — calendar sharing + Gemini slot finding"}
