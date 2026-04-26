"""Memory access for negotiation agents.

For phase 1 we read directly from the `memories` table (Supabase). The
function is intentionally async to match the rest of the stack — even
though supabase-py is sync underneath, we wrap to fit the orchestrator.
"""

import logging

from src.services import supabase_client as db

logger = logging.getLogger(__name__)


async def get_user_memories_text(user_id: str) -> list[dict]:
    """Return the user's memory rows ready for prompt injection.

    Each row has at minimum `scope` and `content` — the prompt builder
    just bullets them.
    """
    try:
        memories = await db.get_memories(user_id)
        # Skip anything missing meaningful content.
        return [m for m in memories if (m.get("content") or "").strip()]
    except Exception:
        logger.exception("Failed to load memories for user=%s", user_id)
        return []
