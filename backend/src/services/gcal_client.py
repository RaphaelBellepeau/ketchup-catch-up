"""Google Calendar API client.

Real implementation: OAuth tokens stored in Supabase, Google Calendar freebusy API.

CURRENT STATE: mock schedules — deterministic per user_id so each agent in a
negotiation consistently defends a different schedule. Swap get_calendar_context()
body for the real API call once OAuth credentials are configured.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock schedule templates (next 2 weeks, natural language, French)
# Each template is realistic enough for agents to negotiate around.
# ---------------------------------------------------------------------------

_SCHEDULE_TEMPLATES = [
    # Template 0 — busy professional
    (
        "Créneaux libres sur les 2 prochaines semaines :\n"
        "- Mardi soir (19h–23h) ✓\n"
        "- Jeudi soir (20h–23h) ✓\n"
        "- Samedi après-midi et soir (14h–23h) ✓\n\n"
        "Indisponibilités :\n"
        "- Lundi toute la journée (réunions de travail)\n"
        "- Mercredi soir (sport)\n"
        "- Vendredi soir et samedi matin (voyage prévu)"
    ),
    # Template 1 — social, free on weekday evenings
    (
        "Créneaux libres sur les 2 prochaines semaines :\n"
        "- Lundi soir (19h–22h) ✓\n"
        "- Mercredi soir (18h–23h) ✓\n"
        "- Vendredi soir (18h–minuit) ✓\n"
        "- Dimanche après-midi (14h–20h) ✓\n\n"
        "Indisponibilités :\n"
        "- Mardi soir (dîner de famille)\n"
        "- Jeudi soir (sport)\n"
        "- Samedi toute la journée (événement personnel)"
    ),
    # Template 2 — weekend person, evenings mostly busy
    (
        "Créneaux libres sur les 2 prochaines semaines :\n"
        "- Samedi toute la journée (10h–23h) ✓\n"
        "- Dimanche matin et après-midi (10h–18h) ✓\n"
        "- Jeudi soir (20h–23h) ✓\n\n"
        "Indisponibilités :\n"
        "- Lundi au mercredi soir (réunions tardives)\n"
        "- Vendredi soir (soirée déjà prévue)\n"
        "- Dimanche soir (besoin de se reposer avant la semaine)"
    ),
    # Template 3 — flexible, lots of availability
    (
        "Créneaux libres sur les 2 prochaines semaines :\n"
        "- Mardi soir (19h–23h) ✓\n"
        "- Mercredi soir (19h–23h) ✓\n"
        "- Vendredi soir (18h–minuit) ✓\n"
        "- Samedi toute la journée et soir ✓\n"
        "- Dimanche matin (10h–14h) ✓\n\n"
        "Indisponibilités :\n"
        "- Lundi toute la journée (travail intensif)\n"
        "- Jeudi (sport le soir)"
    ),
    # Template 4 — lots of constraints, hard to plan
    (
        "Créneaux libres sur les 2 prochaines semaines :\n"
        "- Mercredi soir semaine 1 (20h–23h) ✓\n"
        "- Samedi après-midi semaine 1 (15h–19h) ✓\n"
        "- Dimanche semaine 2 (11h–17h) ✓\n\n"
        "Indisponibilités :\n"
        "- Semaine 1 : très chargé (projet urgent au boulot)\n"
        "- Vendredi semaine 1 : départ en week-end\n"
        "- Lundi semaine 2 : retour et récupération\n"
        "- Mardi–jeudi semaine 2 : conférence professionnelle"
    ),
]


def _pick_template(user_id: str) -> str:
    """Select a schedule template deterministically based on user_id."""
    if not user_id:
        return _SCHEDULE_TEMPLATES[0]
    try:
        # Hash the user_id UUID digits to an index
        digits = user_id.replace("-", "")
        idx = int(digits[:8], 16) % len(_SCHEDULE_TEMPLATES)
        return _SCHEDULE_TEMPLATES[idx]
    except (ValueError, IndexError):
        return _SCHEDULE_TEMPLATES[0]


def get_calendar_context(
    user_id: str,
    time_window: str = "next 2 weeks",
    intent: str = "dinner",
) -> str:
    """Return a natural-language summary of the user's schedule.

    This text is injected directly into the agent's system prompt so the agent
    can defend its user's availability during negotiation without exposing raw
    calendar data to other agents.

    Args:
        user_id: The user whose schedule to summarise.
        time_window: Time range label (informational, e.g. "next 2 weeks").
        intent: Type of outing — colours the framing of the summary.

    Returns:
        A multi-line string describing free slots and busy periods.

    TODO: Replace body with real implementation:
        1. Load OAuth tokens from `calendar_tokens` Supabase table.
        2. Refresh if expired via google-auth.
        3. Call `calendar_v3.freebusy().query()` for the time window.
        4. Convert busy intervals to natural language.
    """
    logger.info(
        "calendar_context requested: user=%s window=%s intent=%s [MOCK]",
        user_id,
        time_window,
        intent,
    )
    return _pick_template(user_id)


async def get_busy_slots(user_id: str, date_range: str = "next 2 weeks") -> list[dict]:
    """Fetch busy slots from Google Calendar for a user.

    TODO: Implement with google-api-python-client + stored OAuth tokens.

    Returns:
        List of dicts with 'start' and 'end' ISO timestamps.
    """
    logger.info("get_busy_slots: user=%s range=%s [MOCK — returns empty]", user_id, date_range)
    return []


async def create_event(
    user_id: str,
    title: str,
    start_time: str,
    end_time: str,
    location: str = "",
    attendees: list[str] | None = None,
) -> dict:
    """Create a Google Calendar event for a user.

    TODO: Implement with google-api-python-client.
    """
    logger.info("create_event: '%s' at %s for user %s [MOCK]", title, start_time, user_id)
    return {
        "status": "success",
        "event_id": "mock_event_id",
        "message": f"Event '{title}' created (mock)",
    }
