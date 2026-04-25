"""Multi-agent negotiation orchestrator.

This is the core of Catch-Up: multiple user agents negotiate
a meetup plan through structured dialogue rounds.
"""

import asyncio
import json
import logging
from datetime import datetime

from src.agents.user_agent import create_user_agent
from src.agents.tools.calendar_tool import check_availability
from src.agents.tools.tavily_tool import search_venues
from src.agents.tools.memory_tool import get_user_memories
from src.models.schemas import NegotiationMessage

logger = logging.getLogger(__name__)

# In-memory message queues per negotiation (for SSE streaming)
# In prod, this would be Supabase Realtime
_negotiation_streams: dict[str, asyncio.Queue] = {}


def get_or_create_stream(negotiation_id: str) -> asyncio.Queue:
    """Get or create a message queue for SSE streaming."""
    if negotiation_id not in _negotiation_streams:
        _negotiation_streams[negotiation_id] = asyncio.Queue()
    return _negotiation_streams[negotiation_id]


async def emit_message(
    negotiation_id: str,
    agent_name: str,
    role: str,
    content: str,
    data: dict | None = None,
) -> NegotiationMessage:
    """Emit a negotiation message to the stream and log it."""
    msg = NegotiationMessage(
        agent_name=agent_name,
        role=role,
        content=content,
        data=data or {},
        timestamp=datetime.now(),
    )

    queue = get_or_create_stream(negotiation_id)
    await queue.put(msg)

    # TODO: also write to Supabase negotiation_messages table
    logger.info(f"[{negotiation_id}] {agent_name} ({role}): {content[:80]}...")

    return msg


async def run_negotiation(
    negotiation_id: str,
    catchup_id: str,
    members: list[dict],
    catchup_context: dict,
) -> dict:
    """Run a full A2A negotiation between user agents.

    Args:
        negotiation_id: Unique ID for this negotiation session.
        catchup_id: The catchup being negotiated.
        members: List of dicts with user_id, name, preferences, history.
        catchup_context: Dict with vibe, time_window, group_members.

    Returns:
        dict with the final proposal or failure reason.
    """
    await emit_message(
        negotiation_id,
        agent_name="system",
        role="info",
        content=f"Négociation lancée pour {len(members)} participants...",
    )

    # Create an agent per member
    agents = {}
    for member in members:
        tools = [check_availability, search_venues, get_user_memories]
        agent = create_user_agent(
            user_id=member["user_id"],
            user_name=member["name"],
            preferences=member.get("preferences", {}),
            history=member.get("history", []),
            catchup_context=catchup_context,
            tools=tools,
        )
        agents[member["user_id"]] = {
            "agent": agent,
            "name": member["name"],
            "preferences": member.get("preferences", {}),
        }

    # === Negotiation rounds ===
    # Simple protocol: initiator proposes → others respond → iterate max 3 rounds
    max_rounds = 3
    proposal = None

    for round_num in range(max_rounds):
        await emit_message(
            negotiation_id,
            agent_name="system",
            role="info",
            content=f"--- Tour {round_num + 1}/{max_rounds} ---",
        )

        # TODO: Actually invoke each agent via ADK runner
        # For now, simulate the negotiation flow for demo scaffolding
        
        initiator = members[0]
        initiator_name = f"{initiator['name'].lower().replace(' ', '_')}_agent"

        if round_num == 0:
            # Initiator proposes
            await emit_message(
                negotiation_id,
                agent_name=initiator_name,
                role="propose",
                content=f"Je propose qu'on se retrouve mardi soir pour un dîner. "
                f"{initiator['name']} est libre et adore la cuisine italienne. "
                f"Qu'est-ce que vous en pensez ?",
                data={"proposed_day": "mardi", "proposed_time": "20h", "cuisine": "italien"},
            )

            # Others respond
            for member in members[1:]:
                agent_name = f"{member['name'].lower().replace(' ', '_')}_agent"
                await emit_message(
                    negotiation_id,
                    agent_name=agent_name,
                    role="counter",
                    content=f"{member['name']} préfère jeudi soir, mais mardi peut marcher "
                    f"si c'est après 20h. Pour la cuisine, pas de sushi svp !",
                    data={"available": ["mardi après 20h", "jeudi soir"]},
                )

                # Small delay for dramatic effect in SSE stream
                await asyncio.sleep(0.8)

        elif round_num == 1:
            # Convergence round
            await emit_message(
                negotiation_id,
                agent_name=initiator_name,
                role="propose",
                content="OK, mardi 20h30 ça marche pour tout le monde ? "
                "Je cherche un bon italien dans le 11e...",
            )
            await asyncio.sleep(0.5)

            # Tavily search for a real venue
            venue_results = search_venues(
                query="restaurant italien",
                location="Paris 11e",
                max_results=3,
            )

            venue_name = "La Trattoria"
            if venue_results["status"] == "success" and venue_results["venues"]:
                venue_name = venue_results["venues"][0]["title"]

            await emit_message(
                negotiation_id,
                agent_name=initiator_name,
                role="propose",
                content=f"J'ai trouvé {venue_name} dans le 11e, très bien noté. "
                f"Mardi 20h30, ça vous va ?",
                data={"venue": venue_name, "time": "mardi 20h30"},
            )

            for member in members[1:]:
                agent_name = f"{member['name'].lower().replace(' ', '_')}_agent"
                await emit_message(
                    negotiation_id,
                    agent_name=agent_name,
                    role="accept",
                    content=f"Parfait pour {member['name']} ! Mardi 20h30 à {venue_name} 🤝",
                )
                await asyncio.sleep(0.5)

            proposal = {
                "venue": venue_name,
                "time": "mardi 20h30",
                "activity": "dîner italien",
                "justification": f"Compromis trouvé : {venue_name} dans le 11e, "
                f"mardi 20h30 — convient à tous les participants.",
            }
            break

    # Emit final result
    if proposal:
        await emit_message(
            negotiation_id,
            agent_name="system",
            role="info",
            content=f"✅ Consensus trouvé ! {proposal['venue']} — {proposal['time']}",
            data=proposal,
        )
    else:
        await emit_message(
            negotiation_id,
            agent_name="system",
            role="info",
            content="❌ Pas de consensus après 3 tours. Proposition du meilleur compromis...",
        )

    # Signal end of stream
    await emit_message(
        negotiation_id,
        agent_name="system",
        role="done",
        content="Négociation terminée.",
        data={"proposal": proposal},
    )

    return {"negotiation_id": negotiation_id, "proposal": proposal}
