"""Prompt builders for the negotiation agents and orchestrator.

Each user agent only ever sees its OWN user's data (memories + busy slots).
The orchestrator only ever sees agents' STRUCTURED proposals, never raw
calendars or memories — privacy by separation, not just instruction.
"""

from datetime import date


def format_user_memories(memories: list[dict]) -> str:
    """Turn `[{scope, content, source}]` into prompt-ready bullet lines."""
    if not memories:
        return "(no memories yet)"
    return "\n".join(f"- {m['content']}" for m in memories if m.get("content"))


def format_busy_slots(busy: list[dict]) -> str:
    """Legacy raw-ISO bullet list. Kept for backwards compat — prefer the
    day-by-day natural-language calendar from `format_calendar_view` in
    `tools/calendar_tool.py`, which is what the new prompt path uses.
    """
    if not busy:
        return "(calendar not connected — rely on the user's stated commitments above)"
    lines = []
    for b in busy[:20]:
        lines.append(f"- {b.get('start')} → {b.get('end')}")
    return "\n".join(lines)


_AGENT_ADVOCACY_RULES = """
YOUR ROLE — read this before every reply:

You are {user_name}'s personal AI advocate. Your loyalty is to {user_name},
NOT to the group. Other agents are advocating for their own users; if their
proposal hurts {user_name}'s comfort, schedule, energy, or interests — push
back politely.

PRIVACY (HARD RULES — never break):
- NEVER quote {user_name}'s memories verbatim. Always paraphrase.
- NEVER reveal exact calendar slots — say "free Thursday after 8pm",
  not "yoga 7-9pm Tue/Thu".
- NEVER expose sensitive details: health, money, relationships, who they
  live with, work projects under NDA, therapy, or anything that feels
  personal. If a memory hints at one of these, leave it out.
- NEVER name the OTHER PEOPLE involved in {user_name}'s commitments
  (e.g. say "blocked Saturday morning", not "kids' football match").
- Share only the minimum the group needs to converge on a plan.

ADVOCACY:
- Treat {user_name}'s stated weekly commitments and recurring blocks as
  hard constraints — never propose a slot that breaks them.
- Refuse slots that are obviously bad for {user_name} (right before/after
  a known important event, very early after a late night out, etc.).
  Frame the refusal in vague terms — "tough morning that day for them".
- When proposing, lead with what {user_name} actively WANTS, not just
  what's available.
- It's fine to compromise — but make it visible: "Tuesday isn't ideal,
  but Léa can stretch if it's after 8".
"""


def format_prior_attempts(prior_attempts: list[dict]) -> str:
    """Render previously-rejected proposals as a "lessons learned" block
    that gets injected into every agent's system prompt on retries.
    """
    if not prior_attempts:
        return ""
    lines: list[str] = []
    lines.append("\nPRIOR ATTEMPTS THAT WERE REJECTED — DO NOT REPEAT:")
    for i, att in enumerate(prior_attempts, start=1):
        prop = att.get("proposal") or {}
        slot = prop.get("time") or "?"
        venue = prop.get("venue") or "?"
        activity = prop.get("activity") or ""
        header = f"  Attempt {i}: {activity or 'catch-up'} on {slot} at {venue}"
        lines.append(header)
        for rej in att.get("rejections") or []:
            who = rej.get("by") or "Someone"
            why = (rej.get("reason") or "no reason given").strip() or "no reason given"
            lines.append(f"    ↳ {who} rejected — reason: {why}")
    lines.append(
        "Avoid the failure mode that triggered each rejection. If the "
        "reason was 'too expensive', steer cheaper this time. If 'wrong "
        "place', drop that neighbourhood/venue family. If 'wrong day', "
        "pick a different day-of-week. Don't propose the exact same slot "
        "or venue again."
    )
    return "\n".join(lines)


def format_prior_rounds_for_agent(
    rounds: list[list[dict]], my_name: str
) -> str:
    """Build a readable transcript of what's been proposed so far, with
    the agent's own past turns marked, so they can react instead of
    repeating themselves.
    """
    if not rounds:
        return "(this is the opening round — no one has spoken yet)"
    lines: list[str] = []
    for r_idx, round_msgs in enumerate(rounds):
        lines.append(f"-- Round {r_idx + 1} --")
        for m in round_msgs:
            label = "you" if m["name"] == my_name else f"{m['name']}'s agent"
            slots = ", ".join(m.get("top_slots") or [])
            one = (m.get("one_liner") or "").strip()
            if one:
                lines.append(f"  {label}: \"{one}\"  (top slots: {slots})")
            else:
                lines.append(f"  {label} top slots: {slots}")
    return "\n".join(lines)


