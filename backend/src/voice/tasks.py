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
        "liked": {
            "type": "string",
            "description": "Comma-separated list of things the user enjoyed.",
        },
        "disliked": {
            "type": "string",
            "description": "Comma-separated list of things the user disliked or would change.",
        },
        "would_repeat": {
            "type": "boolean",
            "description": "Whether the user would do this outing again.",
        },
        "free_comment": {
            "type": "string",
            "description": "Any free-form comment from the user.",
        },
    },
    "required": ["rating"],
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

FEEDBACK_PROMPT = """You are the Catch-Up voice assistant. The user just got back from an outing planned by the app, and you want a quick honest debrief.

Cover these one at a time, casually:
1. How was it? (rating 1 to 5)
2. What was the best part?
3. Anything you'd change next time?
4. Would you do it again?

When you have at least the rating, call save_result.

CRITICAL RULES:
- Keep ALL your responses to 1-2 SHORT sentences. This is voice.
- One question at a time.
- Be warm and quick — under 90 seconds total ideally.
- Speak in English."""


def build_task(task_type: str, user_id: str, **kwargs) -> VoiceTask:
    """Factory to create a VoiceTask from a task type."""
    if task_type == "onboarding":
        return VoiceTask(
            task_type="onboarding",
            user_id=user_id,
            system_prompt=ONBOARDING_PROMPT,
            output_schema=ONBOARDING_SCHEMA,
            context=kwargs.get("context", {}),
        )
    if task_type == "feedback":
        return VoiceTask(
            task_type="feedback",
            user_id=user_id,
            system_prompt=FEEDBACK_PROMPT,
            output_schema=FEEDBACK_SCHEMA,
            context=kwargs.get("context", {}),
        )
    raise ValueError(f"Unknown voice task type: {task_type}")
