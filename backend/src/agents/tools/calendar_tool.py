"""Calendar tool for agents to check their user's availability."""

import logging

from src.services.gcal_client import get_calendar_context

logger = logging.getLogger(__name__)


def check_availability(
    user_id: str,
    date_range: str = "next 2 weeks",
    intent: str = "dinner",
) -> dict:
    """Check the user's calendar availability for the given date range.

    This tool is called by the user's own agent only. It returns a natural-
    language summary of availability — never raw calendar data. The agent
    uses this to negotiate without exposing the full schedule.

    The same context is also pre-injected into the agent's system prompt at
    negotiation start, so this tool is mainly useful mid-conversation when
    the agent needs to re-confirm specific availability.

    Args:
        user_id: The user whose calendar to check.
        date_range: Time range to look at, e.g. "next 2 weeks".
        intent: Type of event (dinner, drinks, activity) to contextualise time slots.

    Returns:
        dict with status and a text summary of available slots.

    TODO: get_calendar_context() will hit real GCal once OAuth is wired.
    """
    try:
        summary = get_calendar_context(
            user_id=user_id,
            time_window=date_range,
            intent=intent,
        )
        # Extract individual slots from the summary for structured access
        slots = [
            line.strip().lstrip("- ").rstrip(" ✓")
            for line in summary.splitlines()
            if "✓" in line
        ]
        return {
            "status": "success",
            "summary": summary,
            "slots": slots,
        }
    except Exception as e:
        logger.error("Calendar check failed for user %s: %s", user_id, e)
        return {
            "status": "error",
            "error": str(e),
            "summary": "Impossible de vérifier le calendrier pour le moment.",
            "slots": [],
        }
