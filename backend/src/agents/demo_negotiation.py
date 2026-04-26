"""Demo negotiation pipeline — no auth or DB required.

Three hard-coded fake members share their calendar schedules, then the
Gemini orchestrator (find_common_slot) identifies the best common slot
for a meetup and streams each step via an asyncio.Queue for SSE.

Fake member roster:
  - Raphaël  (persona 0: busy professional, loves Italian/French/Japanese)
  - Marie    (persona 1: social, free weekday evenings, budget-conscious)
  - Thomas   (persona 2: weekend person, vegetarian)

These three have intentional schedule tension:
  Raphaël  ✓ Tue evening, Thu evening, Sat
  Marie    ✓ Mon evening, Wed evening, Fri evening, Sun afternoon
  Thomas   ✓ Sat all day, Sun morning/afternoon, Thu evening

→ Thursday evening is the only common slot, which Gemini should find.
"""

import asyncio
import logging
from datetime import datetime

from src.agents.orchestrator import find_common_slot
from src.models.schemas import NegotiationMessage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory SSE queues (keyed by session id, typically "demo")
# ---------------------------------------------------------------------------

_demo_streams: dict[str, asyncio.Queue] = {}


def get_or_create_demo_stream(session_id: str = "demo") -> asyncio.Queue:
    if session_id not in _demo_streams:
        _demo_streams[session_id] = asyncio.Queue()
    return _demo_streams[session_id]


def cleanup_demo_stream(session_id: str = "demo") -> None:
    _demo_streams.pop(session_id, None)


# ---------------------------------------------------------------------------
# Fake member data
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
    msg = NegotiationMessage(
        agent_name=agent_name,
        role=role,
        content=content,
        data=data or {},
        timestamp=datetime.now(),
    )
    queue = get_or_create_demo_stream(session_id)
    await queue.put(msg)
    logger.info("[demo/%s] %s (%s): %.80s", session_id, agent_name, role, content)
    return msg


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run_demo_negotiation(session_id: str = "demo") -> dict:
    """Run Phase 1 demo: 3 agents share calendars → Gemini finds common slot.

    Args:
        session_id: Key for the SSE queue (default "demo").

    Returns:
        dict with slot decision and member schedules.
    """
    # Brief pause so the SSE client has time to connect
    await asyncio.sleep(0.8)

    slot_decision = None

    try:
        await _emit(
            session_id, "system", "info",
            f"🚀 Négociation lancée — {len(DEMO_MEMBERS)} agents en ligne..."
        )
        await asyncio.sleep(0.5)

        # ── PHASE 1: Each agent shares their calendar ─────────────────────
        await _emit(
            session_id, "system", "info",
            "📅 Phase 1 : chaque agent partage son agenda avec les autres..."
        )
        await asyncio.sleep(0.6)

        schedules = []
        for member in DEMO_MEMBERS:
            agent_name = f"{member['name'].lower()}_agent"

            # Brief "typing" pause to feel natural
            await asyncio.sleep(0.8)

            await _emit(
                session_id,
                agent_name,
                "schedule",
                f"{member['emoji']} {member['name']} partage son agenda :\n\n{member['schedule_text']}",
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

        # ── ORCHESTRATOR: Find common slot via Gemini ─────────────────────
        await asyncio.sleep(0.5)
        await _emit(
            session_id, "orchestrator", "info",
            "🧠 Orchestrateur : analyse des 3 agendas avec Gemini..."
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
        await _emit(
            session_id, "system", "info",
            "✔️ Phase 1 terminée. Le créneau est validé par tous les agents."
        )

    except Exception as exc:
        logger.exception("Demo negotiation failed: %s", exc)
        await _emit(
            session_id, "system", "error",
            f"❌ Erreur inattendue : {exc}"
        )

    finally:
        await _emit(
            session_id, "system", "done",
            "Négociation terminée.",
            data={"slot": slot_decision},
        )

    return {"session_id": session_id, "slot": slot_decision}
