"""Catch-Up Backend — FastAPI application."""

import logging

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import settings
from src.routers import auth, catchups, feedbacks, friends, groups, memories, users

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Catch-Up API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Error handling ─────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


# ── Routers ────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(friends.router)
app.include_router(groups.router)
app.include_router(catchups.router)
app.include_router(memories.router)
app.include_router(feedbacks.router)


# ── Health ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.env}


# ── Calendar ───────────────────────────────────────────

@app.get("/calendar/auth-link", tags=["calendar"])
async def calendar_auth_link():
    # TODO: generate Google OAuth URL
    return {"todo": "implement"}


@app.post("/calendar/sync", tags=["calendar"])
async def calendar_sync():
    # TODO: pull busy slots from Google Calendar
    return {"todo": "implement"}


@app.get("/calendar/context", tags=["calendar"])
async def calendar_context(user_id: str, date_range: str, intent: str = ""):
    """Internal: returns text summary of schedule for agent reasoning."""
    # TODO: call gcal_client
    return {"todo": "implement"}


# ── Invites ────────────────────────────────────────────

@app.post("/invites/notify", tags=["invites"])
async def notify_non_member():
    """Send SMS to non-member friend with meetup summary. Bonus feature."""
    return {"todo": "implement — bonus"}


# ── Voice (Gradbot WebSocket) ──────────────────────────

@app.websocket("/ws/voice/{task_type}/{user_id}")
async def ws_voice(websocket: WebSocket, task_type: str, user_id: str):
    """Unified Gradbot voice session for onboarding and feedback."""
    await websocket.accept()
    logger.info("Voice session started: task=%s user=%s", task_type, user_id)
    # TODO: import VoiceService, build VoiceTask, handle session
    await websocket.close()
