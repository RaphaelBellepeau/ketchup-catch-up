"""Memory tool for agents to read and update user knowledge."""

import logging

logger = logging.getLogger(__name__)


def get_user_memories(
    user_id: str,
    scope: str = "all",
) -> dict:
    """Retrieve what the agent knows about its user.

    Args:
        user_id: The user to look up.
        scope: Filter by scope — "cuisine", "schedule", "social", or "all".

    Returns:
        dict with status and a list of memory entries.
    """
    try:
        # TODO: read from Supabase memories table
        # For now, return structure for demo
        return {
            "status": "success",
            "memories": [],
            "summary": "Pas encore de mémoire pour cet utilisateur.",
        }
    except Exception as e:
        logger.error(f"Memory read failed for user {user_id}: {e}")
        return {"status": "error", "error": str(e), "memories": []}


def save_user_memory(
    user_id: str,
    scope: str,
    content: str,
    source: str = "agent",
) -> dict:
    """Save a new memory about the user.

    Args:
        user_id: The user this memory is about.
        scope: Category — "cuisine", "schedule", "social", "general".
        content: The memory content in natural language.
        source: Where this memory came from — "onboarding", "feedback", "agent".

    Returns:
        dict with status.
    """
    try:
        # TODO: write to Supabase memories table
        logger.info(f"Memory saved: user={user_id} scope={scope} content={content[:50]}...")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Memory save failed: {e}")
        return {"status": "error", "error": str(e)}
