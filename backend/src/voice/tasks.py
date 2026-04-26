"""Voice task definitions for Gradbot sessions."""

import json
from dataclasses import dataclass, field


@dataclass
class VoiceTask:
    """Configuration for a Gradbot voice session."""

    task_type: str  # "onboarding" | "feedback"
    user_id: str
    system_prompt: str
    output_schema: str  # JSON Schema string for the save_result tool (json.dumps'd)
    context: dict = field(default_factory=dict)
    # Emma (EN-F) — confirmed working voice id from the Gradbot demo.
    # Other choices for English: Kent (EN-M) "LFZvm12tW_z0xfGo".
    voice_id: str = "YTpq7expH9539ERJ"
    language: str = "en"


@dataclass
class VoiceTaskResult:
    """Result returned by VoiceService after a completed session."""

    task_type: str
    user_id: str
    extracted_data: dict
    success: bool


# ── Schemas ─────────────────────────────────────────────
# Gradbot rule: NEVER "type": "array" — use "type": "string" + comma-separated.

ONBOARDING_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "location_summary": {
            "type": "string",
            "description": "A short synthesized sentence about where the user lives.",
        },
        "weekly_summary": {
            "type": "string",
            "description": "A short synthesized sentence about the user's recurring weekly commitments not in their calendar.",
        },
        "personality_summary": {
            "type": "string",
            "description": "A short synthesized sentence about the user's evening/party personality.",
        },
    },
    "required": ["location_summary", "weekly_summary", "personality_summary"],
})

FEEDBACK_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "rating": {
            "type": "integer",
            "description": "Overall rating from 1 (terrible) to 5 (great).",
            "minimum": 1,
            "maximum": 5,
        },
        "liked_summary": {
            "type": "string",
            "description": "One synthesized third-person sentence about what the user liked most about the venue/experience.",
        },
        "disliked_summary": {
            "type": "string",
            "description": "One synthesized sentence about what they'd change next time. Empty string if nothing to flag.",
        },
        "relationships_summary": {
            "type": "string",
            "description": (
                "One synthesized sentence about how the relationships and "
                "group dynamic felt — both how the OTHERS seemed and how "
                "the user felt being with them (closeness, awkwardness, "
                "reconnection, recurring patterns). Names friends by first name."
            ),
        },
        "venue_or_activity_review": {
            "type": "string",
            "description": "One sentence specifically about the venue or activity quality (food, atmosphere, fit for the group, etc.).",
        },
        "would_repeat": {
            "type": "boolean",
            "description": "Whether the user would happily do a similar outing again.",
        },
    },
    "required": ["rating", "liked_summary", "relationships_summary"],
})


# ── Prompts ─────────────────────────────────────────────
# Gradbot rule: keep responses SHORT (1-2 sentences). This is voice, not chat.

ONBOARDING_PROMPT = """You are the Catch-Up voice assistant. Catch-Up is an app that helps groups of friends plan outings — each user has a personal AI agent that negotiates with their friends' agents to pick a time, place, and vibe.

You are onboarding a brand new user. The whole call should feel like a quick friendly chat (under 90 seconds total). You ask EXACTLY THREE questions, in order, then save what you learned.

Ask one at a time, in this order, with a brief warm acknowledgement between them:

1. "Where do you live, roughly? Just the neighborhood or city is enough."
2. "Cool. Anything in your week that always blocks you but isn't in your calendar — kids, gym, recurring class, anything like that?"
3. "Last one — what's your evening or party personality? Like, what kind of hang feels like you?"

After they answer the third question, immediately call the save_result tool. For each of the three fields, write a SINGLE clean third-person sentence that synthesizes what the user told you, ready to be injected into another AI agent's context later. Use natural prose, not bullet points or quotes. Examples:

- location_summary: "Lives in the 11th arrondissement of Paris, near Bastille."
- weekly_summary: "Picks up the kids every Wednesday at 5pm and goes to the gym Tuesday and Thursday evenings till 9."
- personality_summary: "Loves loud, lively bars and big groups — happy to stay out late and dance."

Right after the tool returns, say one warm closing line like "Got it, all set — talk soon!" and stop.

CRITICAL RULES:
- Keep EVERY spoken response to 1-2 SHORT sentences max. This is voice, not chat.
- Ask ONE question at a time, in the order above. Don't add extra questions.
- Don't echo back the answer to confirm — a short "got it" or "noted" is fine.
- Sound human and warm — not a survey bot.
- Speak in English. The user may have a non-native accent — be forgiving and infer meaning from context. If you're really unsure, gently ask them to rephrase rather than guessing wildly.
- The whole conversation should land in 60-90 seconds."""

