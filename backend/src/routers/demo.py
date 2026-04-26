"""Demo router — auth-free endpoints for hackathon demo.

POST /demo/negotiate        — start the demo negotiation pipeline
GET  /demo/negotiate/stream — SSE stream of agent messages
"""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/negotiate")
async def start_demo_negotiation(background_tasks: BackgroundTasks):
    """Launch the demo A2A negotiation (no auth, no DB).

    Three fake agents (Raphaël, Marie, Thomas) share their calendars,
    then the Gemini orchestrator finds the best common time slot.

    Returns immediately — stream via GET /demo/negotiate/stream.
    """
    from src.agents.demo_negotiation import run_demo_negotiation, get_or_create_demo_stream

    # Reset / create a fresh queue for this session
    get_or_create_demo_stream("demo")

    background_tasks.add_task(run_demo_negotiation, "demo")

    logger.info("Demo negotiation started")
    return {
        "session_id": "demo",
        "status": "started",
        "stream_url": "/demo/negotiate/stream",
        "members": ["Raphaël", "Marie", "Thomas"],
    }


@router.get("/negotiate/stream")
async def demo_negotiate_stream():
    """SSE stream for the demo negotiation session.

    Reads from the in-memory asyncio.Queue populated by run_demo_negotiation().
    Sends a keepalive comment every 25 s to prevent proxy timeouts.
    Stops when it receives the 'done' message.
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
                    yield {"comment": "keepalive"}
        finally:
            cleanup_demo_stream("demo")

    return EventSourceResponse(event_generator())
