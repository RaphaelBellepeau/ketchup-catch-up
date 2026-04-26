"""Multi-agent negotiation orchestrator — 2-phase pipeline.

Phase 1 — Schedule sharing:
  Each agent emits their calendar availability.
  Orchestrator Gemini call finds the best common slot.

Phase 2 — Venue discovery:
  Group preferences compiled from all members.
  Tavily search for real venues.
  Orchestrator Gemini call picks the best match.

SSE stream is keyed by catchup_id (not negotiation_id) so the stream
endpoint can find the queue with just the catchup_id from the URL.
"""

import asyncio
import json
import logging
from datetime import datetime

from src.agents.user_agent import create_user_agent
from src.agents.tools.calendar_tool import check_availability
from src.agents.tools.tavily_tool import search_venues
from src.agents.tools.memory_tool import get_user_memories
from src.agents.orchestrator import find_common_slot, pick_venue
from src.agents.fake_preferences import compile_group_preferences
from src.models.schemas import NegotiationMessage
from src.services.gcal_client import get_calendar_context
from src.services import supabase_client as db

logger = logging.getLogger(__name__)

# SSE message queues keyed by catchup_id
_negotiation_streams: dict[str, asyncio.Queue] = {}


def get_or_create_stream(catchup_id: str) -> asyncio.Queue:
    """Get or create a message queue for SSE streaming."""
    if catchup_id not in _negotiation_streams:
        _negotiation_streams[catchup_id] = asyncio.Queue()
    return _negotiation_streams[catchup_id]


def cleanup_stream(catchup_id: str) -> None:
    """Remove the stream queue once negotiation is complete."""
    _negotiation_streams.pop(catchup_id, None)


async def emit_message(
    catchup_id: str,
    agent_name: str,
    role: str,
    content: str,
    data: dict | None = None,
) -> NegotiationMessage:
    """Emit a negotiation message to the SSE queue."""
    msg = NegotiationMessage(
        agent_name=agent_name,
        role=role,
        content=content,
        data=data or {},
        timestamp=datetime.now(),
    )
    queue = get_or_create_stream(catchup_id)
    await queue.put(msg)
    logger.info("[%s] %s (%s): %.80s", catchup_id, agent_name, role, content)
    return msg


