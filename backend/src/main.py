"""Catch-Up Backend — FastAPI application."""

import logging
import pathlib

# Load .env into os.environ BEFORE importing gradbot — Gradbot reads
# GRADIUM_API_KEY / LLM_API_KEY directly from the process environment, not
# from our pydantic-settings Settings object.
from dotenv import load_dotenv

load_dotenv()

import gradbot  # noqa: E402
from fastapi import FastAPI, Request, WebSocket  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from src.config import settings  # noqa: E402
from src.llm_proxy import router as llm_proxy_router  # noqa: E402
from src.routers import (  # noqa: E402
    auth,
    calendar as calendar_router,
    catchups,
    feedbacks,
    friends,
    groups,
    memories,
    users,
)
from src.voice.persist import persist_onboarding_memories  # noqa: E402
from src.voice.service import voice_service  # noqa: E402
from src.voice.tasks import build_task  # noqa: E402

logging.basicConfig(level=logging.INFO)
# Surface gradbot's Rust-side logs (LLM/TTS/STT errors) on stdout.
import gradbot as _gradbot_init  # noqa: E402

_gradbot_init.init_logging()
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
app.include_router(calendar_router.router)
app.include_router(llm_proxy_router)


# ── Health ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.env}


# ── Invites ────────────────────────────────────────────

@app.post("/invites/notify", tags=["invites"])
async def notify_non_member():
    """Send SMS to non-member friend with meetup summary. Bonus feature."""
    return {"todo": "implement — bonus"}


# ── Voice (Gradbot WebSocket) ──────────────────────────

@app.websocket("/ws/voice/{task_type}/{user_id}")
async def ws_voice(websocket: WebSocket, task_type: str, user_id: str):
    """Unified Gradbot voice session for onboarding and feedback.

    Gradbot accepts the WebSocket itself — do NOT call websocket.accept() here.
    """
    logger.info("Voice session starting: task=%s user=%s", task_type, user_id)

    try:
        task = build_task(task_type, user_id)
    except ValueError as e:
        await websocket.close(code=1008, reason=str(e))
        return

    result = await voice_service.handle_session(websocket, task)

    if result.success and task_type == "onboarding":
        await persist_onboarding_memories(user_id, result.extracted_data)
    elif not result.success:
        logger.warning(
            "Voice session ended without extracted data: task=%s user=%s",
            task_type,
            user_id,
        )


# ── Gradbot static assets (must come AFTER routers) ────
# Serves /static/js/{opus-encoder,audio-processor,synced-audio-player}.js
# and /api/audio-config — required by the browser-side Gradbot client.

_GRADBOT_STATIC_DIR = pathlib.Path(__file__).parent / "voice" / "static"
_GRADBOT_STATIC_DIR.mkdir(parents=True, exist_ok=True)

gradbot.routes.setup(
    app,
    config=gradbot.config.from_env(),
    static_dir=_GRADBOT_STATIC_DIR,
)
