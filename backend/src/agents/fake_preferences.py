"""Fake user preferences for negotiation demo.

Deterministic mock data keyed by user_id hash — 5 distinct personas with
real tension (budget conflicts, dietary constraints, cuisine clashes) so
agents genuinely have something to negotiate about.

TODO: Replace get_user_preferences() body with a Supabase query to the
      memories table (scope = "cuisine" | "schedule" | "general").
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Preference personas
# ---------------------------------------------------------------------------

_PREFERENCE_TEMPLATES = [
    {   # 0 — Foodie / high budget
        "cuisines_liked": ["italien", "français", "japonais"],
        "cuisines_disliked": ["fast food", "kebab"],
        "budget": "high",
        "dietary": [],
        "preferred_areas": ["11e", "6e", "Marais"],
        "dislikes": ["trop bruyant", "service lent", "carte trop courte"],
    },
    {   # 1 — Budget-conscious student
        "cuisines_liked": ["brasserie", "thaï", "libanais"],
        "cuisines_disliked": ["gastronomique", "japonais"],
        "budget": "low",
        "dietary": [],
        "preferred_areas": ["10e", "11e", "République"],
        "dislikes": ["prix > 25€/pers", "dress code", "réservation obligatoire"],
    },
    {   # 2 — Health-first vegetarian
        "cuisines_liked": ["végétalien", "méditerranéen", "libanais"],
        "cuisines_disliked": ["fast food", "viande obligatoire"],
        "budget": "medium",
        "dietary": ["végétarien"],
        "preferred_areas": ["9e", "Batignolles", "Montmartre"],
        "dislikes": ["ambiance trop festive", "fumée"],
    },
    {   # 3 — Adventurous food explorer
        "cuisines_liked": ["thaï", "coréen", "péruvien", "éthiopien"],
        "cuisines_disliked": ["brasserie classique"],
        "budget": "medium",
        "dietary": [],
        "preferred_areas": ["13e", "Belleville", "Oberkampf"],
        "dislikes": ["restaurants sans originalité", "menu fixe uniquement"],
    },
    {   # 4 — Classic Parisian
        "cuisines_liked": ["brasserie", "bistrot", "français classique"],
        "cuisines_disliked": ["trop épicé", "fusion expérimental"],
        "budget": "medium",
        "dietary": [],
        "preferred_areas": ["Saint-Germain", "7e", "Invalides"],
        "dislikes": ["musique trop forte", "tables trop serrées", "tendance instagram"],
    },
]


def _pick_template(user_id: str) -> dict:
    """Select a preference template deterministically based on user_id."""
    if not user_id:
        return _PREFERENCE_TEMPLATES[0]
    try:
        digits = user_id.replace("-", "")
        idx = int(digits[:8], 16) % len(_PREFERENCE_TEMPLATES)
        return _PREFERENCE_TEMPLATES[idx]
    except (ValueError, IndexError):
        return _PREFERENCE_TEMPLATES[0]


def get_user_preferences(user_id: str) -> dict:
    """Return deterministic fake preferences for a user.

    Args:
        user_id: The user's UUID.

    Returns:
        Dict with cuisines_liked, cuisines_disliked, budget, dietary,
        preferred_areas, dislikes.

    TODO: Replace body with:
        memories = await supabase_client.get_memories(user_id, scope="cuisine")
        return parse_memories_into_prefs(memories)
    """
    prefs = _pick_template(user_id)
    logger.debug("fake_preferences: user=%s → budget=%s dietary=%s", user_id, prefs["budget"], prefs["dietary"])
    return prefs


def compile_group_preferences(members_prefs: list[dict]) -> dict:
    """Merge preferences from all group members for the Tavily search query.

    Rules:
    - Budget: take the most restrictive (lowest) across the group
    - Cuisines liked: union, minus anything anyone dislikes
    - Dietary: union (any constraint applies to the whole group)
    - Dislikes: union

    Args:
        members_prefs: List of preference dicts from get_user_preferences().

    Returns:
        Unified group preference dict.
    """
    budget_rank = {"low": 0, "medium": 1, "high": 2}
    min_budget = "high"

    all_liked: list[str] = []
    all_disliked: list[str] = []
    all_dietary: list[str] = []
    all_dislikes: list[str] = []

    for prefs in members_prefs:
        all_liked.extend(prefs.get("cuisines_liked", []))
        all_disliked.extend(prefs.get("cuisines_disliked", []))
        all_dietary.extend(prefs.get("dietary", []))
        all_dislikes.extend(prefs.get("dislikes", []))
        b = prefs.get("budget", "medium")
        if budget_rank.get(b, 1) < budget_rank.get(min_budget, 2):
            min_budget = b

    # Remove anything anyone dislikes from the liked list
    disliked_set = {d.lower() for d in all_disliked}
    safe_liked = [c for c in all_liked if c.lower() not in disliked_set]

    return {
        "cuisines_liked": list(dict.fromkeys(safe_liked)),   # dedupe, preserve order
        "cuisines_disliked": list(set(all_disliked)),
        "dietary": list(set(all_dietary)),
        "budget": min_budget,
        "dislikes": list(set(all_dislikes)),
    }
