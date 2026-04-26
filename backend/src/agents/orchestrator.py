"""Orchestrator LLM for multi-agent negotiations.

Two focused Gemini calls — no tools needed, just structured JSON output.
Uses google-genai SDK (v1.73.1) with GOOGLE_API_KEY from .env.

  find_common_slot()  — Phase 1: given N schedules, find the best common slot
  pick_venue()        — Phase 2: given Tavily results + group prefs, pick the venue
"""

import json
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class SlotDecision(BaseModel):
    """Common time slot agreed by the orchestrator."""
    day: str = Field(description="Day name, e.g. 'jeudi'")
    time: str = Field(description="Start time, e.g. '20h30'")
    reasoning: str = Field(description="Short French explanation")


class FinalProposal(BaseModel):
    """Final venue proposal produced by the orchestrator."""
    venue: str
    url: str = ""
    time: str = Field(description="Full day + time, e.g. 'jeudi 20h30'")
    activity: str = Field(description="Type of outing, e.g. 'dîner'")
    justification: str = Field(description="Why this venue fits the group")


# ---------------------------------------------------------------------------
# Shared Gemini call helper
# ---------------------------------------------------------------------------

async def _call_gemini(system_instruction: str, user_prompt: str) -> dict:
    """Make a single Gemini call, return parsed JSON dict.

    Strips markdown fences defensively. Raises on parse failure — callers
    handle exceptions and provide fallbacks.
    """
    from google import genai
    from google.genai import types
    from src.config import settings

    client = genai.Client(api_key=settings.google_api_key)

    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,      # Low temp → consistent structured output
            max_output_tokens=512,
        ),
    )

    raw = response.text.strip()
    # Strip markdown fences if the model wraps anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ---------------------------------------------------------------------------
# Phase 1 — Schedule alignment
# ---------------------------------------------------------------------------

_SLOT_SYSTEM = """Tu es l'orchestrateur d'une négociation Catch-Up.
Ta tâche : analyser les emplois du temps de N participants et trouver le meilleur créneau commun.

Règles :
- Choisis un créneau marqué ✓ dans TOUS les agendas si possible
- Si aucun créneau n'est commun à tous, choisis le créneau qui convient au plus grand nombre
- Préfère les soirées (après 19h) pour un dîner, les après-midis pour une activité

Réponds UNIQUEMENT avec un JSON valide, sans markdown ni backticks :
{
  "day": "nom du jour (ex: jeudi)",
  "time": "heure de début (ex: 20h30)",
  "reasoning": "explication courte en français (max 2 phrases)"
}"""


async def find_common_slot(
    schedules: list[dict],
    catchup_context: dict,
) -> SlotDecision:
    """Ask Gemini to find the best common time slot from all agents' schedules.

    Args:
        schedules: List of dicts — {agent_name, user_name, schedule_text}
        catchup_context: Dict with vibe, time_window, etc.

    Returns:
        SlotDecision with day, time, reasoning.
    """
    vibe = catchup_context.get("vibe", "dîner")
    schedules_text = "\n\n".join(
        f"=== {s['user_name']} ===\n{s['schedule_text']}"
        for s in schedules
    )

    user_prompt = (
        f"Type de sortie : {vibe}\n"
        f"Fenêtre : {catchup_context.get('time_window', 'prochaines 2 semaines')}\n\n"
        f"Agendas des participants :\n\n{schedules_text}\n\n"
        "Quel est le meilleur créneau commun ?"
    )

    try:
        data = await _call_gemini(_SLOT_SYSTEM, user_prompt)
        decision = SlotDecision(**data)
        logger.info("Slot found: %s %s — %s", decision.day, decision.time, decision.reasoning)
        return decision
    except Exception as exc:
        logger.error("find_common_slot failed: %s — using fallback", exc)
        return SlotDecision(
            day="samedi",
            time="19h30",
            reasoning=f"Créneau par défaut (orchestrateur indisponible : {exc})",
        )


# ---------------------------------------------------------------------------
# Phase 2 — Venue selection
# ---------------------------------------------------------------------------

_VENUE_SYSTEM = """Tu es l'orchestrateur d'une négociation Catch-Up.
Ta tâche : choisir le meilleur lieu parmi les résultats de recherche, en tenant compte des préférences du groupe.

Règles :
- Évite absolument les cuisines que quelqu'un n'aime pas
- Respecte les contraintes alimentaires (végétarien, halal, etc.)
- Prends le budget le plus restrictif du groupe comme maximum
- S'il n'y a pas de résultat parfait, choisis le moins mauvais et explique le compromis

Réponds UNIQUEMENT avec un JSON valide, sans markdown ni backticks :
{
  "venue": "nom exact du lieu",
  "url": "url si disponible, sinon chaîne vide",
  "time": "jour et heure convenus (ex: jeudi 20h30)",
  "activity": "type de sortie (ex: dîner, soirée, activité sportive)",
  "justification": "pourquoi ce lieu est le meilleur compromis (max 3 phrases)"
}"""


async def pick_venue(
    slot: SlotDecision,
    venues: list[dict],
    group_prefs: dict,
    catchup_context: dict,
) -> FinalProposal:
    """Ask Gemini to pick the best venue from Tavily results.

    Args:
        slot: The agreed time slot from Phase 1.
        venues: Tavily results — [{title, url, snippet}]
        group_prefs: Compiled group preferences from compile_group_preferences().
        catchup_context: Dict with vibe, location, etc.

    Returns:
        FinalProposal with venue, time, activity, justification.
    """
    agreed_time = f"{slot.day} à {slot.time}"
    vibe = catchup_context.get("vibe", "dîner")

    venues_text = "\n\n".join(
        f"Option {i+1}: {v['title']}\nURL: {v.get('url', 'N/A')}\nDescription: {v.get('snippet', '')}"
        for i, v in enumerate(venues)
    ) if venues else "Aucun résultat Tavily disponible — propose un lieu générique adapté."

    prefs_text = (
        f"Cuisines aimées : {', '.join(group_prefs.get('cuisines_liked', [])) or 'pas de préférence'}\n"
        f"Cuisines évitées : {', '.join(group_prefs.get('cuisines_disliked', [])) or 'aucune'}\n"
        f"Contraintes alimentaires : {', '.join(group_prefs.get('dietary', [])) or 'aucune'}\n"
        f"Budget max du groupe : {group_prefs.get('budget', 'medium')}\n"
        f"À éviter : {', '.join(group_prefs.get('dislikes', [])) or 'rien de particulier'}"
    )

    user_prompt = (
        f"Type de sortie : {vibe}\n"
        f"Créneau convenu : {agreed_time}\n\n"
        f"Préférences du groupe :\n{prefs_text}\n\n"
        f"Résultats de recherche :\n\n{venues_text}\n\n"
        "Quel lieu choisir ?"
    )

    try:
        data = await _call_gemini(_VENUE_SYSTEM, user_prompt)
        proposal = FinalProposal(**data)
        logger.info("Venue selected: %s at %s", proposal.venue, proposal.time)
        return proposal
    except Exception as exc:
        logger.error("pick_venue failed: %s — using fallback", exc)
        fallback_venue = venues[0]["title"] if venues else "Lieu à déterminer"
        fallback_url = venues[0].get("url", "") if venues else ""
        return FinalProposal(
            venue=fallback_venue,
            url=fallback_url,
            time=agreed_time,
            activity=vibe,
            justification=f"Sélection automatique (orchestrateur indisponible : {exc})",
        )
