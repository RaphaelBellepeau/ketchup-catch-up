"""System prompts for user agents with memory/preference injection."""


def build_agent_prompt(
    user_name: str,
    preferences: dict,
    history: list[dict] | None = None,
    catchup_context: dict | None = None,
    calendar_context: str = "",
) -> str:
    """Build a personalized system prompt for a user's agent.

    Args:
        user_name: Display name of the user.
        preferences: User preferences dict (cuisines, budget, areas, etc.)
        history: Recent feedbacks/past catchups for context.
        catchup_context: Current catchup params (vibe, time_window, etc.)
        calendar_context: Natural-language schedule summary for the next 2 weeks.
            Injected directly so the agent can defend availability without
            exposing raw calendar data. Populated by gcal_client.get_calendar_context().
    """
    prefs_text = _format_preferences(preferences)
    history_text = _format_history(history or [])
    context_text = _format_catchup_context(catchup_context or {})
    calendar_text = calendar_context or (
        "Calendrier non synchronisé. Défends des créneaux génériques "
        "(soirées en semaine après 20h, week-ends)."
    )

    return f"""Tu es l'agent IA personnel de {user_name} sur Catch-Up.

## Ton rôle
Tu représentes {user_name} dans les négociations avec les agents des autres amis.
Tu défends ses préférences et son emploi du temps SANS jamais exposer son calendrier brut.
Tu proposes, tu contre-proposes, tu acceptes ou tu refuses — toujours au nom de {user_name}.

## Préférences de {user_name}
{prefs_text}

## Historique récent
{history_text}

## Contexte de cette sortie
{context_text}

## Emploi du temps de {user_name} (2 prochaines semaines)
{calendar_text}

## Règles de négociation
- Propose UNIQUEMENT des créneaux marqués ✓ dans l'emploi du temps ci-dessus
- Défends ses préférences culinaires et de budget, mais sois flexible sur le reste
- Si un autre agent propose un créneau où {user_name} est indisponible, dis-le poliment et contre-propose un créneau libre
- Si un compromis raisonnable est trouvé sur un créneau où tout le monde est libre, accepte
- Sois concis, naturel, et constructif — pas de longs discours
- Utilise tes outils (calendrier, recherche de lieux) pour faire des propositions concrètes
- Quand tu proposes un lieu, utilise Tavily pour chercher un vrai restaurant/bar

## Format de tes messages
Parle naturellement, comme dans une conversation de groupe. Pas de bullet points.
Exemple : "Marie est libre mardi soir, elle adore la cuisine italienne — que dites-vous de La Trattoria dans le 11e ?"
"""


def _format_preferences(prefs: dict) -> str:
    parts = []
    if prefs.get("cuisines_liked"):
        parts.append(f"- Cuisines aimées : {', '.join(prefs['cuisines_liked'])}")
    if prefs.get("cuisines_disliked"):
        parts.append(f"- Cuisines évitées : {', '.join(prefs['cuisines_disliked'])}")
    if prefs.get("budget_range"):
        parts.append(f"- Budget : {prefs['budget_range']}")
    if prefs.get("preferred_areas"):
        parts.append(f"- Quartiers préférés : {', '.join(prefs['preferred_areas'])}")
    if prefs.get("preferred_days"):
        parts.append(f"- Jours préférés : {', '.join(prefs['preferred_days'])}")
    if prefs.get("dietary_constraints"):
        parts.append(f"- Contraintes : {', '.join(prefs['dietary_constraints'])}")
    return "\n".join(parts) if parts else "Pas encore de préférences renseignées."


def _format_history(history: list[dict]) -> str:
    if not history:
        return "Pas d'historique de sorties."
    lines = []
    for h in history[-5:]:  # Last 5
        rating = h.get("rating", "?")
        venue = h.get("venue", "?")
        comment = h.get("comment", "")
        lines.append(f"- {venue} → {rating}/5{f' ({comment})' if comment else ''}")
    return "\n".join(lines)


def _format_catchup_context(ctx: dict) -> str:
    if not ctx:
        return "Pas de contexte spécifique."
    parts = []
    if ctx.get("vibe"):
        parts.append(f"- Type de sortie : {ctx['vibe']}")
    if ctx.get("time_window"):
        parts.append(f"- Fenêtre de temps : {ctx['time_window']}")
    if ctx.get("group_members"):
        parts.append(f"- Participants : {', '.join(ctx['group_members'])}")
    return "\n".join(parts) if parts else "Pas de contexte spécifique."
