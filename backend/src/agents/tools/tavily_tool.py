"""Tavily search tool for finding venues and activities."""

import logging

from src.config import settings

logger = logging.getLogger(__name__)


def search_venues(
    query: str,
    location: str = "Paris",
    max_results: int = 8,
    search_depth: str = "advanced",
) -> dict:
    """Search for restaurants, bars, or activities using Tavily.

    Defaults to ``search_depth=advanced`` and ``max_results=8`` because
    the negotiation orchestrator runs a downstream LLM pass that extracts
    real venue names from listicles — it benefits from richer raw text.

    Args:
        query: What to search for, e.g. "italian dinner cozy".
        location: City or area to search in.
        max_results: Maximum number of raw Tavily results.
        search_depth: "basic" (cheap, snippets) or "advanced" (deeper).

    Returns:
        ``{"status", "answer", "venues": [{title, url, snippet}]}``.
    """
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(
            query=f"{query} {location}".strip(),
            search_depth=search_depth,
            max_results=max_results,
            include_answer=True,
        )

        venues = []
        for result in response.get("results", []):
            venues.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": (result.get("content", "") or "")[:600],
            })

        return {
            "status": "success",
            "answer": response.get("answer", "") or "",
            "venues": venues,
        }
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "answer": "",
            "venues": [],
        }
