"""Personal user agent built with Google ADK."""

import logging

from google.adk.agents import Agent

from src.agents.prompts import build_agent_prompt

logger = logging.getLogger(__name__)


def create_user_agent(
    user_id: str,
    user_name: str,
    preferences: dict,
    history: list[dict] | None = None,
    catchup_context: dict | None = None,
    calendar_context: str = "",
    tools: list | None = None,
) -> Agent:
    """Create a personalized ADK agent for a user.

    Args:
        user_id: Unique user identifier.
        user_name: Display name.
        preferences: User preferences dict from Supabase.
        history: Recent feedbacks for memory.
        catchup_context: Current catchup params (vibe, time_window, etc.)
        calendar_context: Natural-language schedule for the next 2 weeks,
            pre-fetched from gcal_client.get_calendar_context(). Injected
            into the system prompt so the agent defends real availability.
        tools: List of tool functions the agent can call.

    Returns:
        A configured ADK Agent ready for negotiation.
    """
    prompt = build_agent_prompt(
        user_name=user_name,
        preferences=preferences,
        history=history,
        catchup_context=catchup_context,
        calendar_context=calendar_context,
    )

    agent = Agent(
        model="gemini-2.5-flash",
        name=f"{user_name.lower().replace(' ', '_')}_agent",
        description=f"Personal agent for {user_name}",
        instruction=prompt,
        tools=tools or [],
    )

    logger.info(
        "Created agent for %s (user_id=%s, calendar_context=%s)",
        user_name,
        user_id,
        "injected" if calendar_context else "empty",
    )
    return agent