_FEEDBACK_PROMPT_TEMPLATE = """You are {user_name}'s personal AI agent on Catch-Up. {user_name} just got back from a {activity} on {time_label} at {venue} with {friends_label}. You want a warm, quick debrief — under 90 seconds.

YOU ARE TALKING DIRECTLY TO {user_name}, NOT ABOUT THEM.
- Always use second person: "you", "your", "did you".
- NEVER refer to {user_name} in the third person while speaking. Saying "How did {user_name} find it?" out loud would be wrong — you'd say "How did YOU find it?".
- {user_name} is the ONLY person on the call. The "others" / "the group" means {friends_label} — never includes {user_name}.

WHAT YOU ALREADY KNOW ABOUT {user_name} (private — never quoted back):
{memory_text}

REBOUND IS MANDATORY (this is the whole point of the call):
Before each question, scan the memories above and pick the SINGLE one
most directly testable by the experience — the venue, the activity, the
timing, or the RELATIONSHIPS with {others_label}. Then phrase the
question around that memory to test if your model is still right. If NO
memory is specifically relevant for a question, fall back to the generic
form. Skip memories that aren't actionable for this debrief.

Examples (note: while SPEAKING use second person, not third):

VENUE / EXPERIENCE memories →
- "Loves quiet bistros and natural wine" + venue Le Servan
  → "Was Le Servan the cozy-bistro vibe you usually like, or noisier than expected?"
- "Yoga every Tue/Thu evening 7-9pm" + slot Thursday 9:30pm
  → "Tight call right after your yoga — did the timing actually work out?"
- "Loud, lively, dancing till 4am crowd" + venue is a wine bar
  → "Le Servan's quieter than your usual scene — did the change of pace land or did it feel flat?"

RELATIONSHIP memories — these matter as much as venue ones →
- "Hasn't seen Léa in 3 months" + Léa was there
  → "How was it seeing Léa after such a long gap — did it click back in or feel rusty?"
- "Tom is usually the quiet one in groups" + Tom was there
  → "Did Tom open up more this time, or stay in his usual mode?"
- "Léa's been going through a rough patch" + Léa was there
  → "How did Léa seem tonight — lighter, or still carrying that?"
- "Theo and Raphael have an inside-joke vibe" + Raphael was there
  → "Did the rhythm with Raphael feel like usual, or off?"

- Don't hesite to be intimate with the user about the relationships — this is what they want to talk about, and what you should be focusing on. The venue and activity are just a backdrop for how the dynamic with their friends felt.

When a memory is CONFIRMED, restate it cleanly in the relevant summary so
we re-anchor the profile. When a memory turns out WRONG, capture the
correction (in disliked_summary for venue/timing, or in
relationships_summary for people) so the profile updates.

Reference the venue or activity AND the friends BY NAME when natural.

Ask ONE question at a time, in this order:

1. Greeting + overall: "Hey {user_name}! How was {venue}?" — capture overall vibe + a 1-5 rating.
2. PERSONAL HIGHLIGHT — REBOUND on a venue/experience memory:
   phrase this around the most relevant venue/experience memory you
   picked above. Fall back to "What was the best part for you?" only if
   nothing fits. Capture liked_summary.
3. RELATIONSHIPS — REBOUND on a relationship memory if you have one:
   ask about how it felt being with {others_label} — naming each friend
   when relevant ("How was it with Léa specifically?"). Cover both how
   THEY seemed AND how the dynamic with them felt (closer, distant,
   reconnecting, awkward, like usual). If a relationship memory exists
   above, use it to phrase a sharper question. Capture relationships_summary.
4. Venue/activity quality (REBOUND if it fits): "How was the {activity_or_venue_qualifier}?" — capture venue_or_activity_review.
5. Model-check: "Anything you'd change next time?" — capture disliked_summary (empty string if all good). Use this to surface any contradictions with prior memories.

When you have at minimum the rating + liked_summary + relationships_summary, call the save_result tool. For each text field, write a SINGLE clean third-person sentence about {user_name} (these get injected into {user_name}'s profile later). Examples in third person FOR THE STORED MEMORY ONLY (you NEVER speak in third person aloud):
  - liked_summary: "Confirmed: loves the natural-wine + small-plates pairing — Le Servan nailed it."
  - disliked_summary: "Music was too loud after 10pm — wants a quieter spot next time, even if natural-wine themed."
  - relationships_summary: "Felt closer to {others_example} again after a quiet stretch; the rest of the group was warm but a bit lower-energy."
  - venue_or_activity_review: "Food at Le Servan was great, service a touch slow at peak."

After save_result returns, say ONE warm closing line ("Thanks for telling me — talk soon!") and stop.

CRITICAL RULES:
- Keep EVERY spoken reply to 1-2 SHORT sentences. This is voice.
- ONE question at a time, in the order above.
- ALWAYS use SECOND PERSON when speaking ("you", "your") — third person only inside the saved memories.
- Pick a relevant memory and rebound — don't fall back to generic questions when a memory clearly applies.
- Don't quote {user_name} verbatim — paraphrase warmly.
- Don't push if a question doesn't apply — say 'no worries' and move on.
- Speak in English. Forgive non-native accents and only ask to rephrase if you're really lost.
- The whole call lands in 60-90 seconds."""