async def run_negotiation(
    negotiation_id: str,
    catchup_id: str,
    members: list[dict],
    catchup_context: dict,
) -> dict:
    """Run the 2-phase A2A negotiation pipeline.

    Args:
        negotiation_id: DB id for logging/persistence.
        catchup_id: Used as the SSE queue key and for DB updates.
        members: List of {user_id, name, preferences, history}.
        catchup_context: {vibe, time_window, location, group_members}.

    Returns:
        {negotiation_id, proposal} dict.
    """
    # Small delay so the SSE client can connect before messages start flowing
    await asyncio.sleep(0.8)

    final_proposal = None

    try:
        await emit_message(catchup_id, "system", "info",
                           f"🚀 Négociation lancée pour {len(members)} participant(s)...")

        # ── Create agents (with calendar context in their system prompt) ──────
        agents = {}
        for member in members:
            try:
                cal_ctx = get_calendar_context(
                    user_id=member["user_id"],
                    time_window=catchup_context.get("time_window", "next 2 weeks"),
                    intent=catchup_context.get("vibe", "dinner"),
                )
            except Exception as exc:
                logger.warning("calendar_context failed for %s: %s", member["name"], exc)
                cal_ctx = ""

            agent = create_user_agent(
                user_id=member["user_id"],
                user_name=member["name"],
                preferences=member.get("preferences", {}),
                history=member.get("history", []),
                catchup_context=catchup_context,
                calendar_context=cal_ctx,
                tools=[check_availability, search_venues, get_user_memories],
            )
            agents[member["user_id"]] = {
                "agent": agent,
                "name": member["name"],
                "calendar": cal_ctx,
            }

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 1 — Schedule sharing
        # ══════════════════════════════════════════════════════════════════════
        await emit_message(catchup_id, "system", "info",
                           "📅 Phase 1 : chaque agent partage son agenda...")

        schedules = []
        for member in members:
            agent_name = f"{member['name'].lower().replace(' ', '_')}_agent"
            cal_text = agents[member["user_id"]]["calendar"]

            await emit_message(
                catchup_id, agent_name, "schedule",
                f"Voici les disponibilités de {member['name']} :\n{cal_text}",
                data={"user_id": member["user_id"]},
            )
            schedules.append({
                "agent_name": agent_name,
                "user_name": member["name"],
                "schedule_text": cal_text,
            })
            await asyncio.sleep(0.6)

        # Orchestrator Phase 1 — find common slot
        await emit_message(catchup_id, "orchestrator", "info",
                           "🧠 Orchestrateur : analyse des agendas en cours...")
        slot = await find_common_slot(schedules, catchup_context)
        await emit_message(
            catchup_id, "orchestrator", "slot",
            f"✅ Créneau commun trouvé : {slot.day} à {slot.time}\n💬 {slot.reasoning}",
            data={"day": slot.day, "time": slot.time, "reasoning": slot.reasoning},
        )

        await asyncio.sleep(0.4)

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 2 — Venue discovery
        # ══════════════════════════════════════════════════════════════════════
        await emit_message(catchup_id, "system", "info",
                           "🔍 Phase 2 : recherche du meilleur endroit...")

        # Compile group preferences
        prefs_list = [member.get("preferences", {}) for member in members]
        group_prefs = compile_group_preferences(prefs_list)

        # Build Tavily search query
        vibe = catchup_context.get("vibe", "restaurant")
        cuisines = " ".join(group_prefs["cuisines_liked"][:2]) if group_prefs["cuisines_liked"] else ""
        dietary = " ".join(group_prefs["dietary"]) if group_prefs["dietary"] else ""
        query = " ".join(filter(None, [vibe, cuisines, dietary])).strip() or "restaurant"
        location = catchup_context.get("location", "Paris")

        await emit_message(catchup_id, "orchestrator", "info",
                           f"🔎 Recherche Tavily : « {query} » à {location}...")

        venue_results = search_venues(query=query, location=location, max_results=5)
        venues = []
        if venue_results["status"] == "success" and venue_results["venues"]:
            venues = venue_results["venues"]
            for v in venues:
                snippet = (v.get("snippet") or "")[:120]
                await emit_message(
                    catchup_id, "orchestrator", "venue_option",
                    f"📍 {v['title']} — {snippet}",
                    data={"title": v["title"], "url": v.get("url", "")},
                )
                await asyncio.sleep(0.3)
        else:
            await emit_message(catchup_id, "orchestrator", "info",
                               "⚠️ Pas de résultats Tavily — l'orchestrateur va proposer un lieu.")

        # Orchestrator Phase 2 — pick venue
        await emit_message(catchup_id, "orchestrator", "info",
                           "🧠 Orchestrateur : sélection du meilleur lieu...")
        proposal = await pick_venue(slot, venues, group_prefs, catchup_context)

        await emit_message(
            catchup_id, "orchestrator", "confirm",
            f"🎉 Proposition finale : **{proposal.venue}** — {proposal.time}\n{proposal.justification}",
            data=proposal.model_dump(),
        )

        # ── Persist to DB ──────────────────────────────────────────────────
        try:
            await db.save_proposal(catchup_id, {
                "venue": proposal.venue,
                "time": proposal.time,
                "activity": proposal.activity,
                "justification": proposal.justification,
            })
            await db.update_catchup_status(catchup_id, "proposed")
        except Exception as exc:
            logger.error("DB persist failed for catchup %s: %s", catchup_id, exc)

        final_proposal = proposal.model_dump()

    except Exception as exc:
        logger.exception("Negotiation %s failed: %s", negotiation_id, exc)
        await emit_message(catchup_id, "system", "error",
                           f"❌ Erreur inattendue : {exc}")

    finally:
        await emit_message(
            catchup_id, "system", "done",
            "Négociation terminée.",
            data={"proposal": final_proposal},
        )
        # Queue cleanup happens in the SSE generator after it reads "done"

    return {"negotiation_id": negotiation_id, "proposal": final_proposal}