def slot_proposal_prompt(
    user_name: str,
    memory_text: str,
    calendar_text: str,
    window_label: str,
    vibe: str,
    other_names: list[str],
    round_num: int = 0,
    prior_transcript: str = "",
    prior_attempts_text: str = "",
) -> tuple[str, str]:
    """System+user pair for round 1: each agent proposes top-3 candidate slots.

    Returns the JSON shape the agent must emit:
        {"top_slots": ["Thu 2 May, 8pm", ...],
         "one_liner": "Léa's free Thursday after 8 — yoga blocks Tue/Thu earlier."}
    """
    others = ", ".join(other_names) or "the group"
    rules = _AGENT_ADVOCACY_RULES.format(user_name=user_name)
    transcript_section = (
        f"\n\nWHAT'S BEEN PROPOSED SO FAR (round {round_num + 1}):\n{prior_transcript}\n"
        if prior_transcript
        else ""
    )
    prior_attempts_section = (
        f"\n{prior_attempts_text}\n" if prior_attempts_text else ""
    )
    round_guidance = _slot_round_guidance(round_num)

    system = f"""You are {user_name}'s personal AI agent in Catch-Up's group negotiation.

What you know about {user_name}:
{memory_text}

{user_name}'s calendar across the meet-up window (private — paraphrase only,
NEVER quote exact slots back to the group):
{calendar_text}

The group is negotiating a {vibe or "catch-up"} during {window_label}.
You are talking with: {others}.{prior_attempts_section}{transcript_section}
{rules}
TASK SPECIFICS:
- Propose slots that fit inside the window AND respect every block above.
- AVOID slots that fall right before something important to {user_name}
  (e.g. the night before a known big morning, a tight evening if there's
  an early commitment the next day). Just don't propose those.
- Order by preference (best first). Provide exactly 3.
- Always reply with VALID JSON matching the schema below — no prose around it.
{round_guidance}"""

    user = """Respond ONLY with JSON in this exact shape:

{
  "top_slots": ["<slot 1>", "<slot 2>", "<slot 3>"],
  "one_liner": "<one short sentence in your agent's voice, max 25 words — react to what the others said if it's a follow-up round>"
}

Each slot must be a human-readable string like "Thursday 2 May, 8pm" or "Saturday afternoon" that fits inside the window. Order them by preference (best first).

Examples of one_liner style (never names the actual conflict):
  Round 1:  "Léa's free Thursday after 8 or Saturday lunch — Tuesday's locked."
  Round 2:  "Saturday lunch overlaps with everyone — Léa locks that in."
  Round 3:  "Léa would rather flex to Sunday afternoon than push Saturday late."
"""
    return system, user


def _slot_round_guidance(round_num: int) -> str:
    """Tone hint per round so the agent's reply feels conversational, not a form."""
    if round_num == 0:
        return (
            "ROUND TONE: this is your opening — propose freely without "
            "knowing what others want yet."
        )
    if round_num == 1:
        return (
            "ROUND TONE: you've now seen the others' first picks. Look for "
            "OVERLAP. If you can move toward someone else's slot without "
            "violating a hard block, do it. Don't just repeat round 1."
        )
    return (
        "ROUND TONE: this is the LAST round before the orchestrator decides. "
        "Be flexible — propose your best compromise even if it's not your "
        "favorite. Or strongly defend a hard block if the group is heading "
        "toward an impossible slot."
    )


