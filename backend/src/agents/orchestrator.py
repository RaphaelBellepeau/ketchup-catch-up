"""Orchestrator LLM — focused Gemini calls for the negotiation pipeline.

Two functions, each making a single structured Gemini call:

  find_common_slot()  Phase 1: given N calendar schedules, find the best
                               common time slot for a group meetup.

  pick_venue()        Phase 2: given Tavily search results + group prefs,
                               select the best venue. (Not used in Phase 1.)

Uses google-genai SDK with GOOGLE_API_KEY from .env.
JSON mode is requested via response_mime_type to avoid markdown-wrapping.
"""

import json
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class SlotDecision(BaseModel):
    """Best common time slot agreed by the orchestrator."""
    day: str = Field(description="Day name, e.g. 'jeudi'")
    time: str = Field(description="Start time, e.g. '20h30'")
    reasoning: str = Field(description="Short French explanation (max 2 sentences)")


class FinalProposal(BaseModel):
    """Final venue + time proposal produced by the orchestrator."""
    venue: str
    url: str = ""
    time: str = Field(description="Full day + time, e.g. 'jeudi 20h30'")
    activity: str = Field(description="Type of outing, e.g. 'dîner'")
    justification: str = Field(description="Why this venue fits the group (≤ 3 sentences)")


# ---------------------------------------------------------------------------
# Gemini call helper
# ---------------------------------------------------------------------------

async def _call_gemini_json(system_instruction: str, user_prompt: str) -> dict:
    """Make a single Gemini call and return a parsed JSON dict.

    Uses response_mime_type='application/json' so the model returns raw JSON
    without markdown fences. Falls back to manual fence-stripping just in case.

    Raises:
        json.JSONDecodeError: if the model response is not valid JSON.
        Exception: any google-genai transport error.
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
            temperature=0.2,
            max_output_tokens=512,
            response_mime_type="application/json",
            # Disable thinking tokens — they break JSON parsing by prepending
            # reasoning content before the actual JSON output.
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )

    raw = response.text or ""

    # Strip markdown fences if present (defensive fallback)
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines
            if not line.startswith("```")
        ).strip()

    # Slice from the first '{' to the last '}' to handle any residual prefix/suffix
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in Gemini response: {raw[:300]!r}")
    raw = raw[start : end + 1]

    return json.loads(raw)


# ---------------------------------------------------------------------------
# Phase 1 — Schedule alignment
# ---------------------------------------------------------------------------

_SLOT_SYSTEM = """\
Tu es l'orchestrateur d'une application Catch-Up qui aide des amis à planifier des sorties.
Ta tâche : analyser les emplois du temps de N participants et trouver le MEILLEUR créneau commun.

Règles strictes :
- Choisis un créneau marqué ✓ dans TOUS les agendas si possible.
- Si aucun créneau n'est commun à tous, choisis celui qui convient au plus grand nombre et explique le compromis.
- Préfère les soirées (après 19h) pour un dîner, les après-midis pour une activité.
- Réponds UNIQUEMENT avec un JSON valide respectant exactement ce schéma :

{
  "day": "<nom du jour, ex: jeudi>",
  "time": "<heure de début, ex: 20h30>",
  "reasoning": "<explication courte en français, max 2 phrases>"
}
"""


async def find_common_slot(
    schedules: list[dict],
    catchup_context: dict,
) -> SlotDecision:
    """Ask Gemini to find the best common time slot from all agents' schedules.

    Args:
        schedules: List of dicts with keys: agent_name, user_name, schedule_text.
        catchup_context: Dict with at least: vibe, time_window.

    Returns:
        SlotDecision (day, time, reasoning). Returns a safe fallback on error.
    """
    vibe = catchup_context.get("vibe", "dîner")
    time_window = catchup_context.get("time_window", "prochaines 2 semaines")

    schedules_text = "\n\n".join(
        f"=== {s['user_name']} ===\n{s['schedule_text']}"
        for s in schedules
    )

    user_prompt = (
        f"Type de sortie : {vibe}\n"
        f"Fenêtre de planification : {time_window}\n\n"
        f"Agendas des {len(schedules)} participants :\n\n"
        f"{schedules_text}\n\n"
        "Quel est le meilleur créneau commun pour organiser ce rendez-vous ?"
    )

    try:
        data = await _call_gemini_json(_SLOT_SYSTEM, user_prompt)
        decision = SlotDecision(**data)
        logger.info(
            "Slot found: %s %s — %s",
            decision.day, decision.time, decision.reasoning,
        )
        return decision

    except Exception as exc:
        logger.error("find_common_slot failed: %s — returning fallback slot", exc)
        return SlotDecision(
            day="jeudi",
            time="20h30",
            reasoning=f"Créneau par défaut (orchestrateur indisponible : {exc})",
        )


# ---------------------------------------------------------------------------
# Phase 2 — Venue selection  (not used in the Phase-1 demo)
# ---------------------------------------------------------------------------

_VENUE_SYSTEM = """\
Tu es l'orchestrateur d'une application Catch-Up qui aide des amis à planifier des sorties.
Ta tâche : choisir le MEILLEUR lieu parmi les résultats de recherche, en respectant les préférences du groupe.

Règles strictes :
- Évite absolument les cuisines que quelqu'un n'aime pas.
- Respecte les contraintes alimentaires (végétarien, halal, sans gluten, etc.).
- Prends le budget le plus restrictif du groupe comme plafond.
- S'il n'y a pas de résultat parfait, choisis le moins mauvais et explique le compromis.
- Réponds UNIQUEMENT avec un JSON valide respectant exactement ce schéma :

{
  "venue": "<nom exact du lieu>",
  "url": "<url si disponible, sinon chaîne vide>",
  "time": "<jour et heure convenus, ex: jeudi 20h30>",
  "activity": "<type de sortie, ex: dîner, soirée, activité sportive>",
  "justification": "<pourquoi ce lieu est le meilleur compromis, max 3 phrases>"
}
"""


async def pick_venue(
    slot: SlotDecision,
    venues: list[dict],
    group_prefs: dict,
    catchup_context: dict,
) -> FinalProposal:
    """Ask Gemini to pick the best venue from Tavily results.

    Args:
        slot: The agreed time slot from Phase 1.
        venues: Tavily results — list of {title, url, snippet}.
        group_prefs: Compiled group preferences from compile_group_preferences().
        catchup_context: Dict with at least: vibe, location.

    Returns:
        FinalProposal. Returns a safe fallback on error.
    """
    agreed_time = f"{slot.day} à {slot.time}"
    vibe = catchup_context.get("vibe", "dîner")

    venues_text = (
        "\n\n".join(
            f"Option {i+1}: {v['title']}\n"
            f"URL: {v.get('url', 'N/A')}\n"
            f"Description: {v.get('snippet', '(aucune description)')}"
            for i, v in enumerate(venues)
        )
        if venues
        else "Aucun résultat de recherche disponible — propose un lieu générique adapté."
    )

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
        data = await _call_gemini_json(_VENUE_SYSTEM, user_prompt)
        proposal = FinalProposal(**data)
        logger.info("Venue selected: %s at %s", proposal.venue, proposal.time)
        return proposal

    except Exception as exc:
        logger.error("pick_venue failed: %s — returning fallback proposal", exc)
        fallback_venue = venues[0]["title"] if venues else "Lieu à déterminer"
        fallback_url = venues[0].get("url", "") if venues else ""
        return FinalProposal(
            venue=fallback_venue,
            url=fallback_url,
            time=agreed_time,
            activity=vibe,
            justification=f"Sélection automatique (orchestrateur indisponible : {exc})",
        )
