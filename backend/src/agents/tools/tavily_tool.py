"""Tavily search tool for finding venues and activities."""

import asyncio
import logging

from src.config import settings

logger = logging.getLogger(__name__)


def _search_venues_sync(query: str, location: str, max_results: int) -> dict:
    """Synchronous Tavily search — called via asyncio.to_thread() to avoid blocking."""
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(
            query=f"{query} {location}",
            search_depth="basic",
            max_results=max_results,
            include_answer=True,
        )

        venues = []
        for result in response.get("results", []):
            venues.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("content", "")[:300],
            })

        return {
            "status": "success",
            "answer": response.get("answer", ""),
            "venues": venues,
        }
    except Exception as e:
        logger.error("Tavily search failed: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "venues": [],
        }


async def search_venues(
    query: str,
    location: str = "Paris",
    max_results: int = 5,
) -> dict:
    """Async wrapper — runs the blocking Tavily call in a thread pool.

    Args:
        query: What to search for, e.g. "restaurant méditerranéen végétarien".
        location: City or neighbourhood to search in.
        max_results: Maximum number of results to return.

    Returns:
        dict with status, answer summary, and list of venue dicts
        (title, url, snippet).
    """
    return await asyncio.to_thread(_search_venues_sync, query, location, max_results)


def build_venue_query(group_prefs: dict, vibe: str = "restaurant") -> str:
    """Build a natural-language Tavily query from compiled group preferences.

    Prioritises:
    1. Dietary constraints (hardest filter)
    2. Safe cuisines (liked by all, disliked by none)
    3. Vibe / activity type
    4. Budget signal

    Args:
        group_prefs: Output of compile_group_preferences().
        vibe: Catchup vibe, e.g. "dîner", "brunch", "sortie".

    Returns:
        A concise search query string.
    """
    parts: list[str] = []

    # Dietary constraints first — non-negotiable
    dietary = group_prefs.get("dietary", [])
    if dietary:
        parts.append(" ".join(dietary))

    # Safe cuisines (up to 2 so the query stays focused)
    liked = group_prefs.get("cuisines_liked", [])
    if liked:
        parts.append(" ".join(liked[:2]))

    # Activity type
    parts.append(vibe)

    # Budget hint
    budget = group_prefs.get("budget", "medium")
    if budget == "low":
        parts.append("pas cher abordable")
    elif budget == "high":
        parts.append("gastronomique haut de gamme")

    return " ".join(parts).strip() or "restaurant"