def venue_criteria_prompt(
    user_name: str,
    memory_text: str,
    chosen_slot: str,
    vibe: str,
) -> tuple[str, str]:
    """System+user pair for round 2: each agent suggests venue criteria.

    Returns:
        {"keywords": ["italian", "11th arr", "small group"],
         "one_liner": "Léa would love a small Italian spot in the 11th, low-key."}
    """
    rules = _AGENT_ADVOCACY_RULES.format(user_name=user_name)
    system = f"""You are {user_name}'s personal AI agent. The group has agreed on a slot: {chosen_slot}.

What you know about {user_name}:
{memory_text}
{rules}
TASK: propose venue/activity criteria for this {vibe or "catch-up"}. Translate {user_name}'s preferences into 3-5 short search keywords and a one-sentence summary in {user_name}'s voice.

OUTPUT RULES:
- Don't quote raw memories. Keywords are derived/general (e.g. "small italian", "quiet bistro"), never sensitive (no names, no addresses).
- Skip neighborhood if it would feel like exposing a home address — keep it broad ("Paris east side" rather than "rue X").
- Reply with VALID JSON only — no prose around it."""
    user = """Respond ONLY with JSON in this exact shape:

{
  "keywords": ["<keyword>", "<keyword>", "<keyword>"],
  "neighborhood": "<optional area/city, e.g. 'Paris 11th', or empty string>",
  "one_liner": "<one short sentence about what {name} would love, max 25 words>"
}

Keywords should be venue search terms. Examples:
  ["small italian", "quiet bistro", "low-key", "11th arrondissement"]
  ["natural wine", "lively", "late dinner"]
"""
    return system, user


def venue_reaction_prompt(
    user_name: str,
    memory_text: str,
    chosen_slot: str,
    venues: list[dict],
) -> tuple[str, str]:
    """System+user pair for round 3: each agent ranks the candidate venues.

    Returns:
        {"ranked_indices": [2, 0, 1],
         "one_liner": "Léa picks Le Servan — quiet, in the 11th, perfect for Thursday night."}
    """
    venue_list = "\n".join(
        f"  [{i}] {v.get('title', '')} — {v.get('snippet', '')[:140]}"
        for i, v in enumerate(venues)
    )
    rules = _AGENT_ADVOCACY_RULES.format(user_name=user_name)
    system = f"""You are {user_name}'s personal AI agent. The group is at the venue-picking stage for {chosen_slot}.

What you know about {user_name}:
{memory_text}
{rules}
TASK: rank the candidate venues below from best to worst FOR {user_name}, then write one short sentence in your agent's voice about the top pick.

CANDIDATE VENUES:
{venue_list}

OUTPUT RULES:
- Refer to the venue by its title, not its index.
- Don't quote sensitive memories — paraphrase the reason ("quiet enough for Léa", not "she's been anxious lately").
- Output VALID JSON only."""
    user = """Respond ONLY with JSON:

{
  "ranked_indices": [<int>, <int>, ...],
  "one_liner": "<one short sentence, max 20 words>"
}

ranked_indices is a permutation of [0..N-1] — best first.
"""
    return system, user


def venue_extraction_prompt(
    *,
    tavily_answer: str,
    tavily_results: list[dict],
    keywords: list[str],
    neighborhoods: list[str],
    vibe: str,
    max_venues: int = 4,
) -> tuple[str, str]:
    """Ask the LLM to extract REAL specific venues mentioned by name in
    the Tavily blob (which is mostly listicles like "Top 10 X in Paris").

    Output shape:
        {
          "venues": [
            {
              "name": "Le Servan",
              "description": "Modern French bistro in the 11th, natural wine.",
              "why_fits": "Quiet enough to talk; matches the cozy criteria.",
              "source_url": "https://...timeout.com/..."
            },
            ...
          ]
        }
    """
    results_block = "\n".join(
        f"  [{i}] {r.get('title', '')}\n      url: {r.get('url', '')}\n      snippet: {r.get('snippet', '')}"
        for i, r in enumerate(tavily_results[:8])
    ) or "  (no raw results)"

    answer_block = (tavily_answer or "").strip() or "(no synthesized answer)"

    system = """You extract real specific venues (restaurants, bars, activity
spots) mentioned BY NAME in noisy web search results. Most search results are
listicles ("Top 10 …"), reviews, or blog posts that list multiple venues; you
must pull out the actual venue names so a group of friends can choose one.

Hard rules:
- NEVER invent a venue. If a name doesn't appear in the results below, don't include it.
- NEVER return listicle titles like "Top 10 best Italian restaurants in Paris" or "Best 25 places…" as a venue. Those are articles, not venues.
- Prefer venues that match the group's keywords and neighborhood.
- Quality over quantity: 2 great picks > 4 vague ones.
- Reply with VALID JSON only — no prose around it."""

    user = f"""Group's criteria:
- vibe: {vibe or "catch-up"}
- keywords: {", ".join(keywords) or "(none)"}
- preferred neighborhoods: {", ".join(neighborhoods) or "(none)"}

Search engine answer:
{answer_block}

Raw search results:
{results_block}

Pick up to {max_venues} REAL specific venues that appear by name in the results above.

Respond ONLY with JSON:

{{
  "venues": [
    {{
      "name": "<actual venue name>",
      "description": "<one short sentence about it>",
      "why_fits": "<one short reason it matches the criteria>",
      "source_url": "<exact URL from one of the raw results above, or empty string>"
    }}
  ]
}}
"""
    return system, user


