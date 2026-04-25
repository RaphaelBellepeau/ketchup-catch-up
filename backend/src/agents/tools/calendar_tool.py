"""Calendar tool for agents to check their user's availability."""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def check_availability(
    user_id: str,
    date_range: str = "next 2 weeks",
    intent: str = "dinner",
) -> dict:
    """Check the user's calendar availability for the given date range.

    This tool is called by the user's own agent only. It returns a natural
    language summary of availability — never raw calendar data. The agent
    uses this to negotiate without exposing the full schedule.

    Args:
        user_id: The user whose calendar to check.
        date_range: Time range to look at, e.g. "next 2 weeks".
        intent: Type of event (dinner, drinks, activity) to contextualize time slots.

    Returns:
        dict with status and a text summary of available slots.
    """
    try:
        # TODO: integrate with Google Calendar API via gcal_client.py
        # For now, return mock data for demo
        mock_slots = {
            "dinner": [
                "mardi 19h-22h",
                "jeudi 20h-23h",
                "samedi 19h-23h",
            ],
            "drinks": [
                "mercredi 18h-21h",
                "vendredi 18h-23h",
                "samedi 17h-20h",
            ],
            "activity": [
                "samedi 14h-18h",
                "dimanche 10h-17h",
            ],
        }

        slots = mock_slots.get(intent, mock_slots["dinner"])

        return {
            "status": "success",
            "summary": f"Créneaux disponibles pour un {intent} dans les {date_range} : {', '.join(slots)}",
            "slots": slots,
        }
    except Exception as e:
        logger.error(f"Calendar check failed for user {user_id}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "summary": "Impossible de vérifier le calendrier pour le moment.",
            "slots": [],
        }
