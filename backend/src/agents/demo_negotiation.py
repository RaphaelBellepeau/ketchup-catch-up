"""Demo negotiation — Phase 1 + Phase 2 (no auth, no DB, no ADK agents).

Pipeline:
  Phase 1 — Calendar sharing:
    1. Three fake user-agents emit their calendar availability over SSE.
    2. The Gemini orchestrator (find_common_slot) analyses all three schedules
       and returns the best common time slot.

  Phase 2 — Preference sharing + search query:
    3. Each agent shares their food/budget/dietary preferences.
    4. The orchestrator compiles group preferences (handling tensions).
    5. A structured Tavily search query JSON is emitted.
    6. A "done" sentinel is pushed so the SSE client knows to close.

Intentional schedule tension:
  Raphaël  ✓ Tue evening, Thu evening, Sat afternoon/evening
  Marie    ✓ Mon evening, Wed evening, Fri evening, Sun afternoon
  Thomas   ✓ Sat all day, Sun morning/afternoon, Thu evening

→ Thursday evening is the ONLY slot that works for all three.
  Gemini should identify this.

Intentional preference tension:
  Raphaël  budget=high,  likes japonais
  Marie    budget=low,   dislikes japonais & gastronomique
  Thomas   végétarien,   budget=medium

→ compile_group_preferences should yield:
    budget=low, dietary=[végétarien], japonais removed from liked.

SSE queue is keyed by session_id (default "demo").
Call reset_demo_stream() before each run to avoid stale messages.
"""

import asyncio
import json
import logging
from datetime import datetime

from src.agents.fake_preferences import compile_group_preferences
from src.agents.orchestrator import find_common_slot, pick_venue
from src.agents.tools.tavily_tool import build_venue_query, search_venues
from src.models.schemas import NegotiationMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory SSE queues (keyed by session_id)
# ---------------------------------------------------------------------------

_demo_streams: dict[str, asyncio.Queue] = {}


def get_or_create_demo_stream(session_id: str = "demo") -> asyncio.Queue:
    """Return existing queue or create a new one."""
    if session_id not in _demo_streams:
        _demo_streams[session_id] = asyncio.Queue()
    return _demo_streams[session_id]


def reset_demo_stream(session_id: str = "demo") -> asyncio.Queue:
    """Always create a fresh queue — call this before each negotiation run
    so stale messages from a previous session don't bleed into the new stream.
    """
    _demo_streams[session_id] = asyncio.Queue()
    return _demo_streams[session_id]


def cleanup_demo_stream(session_id: str = "demo") -> None:
    """Remove the queue once the SSE client has consumed all messages."""
    _demo_streams.pop(session_id, None)


# ---------------------------------------------------------------------------
# Fake member roster
# ---------------------------------------------------------------------------