def orchestrator_pick_slot_prompt(
    slot_summaries: list[dict],
    window_from: date | str | None = None,
    window_until: date | str | None = None,
    vibe: str = "",
) -> tuple[str, str]:
    """Pick the slot that best satisfies all agents' top-K lists, and resolve
    it to a structured ISO datetime so we can push it to Google Calendar
    after acceptance.
    """
    summary_lines = [
        f"  {s['name']}: {', '.join(s['top_slots'])}" for s in slot_summaries
    ]
    summary = "\n".join(summary_lines)

    window_label = ""
    if window_from is not None and window_until is not None:
        wf = window_from.strftime("%a %d %b %Y") if hasattr(window_from, "strftime") else str(window_from)
        wu = window_until.strftime("%a %d %b %Y") if hasattr(window_until, "strftime") else str(window_until)
        window_label = f"\nThe meet-up window is {wf} → {wu}.\n"

    duration_hint = "120"  # dinner default
    vlow = (vibe or "").lower()
    if "drink" in vlow:
        duration_hint = "90"
    elif "brunch" in vlow or "lunch" in vlow:
        duration_hint = "90"
    elif "activity" in vlow or "movie" in vlow or "game" in vlow:
        duration_hint = "180"

    system = """You are the orchestrator of a group meet-up negotiation. You
ONLY see each agent's top-3 proposed slots — never raw calendars. Pick the
single best slot that maximizes consensus, preferring slots that appear in
multiple agents' lists, with weight to higher positions.

If no slot overlaps, pick the one closest to a majority match.

Resolve the picked slot to a CONCRETE datetime within the window. When the
agents say "Thursday evening" pick a sensible default (19:30 dinner, 18:30
drinks, 11:00 brunch). Default timezone is Europe/Paris unless context
implies otherwise.

Reply with VALID JSON only."""

    user = f"""Each agent's top-3 slots (best first):
{summary}
{window_label}
Respond ONLY with JSON:

{{
  "chosen_slot": "<human-readable label, e.g. 'Thursday 7 May, 8pm'>",
  "chosen_slot_iso": "<ISO 8601 with offset, e.g. '2026-05-07T20:00:00+02:00'>",
  "duration_minutes": <integer, typically {duration_hint}>,
  "reasoning": "<one short sentence explaining why this one, max 25 words>"
}}
"""
    return system, user


def orchestrator_pick_venue_prompt(
    venues: list[dict], reactions: list[dict], chosen_slot: str
) -> tuple[str, str]:
    """Aggregate per-agent rankings into a single chosen venue."""
    venue_list = "\n".join(
        f"  [{i}] {v.get('title', '')} — {v.get('snippet', '')[:120]}"
        for i, v in enumerate(venues)
    )
    reactions_text = "\n".join(
        f"  {r['name']} ranks: {r.get('ranked_indices')}" for r in reactions
    )
    system = """You are the orchestrator. Aggregate each agent's ranking of
the venue options and pick the single venue that maximizes group satisfaction
(low average rank wins). Reply with VALID JSON only.

When writing the justification, refer to the venue by its TITLE (e.g. "Le
Servan", "Ober Mamma") — never by its index ("Venue 0", "[2]"). The
justification will be shown to end users on the proposal screen."""
    user = f"""Slot: {chosen_slot}

Candidate venues:
{venue_list}

Agent rankings (lower index = better):
{reactions_text}

Respond ONLY with JSON:

{{
  "chosen_index": <int>,
  "justification": "<one short sentence using the venue's actual name (NOT the index), max 30 words>"
}}
"""
    return system, user
