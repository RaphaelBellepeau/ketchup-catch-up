"""Google Calendar API client."""

import logging

logger = logging.getLogger(__name__)


async def get_busy_slots(user_id: str, date_range: str) -> list[dict]:
    """Fetch busy slots from Google Calendar for a user.
    
    TODO: Implement with google-api-python-client.
    Requires OAuth token stored in Supabase for the user.
    """
    # TODO: real implementation
    logger.info(f"Calendar sync requested for user {user_id}, range={date_range}")
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
    logger.info(f"Calendar event creation: {title} at {start_time} for user {user_id}")
    return {
        "status": "success",
        "event_id": "mock_event_id",
        "message": f"Event '{title}' created",
    }
