"""Multi-agent negotiation orchestrator (Phase 1).

Three rounds, in order:
  1. Each user agent proposes its top-3 candidate slots in JSON.
     Orchestrator picks the slot with best consensus.
  2. Each user agent emits venue keywords + neighborhood for that slot.
     Orchestrator merges keywords and asks Tavily for candidates.
  3. Each user agent ranks the Tavily candidates.
     Orchestrator picks the lowest-average-rank venue → final proposal.

Each step EMITS messages (one per agent + orchestrator) onto an in-memory
queue, AND persists them in `negotiation_messages`. The SSE endpoint
subscribes to the queue. Privacy is enforced by separation: each user
agent's prompt sees ONLY that user's memories + busy slots; the
orchestrator only sees structured JSON proposals.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from src.agents import llm_client, prompts
from src.agents.tools.calendar_tool import (
    format_calendar_view,
    get_busy_for_window,
)
from src.agents.tools.memory_tool import get_user_memories_text
from src.agents.tools.tavily_tool import search_venues
from src.services import supabase_client as db

logger = logging.getLogger(__name__)


# ── Streaming queues ──────────────────────────────────

# In-memory broadcast channels per negotiation. Each subscriber gets its
# own asyncio.Queue. We replay the existing message log on subscribe so
# clients connecting late don't miss anything.
_subscribers: dict[str, list[asyncio.Queue]] = {}
_history: dict[str, list[dict]] = {}
_finished: dict[str, bool] = {}


def subscribe(negotiation_id: str) -> tuple[asyncio.Queue, list[dict]]:
    """Open a new SSE subscription. Returns (queue, replay) — the queue is
    the live feed of subsequent messages; replay is everything emitted so
    far for this negotiation, so the client can render the full dialogue
    even if it joined late.
    """
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(negotiation_id, []).append(queue)
    return queue, list(_history.get(negotiation_id, []))


def unsubscribe(negotiation_id: str, queue: asyncio.Queue) -> None:
    subs = _subscribers.get(negotiation_id) or []
    if queue in subs:
        subs.remove(queue)


def is_finished(negotiation_id: str) -> bool:
    return bool(_finished.get(negotiation_id))


async def emit(
    negotiation_id: str,
    *,
    agent_name: str,
    role: str,
    content: str,
    data: dict | None = None,
) -> dict:
    """Persist a message + broadcast to live subscribers."""
    msg = {
        "agent_name": agent_name,
        "role": role,
        "content": content,
        "data": data or {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    _history.setdefault(negotiation_id, []).append(msg)

    # Best-effort persist — don't crash the negotiation if Supabase is flaky.
    try:
        await db.save_negotiation_message(negotiation_id, msg)
    except Exception:
        logger.exception("Persist negotiation message failed (continuing)")

    for q in list(_subscribers.get(negotiation_id, [])):
        try:
            await q.put(msg)
        except Exception:
            pass

    logger.info("[%s] %s (%s): %s", negotiation_id, agent_name, role, content[:100])
    return msg


# ── Helpers ────────────────────────────────────────────

async def _extract_real_venues(
    *,
    tavily_answer: str,
    raw_results: list[dict],
    keywords: list[str],
    neighborhoods: list[str],
    vibe: str,
    location: str,
    max_venues: int = 4,
) -> list[dict]:
    """Run a one-shot LLM pass that pulls real specific venues out of the
    noisy Tavily blob (listicles, reviews, blog posts).

    Returns rows shaped like ``{title, snippet, url}`` so downstream code
    can keep treating them like the old Tavily venue rows.
    """
    if not raw_results and not (tavily_answer or "").strip():
        return []

    sys_p, user_p = prompts.venue_extraction_prompt(
        tavily_answer=tavily_answer,
        tavily_results=raw_results,
        keywords=keywords,
        neighborhoods=neighborhoods,
        vibe=vibe,
        max_venues=max_venues,
    )
    try:
        # Extraction has a richer-than-usual JSON output (4 venues × 4
        # fields). Run it on the configured lite model — the main model's
        # thinking tokens were eating the response budget and truncating
        # the JSON mid-string. Override via LLM_LITE_MODEL env var.
        result = await llm_client.chat_json(
            sys_p,
            user_p,
            temperature=0.2,
            max_tokens=3000,
            model=llm_client.lite_model(),
        )
    except Exception:
        logger.exception("Venue extraction LLM call failed")
        return []

    extracted = result.get("venues") or []
    venues: list[dict] = []
    seen: set[str] = set()
    for v in extracted:
        if not isinstance(v, dict):
            continue
        name = (v.get("name") or "").strip()
        if not name:
            continue
        # Skip obvious listicle/article titles that slipped through.
        lower = name.lower()
        if any(
            phrase in lower
            for phrase in ("top ", "best ", "where to", "guide to", " review", "reddit", "tripadvisor")
        ) or lower.startswith(tuple(str(n) for n in range(10))):
            continue
        if name in seen:
            continue
        seen.add(name)
        description = (v.get("description") or "").strip()
        why_fits = (v.get("why_fits") or "").strip()
        snippet_parts = [p for p in (description, why_fits) if p]
        snippet = " ".join(snippet_parts) or f"Venue in {location}."
        venues.append(
            {
                "title": name,
                "snippet": snippet[:500],
                "url": (v.get("source_url") or "").strip(),
            }
        )
        if len(venues) >= max_venues:
            break
    return venues


def _agent_label(name: str) -> str:
    """Display name in the dialogue feed."""
    first = (name or "").strip().split()[0] or "agent"
    return f"{first}'s agent"


def _slots_match(a: str, b: str) -> bool:
    """Two slot strings match if either contains the other (case-insensitive).
    Loose enough to handle 'Thursday evening' vs 'Thursday 8pm' phrasing.
    """
    an = (a or "").strip().lower()
    bn = (b or "").strip().lower()
    if not an or not bn:
        return False
    return an in bn or bn in an


def _find_unanimous_slot(round_proposals: list[dict]) -> str | None:
    """A slot is unanimous if it appears in EVERY agent's top_slots list
    (with loose matching). Return the first such slot we find, or None.
    """
    if not round_proposals:
        return None
    first_lists = round_proposals[0].get("top_slots") or []
    for candidate in first_lists:
        if all(
            any(_slots_match(candidate, s) for s in (p.get("top_slots") or []))
            for p in round_proposals[1:]
        ):
            return candidate
    return None


def _slot_overlap_summary(slot_summaries: list[dict], chosen: str) -> tuple[str, list[str]]:
    """Classify how unanimous the slot pick is.

    Returns ``(label, flexers)`` where ``label`` is one of
    ``"unanimous" | "majority" | "compromise"`` and ``flexers`` is the list
    of agent names whose top-3 did NOT contain the chosen slot.
    """
    chosen_norm = (chosen or "").strip().lower()

    def _has(slot_list: list[str]) -> bool:
        # Tolerate small variations: chosen is "in" a slot if either
        # contains the other (case-insensitive substring match).
        for s in slot_list:
            sn = (s or "").strip().lower()
            if not sn:
                continue
            if sn in chosen_norm or chosen_norm in sn:
                return True
        return False

    flexers: list[str] = []
    matches = 0
    for s in slot_summaries:
        if _has(s.get("top_slots") or []):
            matches += 1
        else:
            flexers.append(s["name"])

    n = len(slot_summaries) or 1
    if matches == n:
        return "unanimous", []
    if matches >= max(1, n - 1):
        return "majority", flexers
    return "compromise", flexers


def _venue_compromise_summary(
    reactions: list[dict], chosen_index: int, top_k: int = 2
) -> tuple[str, list[str]]:
    """How happy is each agent with the chosen venue?

    Returns ``(label, sacrificers)``. ``label`` ∈ ``unanimous_top1 |
    majority_top_k | compromise``. ``sacrificers`` is the list of agent
    names who ranked the chosen venue WORSE than ``top_k``.
    """
    happy = 0
    sacrificers: list[str] = []
    for r in reactions:
        ranks = r.get("ranked_indices") or []
        try:
            position = ranks.index(chosen_index)
        except ValueError:
            position = len(ranks)
        if position == 0:
            happy += 1
        elif position >= top_k:
            sacrificers.append(r["name"])

    n = len(reactions) or 1
    if happy == n:
        return "unanimous_top1", []
    if not sacrificers:
        return "majority_top_k", []
    return "compromise", sacrificers


async def _gather_user_context(
    member: dict, window_from_dt: datetime, window_until_dt: datetime,
) -> dict:
    """Build the per-agent prompt context (memories + day-by-day calendar).

    Doesn't crash if the calendar isn't reachable — just returns an
    all-Free calendar view in that case (the agent leans on weekly_summary
    memories to fill in recurring blocks).
    """
    memories = await get_user_memories_text(member["user_id"])
    try:
        busy = await get_busy_for_window(
            member["user_id"], window_from_dt, window_until_dt
        )
    except Exception:
        busy = []

    return {
        "user_id": member["user_id"],
        "name": member["name"],
        "memories": memories,
        "busy": busy,
        "calendar_text": format_calendar_view(busy, window_from_dt, window_until_dt),
    }


def _other_names(contexts: list[dict], me: dict) -> list[str]:
    return [c["name"] for c in contexts if c["user_id"] != me["user_id"]]


# ── Main orchestrator ──────────────────────────────────

async def run_negotiation(
    *,
    negotiation_id: str,
    catchup_id: str,
    members: list[dict],
    window_from: datetime,
    window_until: datetime,
    vibe: str,
    default_location: str = "Paris",
    prior_attempts: list[dict] | None = None,
) -> dict:
    """Run the full 3-phase negotiation. `members` is `[{user_id, name}]`.

    ``prior_attempts`` is a list of previously-rejected attempts, each shaped
    like ``{"proposal": {...}, "rejections": [{"by": str, "reason": str}, ...]}``.
    Their content is injected into every agent's prompt so the new round
    actively avoids the previously-rejected slot/venue.
    """
    prior_attempts = prior_attempts or []

    if len(members) < 2:
        await emit(
            negotiation_id,
            agent_name="orchestrator",
            role="info",
            content="Need at least 2 participants to negotiate.",
        )
        return {"proposal": None, "error": "not_enough_members"}

    if prior_attempts:
        last = prior_attempts[-1]
        rejected_summary = ", ".join(
            f"{r.get('by') or 'Someone'} ({r.get('reason') or 'no reason'})"
            for r in (last.get("rejections") or [])
        ) or "the group"
        last_prop = last.get("proposal") or {}
        await emit(
            negotiation_id,
            agent_name="orchestrator",
            role="info",
            content=(
                f"Restarting — last proposal ({last_prop.get('venue', '?')} on "
                f"{last_prop.get('time', '?')}) was rejected by {rejected_summary}. "
                f"Agents will steer away from that this round."
            ),
            data={"prior_attempt": last},
        )

    window_label = (
        f"{window_from.strftime('%a %d %b')} → {window_until.strftime('%a %d %b')}"
    )

    await emit(
        negotiation_id,
        agent_name="orchestrator",
        role="info",
        content=f"Negotiating a {vibe or 'catch-up'} between "
        f"{len(members)} agents · window {window_label}",
    )

    contexts = [
        await _gather_user_context(m, window_from, window_until) for m in members
    ]

    # Visibility: surface how much we actually know about each agent so a
    # surprise "the slot conflicts with my real calendar" failure mode is
    # debuggable from the live SSE feed.
    for ctx in contexts:
        memory_count = len(ctx.get("memories") or [])
        busy_count = len(ctx.get("busy") or [])
        if busy_count == 0:
            cal_status = "no calendar connected"
        else:
            cal_status = f"{busy_count} busy slot{'s' if busy_count != 1 else ''} in window"
        await emit(
            negotiation_id,
            agent_name="orchestrator",
            role="info",
            content=(
                f"Loaded context for {ctx['name']}: {memory_count} "
                f"memories · {cal_status}."
            ),
            data={
                "user_id": ctx["user_id"],
                "memory_count": memory_count,
                "busy_count": busy_count,
            },
        )

    # ── Phase 1: multi-round slot negotiation ─────────────
    # Each agent gets up to MAX_SLOT_ROUNDS turns. After each round, we
    # check for unanimous overlap — if found, stop early. Otherwise keep
    # going so the agents can react to each other's positions.
    MAX_SLOT_ROUNDS = 3
    rounds: list[list[dict]] = []
    chosen_slot: str | None = None
    early_unanimous = False

    for round_num in range(MAX_SLOT_ROUNDS):
        if round_num > 0:
            await emit(
                negotiation_id,
                agent_name="orchestrator",
                role="info",
                content=f"Round {round_num + 1}: agents are reacting to each other.",
                data={"round": round_num},
            )

        round_proposals: list[dict] = []
        for ctx in contexts:
            memory_text = prompts.format_user_memories(ctx["memories"])
            calendar_text = ctx["calendar_text"]
            transcript = (
                prompts.format_prior_rounds_for_agent(rounds, my_name=ctx["name"])
                if rounds
                else ""
            )
            sys_p, user_p = prompts.slot_proposal_prompt(
                user_name=ctx["name"],
                memory_text=memory_text,
                calendar_text=calendar_text,
                window_label=window_label,
                vibe=vibe,
                other_names=_other_names(contexts, ctx),
                round_num=round_num,
                prior_transcript=transcript,
                prior_attempts_text=prompts.format_prior_attempts(prior_attempts),
            )
            try:
                result = await llm_client.chat_json(sys_p, user_p, temperature=0.6)
            except Exception as exc:
                logger.exception("Agent slot proposal failed for %s", ctx["name"])
                await emit(
                    negotiation_id,
                    agent_name=_agent_label(ctx["name"]),
                    role="error",
                    content=f"Agent could not respond: {exc}",
                )
                continue

            top_slots = [str(s) for s in (result.get("top_slots") or [])][:5]
            one_liner = str(result.get("one_liner") or "").strip()
            round_proposals.append(
                {"name": ctx["name"], "top_slots": top_slots, "one_liner": one_liner}
            )
            await emit(
                negotiation_id,
                agent_name=_agent_label(ctx["name"]),
                role="propose" if round_num == 0 else "react",
                content=one_liner or f"{ctx['name']} suggested: {', '.join(top_slots)}",
                data={"top_slots": top_slots, "round": round_num},
            )

        if not round_proposals:
            break
        rounds.append(round_proposals)

        # Stop early if everyone now shares at least one slot.
        unanimous = _find_unanimous_slot(round_proposals)
        if unanimous:
            chosen_slot = unanimous
            early_unanimous = True
            break

    if not rounds:
        await emit(
            negotiation_id, agent_name="orchestrator", role="error",
            content="No agent produced any slot proposal.",
        )
        _finished[negotiation_id] = True
        return {"proposal": None, "error": "no_slot_proposals"}

    # The summaries used downstream are the LATEST round's positions —
    # they're the most informed and reflect the agents' final compromises.
    slot_summaries: list[dict] = [
        {"name": p["name"], "top_slots": p["top_slots"]} for p in rounds[-1]
    ]

    # ── Orchestrator picks the slot ───────────────────────
    chosen_slot_iso: str | None = None
    duration_minutes: int = 120

    if not chosen_slot:
        sys_p, user_p = prompts.orchestrator_pick_slot_prompt(
            slot_summaries,
            window_from=window_from,
            window_until=window_until,
            vibe=vibe,
        )
        try:
            slot_pick = await llm_client.chat_json(sys_p, user_p, temperature=0.3)
        except Exception:
            logger.exception("Orchestrator slot pick failed")
            slot_pick = {
                "chosen_slot": slot_summaries[0]["top_slots"][0]
                if slot_summaries[0].get("top_slots") else "TBD",
                "reasoning": "Fallback to first agent's top choice.",
            }
        chosen_slot = str(slot_pick.get("chosen_slot") or "TBD")
        slot_reasoning = str(slot_pick.get("reasoning") or "")
        iso_raw = slot_pick.get("chosen_slot_iso")
        if iso_raw:
            chosen_slot_iso = str(iso_raw).strip() or None
        try:
            duration_minutes = int(slot_pick.get("duration_minutes") or 120)
        except (TypeError, ValueError):
            duration_minutes = 120
    else:
        slot_reasoning = "Everyone landed on this within the first round."
        # We have a unanimous human label but no LLM-derived ISO yet; ask
        # the orchestrator just for the ISO + duration to keep the
        # downstream calendar push lossless.
        sys_p, user_p = prompts.orchestrator_pick_slot_prompt(
            [{"name": "consensus", "top_slots": [chosen_slot]}],
            window_from=window_from,
            window_until=window_until,
            vibe=vibe,
        )
        try:
            extra = await llm_client.chat_json(sys_p, user_p, temperature=0.2)
            iso_raw = extra.get("chosen_slot_iso")
            if iso_raw:
                chosen_slot_iso = str(iso_raw).strip() or None
            duration_minutes = int(extra.get("duration_minutes") or 120)
        except Exception:
            logger.exception("Slot ISO resolution failed (non-fatal)")

    # Classify the consensus and surface compromises explicitly so the user
    # can see who's flexing — the orchestrator owns the trade-off.
    overlap_label, flexers = _slot_overlap_summary(slot_summaries, chosen_slot)
    if early_unanimous or overlap_label == "unanimous":
        consensus_msg = (
            f"Slot locked: {chosen_slot}. Everyone had this in their top picks."
        )
    elif overlap_label == "majority":
        names = ", ".join(flexers) or "one agent"
        consensus_msg = (
            f"Slot picked: {chosen_slot}. {names} is flexing here — wasn't in "
            f"their top 3, but they can make it work."
        )
    else:
        names = ", ".join(flexers) or "the group"
        consensus_msg = (
            f"No clean overlap after {len(rounds)} rounds — picking {chosen_slot} "
            f"as the closest match. {names} is making the biggest compromise."
        )

    await emit(
        negotiation_id,
        agent_name="orchestrator",
        role="info",
        content=f"{consensus_msg} {slot_reasoning}".strip(),
        data={
            "chosen_slot": chosen_slot,
            "consensus": overlap_label,
            "flexers": flexers,
            "rounds_used": len(rounds),
            "early_unanimous": early_unanimous,
        },
    )

    # ── Phase 2: venue criteria from each agent ───────────
    criteria_per_agent: list[dict] = []
    for ctx in contexts:
        memory_text = prompts.format_user_memories(ctx["memories"])
        sys_p, user_p = prompts.venue_criteria_prompt(
            user_name=ctx["name"],
            memory_text=memory_text,
            chosen_slot=chosen_slot,
            vibe=vibe,
        )
        try:
            crit = await llm_client.chat_json(sys_p, user_p, temperature=0.6)
        except Exception:
            logger.exception("Agent venue criteria failed for %s", ctx["name"])
            continue
        keywords = [str(k) for k in (crit.get("keywords") or [])][:6]
        neighborhood = str(crit.get("neighborhood") or "").strip()
        one_liner = str(crit.get("one_liner") or "").strip()
        criteria_per_agent.append(
            {"name": ctx["name"], "keywords": keywords, "neighborhood": neighborhood}
        )
        await emit(
            negotiation_id,
            agent_name=_agent_label(ctx["name"]),
            role="propose",
            content=one_liner or f"Looking for: {', '.join(keywords)}",
            data={"keywords": keywords, "neighborhood": neighborhood},
        )

    # Merge keywords + neighborhoods.
    all_keywords: list[str] = []
    all_neighborhoods: list[str] = []
    for c in criteria_per_agent:
        for k in c["keywords"]:
            if k.lower() not in {x.lower() for x in all_keywords}:
                all_keywords.append(k)
        if c["neighborhood"] and c["neighborhood"].lower() not in {
            x.lower() for x in all_neighborhoods
        }:
            all_neighborhoods.append(c["neighborhood"])

    query = " ".join(all_keywords[:6]) or (vibe or "casual dinner")
    location = " or ".join(all_neighborhoods[:2]) or default_location

    await emit(
        negotiation_id,
        agent_name="orchestrator",
        role="info",
        content=f"Searching Tavily: {query} · {location}",
        data={"query": query, "location": location},
    )

    venues_resp = search_venues(
        query=query, location=location, max_results=8, search_depth="advanced",
    )
    raw_results = venues_resp.get("venues") or []
    tavily_answer = venues_resp.get("answer") or ""

    venues = await _extract_real_venues(
        tavily_answer=tavily_answer,
        raw_results=raw_results,
        keywords=all_keywords,
        neighborhoods=all_neighborhoods,
        vibe=vibe,
        location=location,
    )

    if not venues:
        await emit(
            negotiation_id,
            agent_name="orchestrator",
            role="error",
            content=(
                "Couldn't pull clean venue candidates from the search. "
                "Falling back to a placeholder."
            ),
        )
        venues = [
            {
                "title": f"{(vibe or 'Catch-up').title()} venue · {location}",
                "snippet": "Venue to be confirmed.",
                "url": "",
            }
        ]

    titles_preview = ", ".join(v.get("title", "") for v in venues)
    await emit(
        negotiation_id,
        agent_name="orchestrator",
        role="info",
        content=f"Found {len(venues)} real options: {titles_preview}",
        data={"venues": venues},
    )

    # ── Phase 3: each agent ranks the candidates ──────────
    reactions: list[dict] = []
    for ctx in contexts:
        memory_text = prompts.format_user_memories(ctx["memories"])
        sys_p, user_p = prompts.venue_reaction_prompt(
            user_name=ctx["name"],
            memory_text=memory_text,
            chosen_slot=chosen_slot,
            venues=venues,
        )
        try:
            r = await llm_client.chat_json(sys_p, user_p, temperature=0.4)
        except Exception:
            logger.exception("Agent venue reaction failed for %s", ctx["name"])
            continue
        ranked = [int(i) for i in (r.get("ranked_indices") or []) if isinstance(i, (int, float))]
        # Dedup + keep only valid indices
        seen: set[int] = set()
        ranked_clean: list[int] = []
        for i in ranked:
            if 0 <= i < len(venues) and i not in seen:
                ranked_clean.append(i)
                seen.add(i)
        # Append any missing indices in their natural order so we always
        # have a full ranking for the orchestrator to aggregate.
        for i in range(len(venues)):
            if i not in seen:
                ranked_clean.append(i)
        reactions.append(
            {
                "name": ctx["name"],
                "ranked_indices": ranked_clean,
            }
        )
        await emit(
            negotiation_id,
            agent_name=_agent_label(ctx["name"]),
            role="react",
            content=str(r.get("one_liner") or "")
            or f"{ctx['name']} ranks: {ranked_clean}",
            data={"ranked_indices": ranked_clean},
        )

    # ── Orchestrator picks final venue ────────────────────
    chosen_index = 0
    justification = "Best overall fit."
    if reactions:
        # Quick deterministic aggregate as a sanity check + LLM call for the
        # justification one-liner.
        scores = [0.0] * len(venues)
        for r in reactions:
            for rank, idx in enumerate(r["ranked_indices"]):
                scores[idx] += rank
        chosen_index = scores.index(min(scores))

        try:
            sys_p, user_p = prompts.orchestrator_pick_venue_prompt(
                venues, reactions, chosen_slot
            )
            pick = await llm_client.chat_json(sys_p, user_p, temperature=0.3)
            llm_index = int(pick.get("chosen_index", chosen_index))
            if 0 <= llm_index < len(venues):
                chosen_index = llm_index
            justification = str(pick.get("justification") or justification)
        except Exception:
            logger.exception("Orchestrator venue pick failed (using deterministic)")

    chosen_venue = venues[chosen_index]
    venue_title = chosen_venue.get("title") or "Catch-up venue"

    # Defense: the LLM occasionally writes "Venue 0" / "[2]" instead of the
    # real name. Patch any such reference in-place using the actual title.
    import re
    justification = re.sub(
        r"\bVenue\s*\d+\b|\[\d+\]",
        venue_title,
        justification,
        flags=re.IGNORECASE,
    )

    # Surface a compromise note for the venue too, same logic as the slot.
    venue_label, sacrificers = _venue_compromise_summary(reactions, chosen_index)
    if venue_label == "unanimous_top1":
        venue_compromise_msg = "Unanimous first choice — everyone ranked it #1."
    elif venue_label == "majority_top_k":
        venue_compromise_msg = "All agents had it in their top 2 — strong consensus."
    else:
        names = ", ".join(sacrificers) or "one agent"
        venue_compromise_msg = (
            f"{names} would have preferred a different spot, but the rest of "
            f"the group leans here."
        )

    # The DB row only carries the columns we have in the proposals table.
    # Anything extra (consensus notes, raw venue snippet, …) lives in the
    # streamed event payload below.
    proposal_db_row: dict = {
        "venue": venue_title,
        "time": chosen_slot,
        "activity": vibe or "catch-up",
        "justification": justification,
    }
    if chosen_slot_iso:
        proposal_db_row["start_at"] = chosen_slot_iso
    if duration_minutes:
        proposal_db_row["duration_minutes"] = duration_minutes
    proposal_payload = {
        **proposal_db_row,
        "consensus_note": venue_compromise_msg,
    }

    try:
        await db.save_proposal(catchup_id, proposal_db_row)
        await db.update_catchup_status(catchup_id, "proposed")
    except Exception:
        logger.exception("Failed to persist proposal")

    await emit(
        negotiation_id,
        agent_name="orchestrator",
        role="info",
        content=venue_compromise_msg,
        data={
            "venue_consensus": venue_label,
            "sacrificers": sacrificers,
        },
    )

    await emit(
        negotiation_id,
        agent_name="orchestrator",
        role="propose",
        content=f"Proposal locked: {venue_title} · {chosen_slot}. {justification}",
        data={"proposal": proposal_payload, "venue": chosen_venue},
    )

    await emit(
        negotiation_id,
        agent_name="system",
        role="done",
        content="Negotiation done.",
        data={"proposal": proposal_payload},
    )
    _finished[negotiation_id] = True
    return {"proposal": proposal_payload}