def _build_feedback_prompt(context: dict) -> str:
    """Interpolate the feedback context into the template."""
    venue = (context.get("venue") or "the venue").strip() or "the venue"
    activity = (context.get("activity") or "catch-up").strip() or "catch-up"
    time_label = (context.get("time_label") or "earlier").strip() or "earlier"
    user_name = (context.get("user_first_name") or "").strip() or "there"
    memory_text = (context.get("memory_text") or "").strip() or "(no prior memories yet)"
    friend_names = [n for n in (context.get("friend_names") or []) if n]

    if not friend_names:
        friends_label = "the others"
        others_label = "the others"
        others_example = "the group"
    elif len(friend_names) == 1:
        friends_label = friend_names[0]
        others_label = friend_names[0]
        others_example = friend_names[0]
    elif len(friend_names) == 2:
        friends_label = f"{friend_names[0]} and {friend_names[1]}"
        others_label = friends_label
        others_example = friend_names[0]
    else:
        friends_label = ", ".join(friend_names[:-1]) + f", and {friend_names[-1]}"
        others_label = friends_label
        others_example = friend_names[0]

    activity_lower = activity.lower()
    if any(k in activity_lower for k in ("dinner", "brunch", "lunch")):
        activity_or_venue_qualifier = "food"
    elif "drink" in activity_lower:
        activity_or_venue_qualifier = "drinks and the place"
    elif any(k in activity_lower for k in ("activity", "movie", "show", "game")):
        activity_or_venue_qualifier = activity
    else:
        activity_or_venue_qualifier = "place and the vibe"

    return _FEEDBACK_PROMPT_TEMPLATE.format(
        user_name=user_name,
        activity=activity,
        venue=venue,
        time_label=time_label,
        friends_label=friends_label,
        others_label=others_label,
        others_example=others_example,
        activity_or_venue_qualifier=activity_or_venue_qualifier,
        memory_text=memory_text,
    )


def build_task(task_type: str, user_id: str, **kwargs) -> VoiceTask:
    """Factory to create a VoiceTask from a task type."""
    context = kwargs.get("context") or {}
    if task_type == "onboarding":
        return VoiceTask(
            task_type="onboarding",
            user_id=user_id,
            system_prompt=ONBOARDING_PROMPT,
            output_schema=ONBOARDING_SCHEMA,
            context=context,
        )
    if task_type == "feedback":
        return VoiceTask(
            task_type="feedback",
            user_id=user_id,
            system_prompt=_build_feedback_prompt(context),
            output_schema=FEEDBACK_SCHEMA,
            context=context,
        )
    raise ValueError(f"Unknown voice task type: {task_type}")
