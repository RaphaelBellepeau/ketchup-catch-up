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


async def persist_feedback_memories(
    user_id: str,
    catchup_id: str | None,
    context: dict,
    extracted_data: dict,
) -> dict:
    """Save the structured feedback from a voice debrief.

    Persists:
      - one row in `feedbacks` (rating + raw fields)
      - 2-4 rows in `memories` (one per LLM-synthesized sentence) so future
        agent negotiations can lean on lived experience

    Returns ``{"feedback_id": str | None, "memories": int}``.
    """
    rating_raw = extracted_data.get("rating")
    try:
        rating = int(rating_raw) if rating_raw is not None else 3
    except (TypeError, ValueError):
        rating = 3
    rating = max(1, min(5, rating))

    liked = _clean(extracted_data.get("liked_summary"))
    disliked = _clean(extracted_data.get("disliked_summary"))
    # Backwards compat: older recordings may still have the old field name.
    relationships = _clean(
        extracted_data.get("relationships_summary")
        or extracted_data.get("group_vibe_summary")
    )
    venue_review = _clean(extracted_data.get("venue_or_activity_review"))

    feedback_id: str | None = None
    if catchup_id:
        try:
            row = await db.save_feedback(
                {
                    "user_id": user_id,
                    "catchup_id": catchup_id,
                    "rating": rating,
                    "liked": [liked] if liked else [],
                    "disliked": [disliked] if disliked else [],
                    "comment": (
                        " · ".join(s for s in (liked, relationships, venue_review) if s)
                        or ""
                    ),
                }
            )
            feedback_id = (row or {}).get("id")
        except Exception:
            logger.exception(
                "Failed to save feedback row for user=%s catchup=%s",
                user_id, catchup_id,
            )

    venue = (context or {}).get("venue") or "the venue"
    activity = (context or {}).get("activity") or "catch-up"
    time_label = (context or {}).get("time_label") or ""
    when_phrase = f" on {time_label}" if time_label else ""

    memory_rows: list[tuple[str, str]] = []
    memory_rows.append((
        "experience",
        f"Rated the {activity} at {venue}{when_phrase}: {rating}/5.",
    ))
    if liked:
        memory_rows.append(("preferences", f"At {venue}: {liked}"))
    if venue_review:
        memory_rows.append(("preferences", f"On {venue} ({activity}): {venue_review}"))
    if disliked:
        memory_rows.append((
            "preferences",
            f"Avoid for next {activity}: {disliked}",
        ))
    if relationships:
        # Stored under "relationship" so the next feedback rebound can pick
        # up a recent relational signal directly (see prompts in tasks.py).
        memory_rows.append(("relationship", f"After {venue}: {relationships}"))

    created = 0
    for scope, content in memory_rows:
        try:
            await db.create_memory(
                user_id=user_id,
                content=content,
                scope=scope,
                source="feedback",
            )
            created += 1
        except Exception:
            logger.exception(
                "Failed to save feedback memory: user=%s scope=%s", user_id, scope,
            )

    logger.info(
        "Feedback persisted: user=%s catchup=%s rating=%s memories=%d",
        user_id, catchup_id, rating, created,
    )
    return {"feedback_id": feedback_id, "memories": created}


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
