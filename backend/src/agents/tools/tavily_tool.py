"""Tavily search tool for finding venues and activities."""

import logging

from src.config import settings

logger = logging.getLogger(__name__)


def search_venues(
    query: str,
    location: str = "Paris",
    max_results: int = 5,
) -> dict:
    """Search for restaurants, bars, or activities using Tavily.

    Args:
        query: What to search for, e.g. "italian restaurant casual dinner".
        location: City or area to search in.
        max_results: Maximum number of results to return.

    Returns:
        dict with status and a list of venue results.
    """
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
                "snippet": result.get("content", "")[:200],
            })

        return {
            "status": "success",
            "answer": response.get("answer", ""),
            "venues": venues,
        }
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "venues": [],
        }