DEMO_MEMBERS = [
    {
        "id": "raphael-demo",
        "name": "Raphaël",
        "emoji": "🧑‍💻",
        "persona": "busy professional",
        "schedule_text": (
            "Créneaux libres sur les 2 prochaines semaines :\n"
            "- Mardi soir (19h–23h) ✓\n"
            "- Jeudi soir (20h–23h) ✓\n"
            "- Samedi après-midi et soir (14h–23h) ✓\n\n"
            "Indisponibilités :\n"
            "- Lundi toute la journée (réunions de travail)\n"
            "- Mercredi soir (sport)\n"
            "- Vendredi soir et samedi matin (voyage prévu)"
        ),
        "preferences": {
            "cuisines_liked": ["italien", "français", "japonais"],
            "cuisines_disliked": ["fast food", "kebab"],
            "budget": "high",
            "dietary": [],
            "preferred_areas": ["11e", "6e", "Marais"],
        },
    },
    {
        "id": "marie-demo",
        "name": "Marie",
        "emoji": "👩‍🎨",
        "persona": "social, free evenings",
        "schedule_text": (
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
        "preferences": {
            "cuisines_liked": ["brasserie", "thaï", "libanais"],
            "cuisines_disliked": ["gastronomique", "japonais"],
            "budget": "low",
            "dietary": [],
            "preferred_areas": ["10e", "11e", "République"],
        },
    },
    {
        "id": "thomas-demo",
        "name": "Thomas",
        "emoji": "🧘",
        "persona": "weekend person, vegetarian",
        "schedule_text": (
            "Créneaux libres sur les 2 prochaines semaines :\n"
            "- Samedi toute la journée (10h–23h) ✓\n"
            "- Dimanche matin et après-midi (10h–18h) ✓\n"
            "- Jeudi soir (20h–23h) ✓\n\n"
            "Indisponibilités :\n"
            "- Lundi au mercredi soir (réunions tardives)\n"
            "- Vendredi soir (soirée déjà prévue)\n"
            "- Dimanche soir (besoin de se reposer avant la semaine)"
        ),
        "preferences": {
            "cuisines_liked": ["végétalien", "méditerranéen", "libanais"],
            "cuisines_disliked": ["fast food", "viande obligatoire"],
            "budget": "medium",
            "dietary": ["végétarien"],
            "preferred_areas": ["9e", "Batignolles", "Montmartre"],
        },
    },
]

DEMO_CATCHUP_CONTEXT = {
    "vibe": "dîner",
    "time_window": "prochaines 2 semaines",
    "location": "Paris",
    "group_members": [m["name"] for m in DEMO_MEMBERS],
}


# ---------------------------------------------------------------------------
# Emit helper
# ---------------------------------------------------------------------------

async def _emit(
    session_id: str,
    agent_name: str,
    role: str,
    content: str,
    data: dict | None = None,
) -> NegotiationMessage:
    """Push a NegotiationMessage onto the SSE queue and log it."""
    msg = NegotiationMessage(
        agent_name=agent_name,
        role=role,
        content=content,
        data=data or {},
        timestamp=datetime.now(),
    )
    queue = get_or_create_demo_stream(session_id)
    await queue.put(msg)
    logger.info("[demo/%s] %s (%s): %.100s", session_id, agent_name, role, content)
    return msg


# ---------------------------------------------------------------------------
# Phase 1 pipeline
# ---------------------------------------------------------------------------

async def run_demo_negotiation(session_id: str = "demo") -> dict:
    """Run the full demo negotiation pipeline (Phase 1 + Phase 2).

    Phase 1: fake agents share calendars → Gemini finds common slot.
    Phase 2: agents share preferences → orchestrator compiles group prefs
             → builds a Tavily search query JSON.

    Each step is streamed to the SSE queue in real time.
    A 'done' sentinel is always emitted at the end (even on error) so the
    SSE client can close cleanly.

    Args:
        session_id: Key for the SSE queue (default "demo").

    Returns:
        {"session_id": ..., "slot": ..., "search_payload": ...}
    """
    # Brief pause so the SSE client has time to connect before messages flow
    await asyncio.sleep(0.8)

    slot_decision = None
    search_result = None
    final_proposal = None

    try:
        # ── Kick-off ──────────────────────────────────────────────────────
        await _emit(
            session_id, "system", "info",
            f"🚀 Négociation démarrée — {len(DEMO_MEMBERS)} agents en ligne...",
        )
        await asyncio.sleep(0.5)

        # ── Phase 1 announcement ──────────────────────────────────────────
        await _emit(
            session_id, "system", "info",
            "📅 Phase 1 : chaque agent partage son agenda avec le groupe...",
        )
        await asyncio.sleep(0.6)

        # ── Each fake agent shares their calendar ─────────────────────────
        schedules = []
        for member in DEMO_MEMBERS:
            agent_name = f"{member['name'].lower()}_agent"

            # Natural "typing" pause
            await asyncio.sleep(0.9)

            await _emit(
                session_id,
                agent_name,
                "schedule",
                (
                    f"{member['emoji']} **{member['name']}** partage son agenda :\n\n"
                    f"{member['schedule_text']}"
                ),
                data={
                    "user_id": member["id"],
                    "user_name": member["name"],
                    "persona": member["persona"],
                },
            )

            schedules.append({
                "agent_name": agent_name,
                "user_name": member["name"],
                "schedule_text": member["schedule_text"],
            })

            await asyncio.sleep(0.4)

        # ── Orchestrator: find common slot via Gemini ─────────────────────
        await asyncio.sleep(0.5)
        await _emit(
            session_id, "orchestrator", "thinking",
            "🧠 Orchestrateur : analyse des 3 agendas avec Gemini...",
        )
        await asyncio.sleep(0.8)

        slot = await find_common_slot(schedules, DEMO_CATCHUP_CONTEXT)

        await _emit(
            session_id,
            "orchestrator",
            "slot",
            (
                f"✅ Créneau commun trouvé : **{slot.day}** à **{slot.time}**\n\n"
                f"💬 {slot.reasoning}"
            ),
            data={
                "day": slot.day,
                "time": slot.time,
                "reasoning": slot.reasoning,
            },
        )

        slot_decision = slot.model_dump()

        await asyncio.sleep(0.6)

        # ── Confirmation Phase 1 ───────────────────────────────────────────
        await _emit(
            session_id, "system", "info",
            "✔️ Phase 1 terminée. Le créneau est validé — les agents ont trouvé un accord.",
        )

        await asyncio.sleep(0.8)

        # ══════════════════════════════════════════════════════════════════
        # PHASE 2 — Preference sharing + search query
        # ══════════════════════════════════════════════════════════════════

        await _emit(
            session_id, "system", "info",
            "🍽️ Phase 2 : chaque agent partage ses préférences pour trouver le lieu idéal...",
        )
        await asyncio.sleep(0.6)

        # ── Each fake agent shares their preferences ──────────────────────
        for member in DEMO_MEMBERS:
            agent_name = f"{member['name'].lower()}_agent"
            prefs = member["preferences"]

            await asyncio.sleep(0.9)

            # Build a natural-language summary
            pref_lines = []
            if prefs.get("cuisines_liked"):
                pref_lines.append(f"Cuisines aimées : {', '.join(prefs['cuisines_liked'])}")
            if prefs.get("cuisines_disliked"):
                pref_lines.append(f"Cuisines évitées : {', '.join(prefs['cuisines_disliked'])}")
            if prefs.get("budget"):
                budget_labels = {"low": "petit budget", "medium": "budget moyen", "high": "budget élevé"}
                pref_lines.append(f"Budget : {budget_labels.get(prefs['budget'], prefs['budget'])}")
            if prefs.get("dietary"):
                pref_lines.append(f"Contraintes alimentaires : {', '.join(prefs['dietary'])}")
            if prefs.get("preferred_areas"):
                pref_lines.append(f"Quartiers préférés : {', '.join(prefs['preferred_areas'])}")

            pref_text = "\n".join(f"- {line}" for line in pref_lines)

            await _emit(
                session_id,
                agent_name,
                "preferences",
                (
                    f"{member['emoji']} **{member['name']}** partage ses préférences :\n\n"
                    f"{pref_text}"
                ),
                data={
                    "user_id": member["id"],
                    "user_name": member["name"],
                    "preferences": prefs,
                },
            )

            await asyncio.sleep(0.4)

        # ── Orchestrator: compile group preferences ───────────────────────
        await asyncio.sleep(0.5)
        await _emit(
            session_id, "orchestrator", "thinking",
            "🧠 Orchestrateur : synthèse des préférences du groupe...",
        )
        await asyncio.sleep(0.8)

        prefs_list = [m["preferences"] for m in DEMO_MEMBERS]
        group_prefs = compile_group_preferences(prefs_list)

        # Human-readable summary of the compiled group preferences
        group_summary_parts = []
        if group_prefs["cuisines_liked"]:
            group_summary_parts.append(f"✅ Cuisines retenues : {', '.join(group_prefs['cuisines_liked'])}")
        if group_prefs["cuisines_disliked"]:
            group_summary_parts.append(f"🚫 Cuisines exclues : {', '.join(group_prefs['cuisines_disliked'])}")
        if group_prefs["dietary"]:
            group_summary_parts.append(f"🥗 Contraintes : {', '.join(group_prefs['dietary'])}")
        budget_labels = {"low": "petit budget", "medium": "budget moyen", "high": "budget élevé"}
        group_summary_parts.append(f"💰 Budget retenu : {budget_labels.get(group_prefs['budget'], group_prefs['budget'])}")
        if group_prefs.get("dislikes"):
            group_summary_parts.append(f"👎 À éviter : {', '.join(group_prefs['dislikes'])}")

        group_summary = "\n".join(group_summary_parts)

        await _emit(
            session_id,
            "orchestrator",
            "group_preferences",
            f"📊 **Préférences compilées du groupe** :\n\n{group_summary}",
            data={"group_preferences": group_prefs},
        )

        await asyncio.sleep(0.6)

        # ── Orchestrator: build Tavily search query ───────────────────────
        vibe = DEMO_CATCHUP_CONTEXT.get("vibe", "dîner")
        location = DEMO_CATCHUP_CONTEXT.get("location", "Paris")
        search_query_text = build_venue_query(group_prefs, vibe=vibe)

        search_payload = {
            "query": f"{search_query_text} {location}",
            "search_depth": "basic",
            "max_results": 5,
            "include_answer": True,
        }

        await _emit(
            session_id,
            "orchestrator",
            "search_query",
            (
                f"🔎 Requête de recherche construite : « {search_query_text} » à {location}\n\n"
                f"Payload Tavily :\n"
                f"```json\n{json.dumps(search_payload, ensure_ascii=False, indent=2)}\n```"
            ),
            data={
                "search_payload": search_payload,
                "search_query": search_query_text,
                "location": location,
            },
        )

        search_result = search_payload  # keep the query payload for reference

        await asyncio.sleep(0.6)

        # ══════════════════════════════════════════════════════════════════
        # PHASE 3 — Tavily search + venue selection
        # ══════════════════════════════════════════════════════════════════

        await _emit(
            session_id, "system", "info",
            "🔍 Phase 3 : recherche Tavily en cours et sélection du lieu...",
        )
        await asyncio.sleep(0.5)

        # ── Call Tavily ───────────────────────────────────────────────────
        await _emit(
            session_id, "orchestrator", "thinking",
            f"🌐 Appel Tavily : « {search_query_text} » à {location}...",
        )

        tavily_result = await search_venues(
            query=search_query_text,
            location=location,
            max_results=5,
        )

        venues = []
        if tavily_result["status"] == "success" and tavily_result.get("venues"):
            venues = tavily_result["venues"]

            # Emit Tavily's synthesized answer if available
            if tavily_result.get("answer"):
                await _emit(
                    session_id, "orchestrator", "info",
                    f"💡 Résumé Tavily : {tavily_result['answer'][:300]}",
                )
                await asyncio.sleep(0.4)

            # Emit each venue option
            for i, v in enumerate(venues):
                snippet = (v.get("snippet") or "")[:150]
                await _emit(
                    session_id,
                    "orchestrator",
                    "venue_option",
                    f"📍 Option {i+1} : **{v['title']}**\n{snippet}",
                    data={"title": v["title"], "url": v.get("url", ""), "snippet": snippet},
                )
                await asyncio.sleep(0.4)
        else:
            error_msg = tavily_result.get("error", "Pas de résultats")
            await _emit(
                session_id, "orchestrator", "info",
                f"⚠️ Tavily n'a pas trouvé de résultats : {error_msg}\n"
                "L'orchestrateur va proposer un lieu générique.",
            )

        await asyncio.sleep(0.5)

        # ── Orchestrator: pick the best venue via Gemini ──────────────────
        await _emit(
            session_id, "orchestrator", "thinking",
            "🧠 Orchestrateur : sélection du meilleur lieu avec Gemini...",
        )
        await asyncio.sleep(0.5)

        proposal = await pick_venue(slot, venues, group_prefs, DEMO_CATCHUP_CONTEXT)

        await _emit(
            session_id,
            "orchestrator",
            "proposal",
            (
                f"🎉 **Proposition finale** :\n\n"
                f"📍 **{proposal.venue}**\n"
                f"🕐 {proposal.time}\n"
                f"🍽️ {proposal.activity}\n"
                + (f"🔗 {proposal.url}\n" if proposal.url else "")
                + f"\n💬 {proposal.justification}"
            ),
            data=proposal.model_dump(),
        )

        final_proposal = proposal.model_dump()

        await asyncio.sleep(0.6)

        # ── Confirmation ──────────────────────────────────────────────────
        await _emit(
            session_id, "system", "info",
            "✔️ Négociation terminée ! Le lieu et le créneau sont validés. 🎊",
        )

    except Exception as exc:
        logger.exception("Demo negotiation (session=%s) failed: %s", session_id, exc)
        await _emit(
            session_id, "system", "error",
            f"❌ Erreur inattendue dans la négociation : {exc}",
        )

    finally:
        # Always emit 'done' so the SSE client knows to close the connection
        await _emit(
            session_id, "system", "done",
            "Négociation terminée.",
            data={
                "slot": slot_decision,
                "search_payload": search_result,
                "proposal": final_proposal,
            },
        )

    return {
        "session_id": session_id,
        "slot": slot_decision,
        "search_payload": search_result,
        "proposal": final_proposal,
    }
