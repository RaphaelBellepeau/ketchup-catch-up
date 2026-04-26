"""Persistence helpers for voice task results.

The voice agent's `save_result` tool returns synthesized sentences (one per
field) ready to be dropped into another agent's prompt later. We don't try
to re-parse or re-template them — we just store each sentence as its own
row in the `memories` table.
"""

import logging

from src.services import supabase_client as db

logger = logging.getLogger(__name__)


def _clean(value: object) -> str | None:
    """Coerce a value to a non-empty stripped string, or None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


async def persist_onboarding_memories(user_id: str, extracted_data: dict) -> int:
    """Save each LLM-synthesized sentence as a memory row, then mark the
    user as onboarded.

    Each value in `extracted_data` is expected to already be a clean,
    prompt-ready third-person sentence (the LLM does the synthesis inside
    the save_result tool call). The field name is used as the memory's
    `scope` — purely for filtering later, no template logic involved.

    Returns the number of memory rows successfully created.
    """
    created = 0
    for field, value in extracted_data.items():
        sentence = _clean(value)
        if not sentence:
            continue
        try:
            await db.create_memory(
                user_id=user_id,
                content=sentence,
                scope=field,
                source="onboarding",
            )
            created += 1
        except Exception:
            logger.exception(
                "Failed to save onboarding memory: user=%s field=%s", user_id, field,
            )

    if created > 0:
        try:
            await db.mark_user_onboarded(user_id)
            logger.info("User marked as onboarded: user=%s", user_id)
        except Exception:
            logger.exception("Failed to mark user onboarded: user=%s", user_id)

    logger.info("Onboarding memories saved: user=%s count=%d", user_id, created)
    return created
