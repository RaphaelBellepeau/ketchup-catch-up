"""Demo negotiation — Phase 1 only (no auth, no DB, no ADK agents).

Pipeline:
  1. Three fake user-agents emit their calendar availability over SSE.
  2. The Gemini orchestrator (find_common_slot) analyses all three schedules
     and returns the best common time slot.
  3. A "done" sentinel is pushed so the SSE client knows to close.

Intentional schedule tension:
  Raphaël  ✓ Tue evening, Thu evening, Sat afternoon/evening
  Marie    ✓ Mon evening, Wed evening, Fri evening, Sun afternoon
  Thomas   ✓ Sat all day, Sun morning/afternoon, Thu evening

→ Thursday evening is the ONLY slot that works for all three.
  Gemini should identify this.

SSE queue is keyed by session_id (default "demo").
Call reset_demo_stream() before each run to avoid stale messages.
"""

import asyncio
import logging
from datetime import datetime

from src.agents.orchestrator import find_common_slot
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
    """Run Phase 1: fake agents share calendars → Gemini finds common slot.

    Each step is streamed to the SSE queue in real time.
    A 'done' sentinel is always emitted at the end (even on error) so the
    SSE client can close cleanly.

    Args:
        session_id: Key for the SSE queue (default "demo").

    Returns:
        {"session_id": ..., "slot": SlotDecision.model_dump() | None}
    """
    # Brief pause so the SSE client has time to connect before messages flow
    await asyncio.sleep(0.8)

    slot_decision = None

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

        # ── Confirmation ──────────────────────────────────────────────────
        await _emit(
            session_id, "system", "info",
            "✔️ Phase 1 terminée. Le créneau est validé — les agents ont trouvé un accord.",
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
            "Négociation Phase 1 terminée.",
            data={"slot": slot_decision},
        )

    return {"session_id": session_id, "slot": slot_decision}
