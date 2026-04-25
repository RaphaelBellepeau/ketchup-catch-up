"""Voice task definitions for Gradbot sessions."""

from dataclasses import dataclass, field


@dataclass
class VoiceTask:
    """Configuration for a Gradbot voice session."""

    task_type: str  # "onboarding" | "feedback"
    user_id: str
    system_prompt: str
    output_schema: str  # JSON Schema string for the save_result tool
    context: dict = field(default_factory=dict)
    voice_id: str = "X8-_I8yFvYONny54"  # Default Gradium voice
    language: str = "fr"


@dataclass
class VoiceTaskResult:
    """Result returned by VoiceService after a completed session."""

    task_type: str
    user_id: str
    extracted_data: dict
    success: bool


# ── Task configs ────────────────────────────────────────

ONBOARDING_SCHEMA = """{
    "type": "object",
    "properties": {
        "cuisines_liked": {"type": "array", "items": {"type": "string"}},
        "cuisines_disliked": {"type": "array", "items": {"type": "string"}},
        "budget_range": {"type": "string", "enum": ["low", "medium", "high"]},
        "preferred_areas": {"type": "array", "items": {"type": "string"}},
        "preferred_days": {"type": "array", "items": {"type": "string"}},
        "dietary_constraints": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["cuisines_liked", "budget_range"]
}"""

FEEDBACK_SCHEMA = """{
    "type": "object",
    "properties": {
        "rating": {"type": "integer", "minimum": 1, "maximum": 5},
        "liked": {"type": "array", "items": {"type": "string"}},
        "disliked": {"type": "array", "items": {"type": "string"}},
        "would_repeat": {"type": "boolean"},
        "free_comment": {"type": "string"}
    },
    "required": ["rating"]
}"""


def build_task(task_type: str, user_id: str, **kwargs) -> VoiceTask:
    """Factory to create a VoiceTask from a task type."""
    if task_type == "onboarding":
        return VoiceTask(
            task_type="onboarding",
            user_id=user_id,
            system_prompt="""Tu es l'assistant vocal de Catch-Up, une app pour organiser des sorties entre amis.
Tu accueilles un nouvel utilisateur chaleureusement et tu lui poses des questions pour apprendre ses préférences.

Pose ces questions naturellement dans la conversation (pas comme un formulaire) :
- Quels types de cuisine il aime et n'aime pas
- Son budget habituel pour une sortie (petit / moyen / gros)
- Ses quartiers préférés pour sortir
- Ses jours/moments préférés pour voir ses amis
- Des contraintes alimentaires éventuelles (végétarien, allergies, etc.)

Quand tu as suffisamment d'infos, appelle l'outil save_result avec les données structurées.
Sois naturel, enthousiaste, et bref. Tu parles en français.""",
            output_schema=ONBOARDING_SCHEMA,
            context=kwargs.get("context", {}),
        )
    elif task_type == "feedback":
        return VoiceTask(
            task_type="feedback",
            user_id=user_id,
            system_prompt="""Tu es l'assistant vocal de Catch-Up.
La sortie vient de se terminer. Demande à l'utilisateur comment ça s'est passé.

Pose ces questions naturellement :
- C'était bien ? (note de 1 à 5)
- Qu'est-ce qu'il a aimé ?
- Qu'est-ce qu'il changerait ?
- Est-ce qu'il referait la même sortie ?

Quand tu as assez d'infos, appelle l'outil save_result.
Sois chaleureux et bref. Tu parles en français.""",
            output_schema=FEEDBACK_SCHEMA,
            context=kwargs.get("context", {}),
        )
    else:
        raise ValueError(f"Unknown task type: {task_type}")
