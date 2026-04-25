# Catch-Up Backend — CLAUDE.md

## Projet
Catch-Up : plateforme multi-agents IA pour organiser des sorties entre amis.
Chaque utilisateur a un agent IA personnel qui négocie avec les agents de ses amis (protocole A2A) pour trouver un créneau, un lieu et une activité.

## Contexte hackathon
- **Durée restante** : ~20h
- **Équipe** : 2 devs. Ce repo = Dev 2 (backend + agents). Dev 1 = front Lovable + Supabase.
- **Partenaires obligatoires (3 min)** : Google DeepMind/GCP, Lovable, Tavily, Gradium
- **Règle d'or** : à chaque palier le projet est démontrable. On rollback au dernier vert.

## Stack technique
- Python 3.12 + FastAPI + uv (package manager)
- Google ADK Python (agents) — `from google.adk.agents import Agent`
- Gemini via Vertex AI (modèle : `gemini-2.5-flash`)
- Gradbot (voix onboarding/feedback) — `pip install gradbot`
- Tavily Python SDK (recherche lieux) — `pip install tavily-python`
- Pydantic v2 pour tous les schémas
- httpx pour les appels HTTP
- Supabase Python SDK pour la DB
- Déploiement : Cloud Run (min instances = 1)
- Logs structurés JSON dans Supabase pour replay négo dans l'UI

## Architecture fichiers
```
catchup-backend/
├── CLAUDE.md                    # CE FICHIER
├── pyproject.toml               # uv project config
├── Dockerfile
├── .env.example
├── .claude/
│   └── skills/
│       ├── deploy.md            # Skill : déployer sur Cloud Run
│       ├── scaffold-agent.md    # Skill : créer un nouvel agent ADK
│       ├── test-endpoint.md     # Skill : tester un endpoint
│       └── gradbot-voice.md     # Skill : intégration Gradbot (API, tools, frontend, troubleshooting)
├── src/
│   ├── main.py                  # FastAPI app, tous les endpoints
│   ├── config.py                # Settings (env vars, Pydantic BaseSettings)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── user_agent.py        # Agent personnel d'un utilisateur (ADK)
│   │   ├── negotiation.py       # Orchestration multi-agents A2A
│   │   ├── prompts.py           # System prompts avec injection mémoire
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── calendar_tool.py # Outil : lire Google Calendar de l'utilisateur
│   │       ├── tavily_tool.py   # Outil : rechercher lieux/activités
│   │       └── memory_tool.py   # Outil : lire/écrire préférences utilisateur
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── tasks.py             # VoiceTask dataclass + configs (onboarding, feedback)
│   │   └── service.py           # VoiceService — handler WebSocket Gradbot
│   ├── services/
│   │   ├── __init__.py
│   │   ├── supabase_client.py   # Client Supabase (CRUD)
│   │   └── gcal_client.py       # Client Google Calendar API
│   └── models/
│       ├── __init__.py
│       └── schemas.py           # Pydantic v2 models (User, Catchup, Preference, etc.)
└── tests/
    └── test_agents.py
```

## Conventions de code
- **Pydantic v2** partout : `from pydantic import BaseModel`, pas de dict bruts
- **Async** partout : tous les endpoints et services sont async
- **Type hints** : obligatoires sur toutes les fonctions
- **Docstrings** : sur les fonctions publiques, en anglais
- **Imports** : stdlib → third-party → local, séparés par une ligne vide
- **Pas de print()** : utiliser `logging` ou `structlog`
- **Pas de secrets en dur** : tout dans `.env` via `config.py`

## Contrat d'API avec le front
Voir le fichier `api-contract-v2.md` à la racine.
Points critiques :
- `POST /catchups/:id/negotiate` → lance la négociation A2A
- `GET /catchups/:id/negotiate/stream` → SSE stream des messages agents (CRITIQUE pour la démo)
- `WS /ws/voice/{task_type}/{user_id}` → WebSocket Gradbot (onboarding + feedback)

## DB Supabase (tables principales)
```sql
users         (id, phone, name, created_at)
friends       (id, user_id, friend_id, name, phone, is_on_app)
groups        (id, name, created_by)
group_members (group_id, user_id)
catchups      (id, group_id, type, status, time_window, vibe, created_at)
negotiations  (id, catchup_id, status, started_at, ended_at)
negotiation_messages (id, negotiation_id, agent_name, role, content, timestamp)
proposals     (id, catchup_id, venue, time, activity, justification)
votes         (id, catchup_id, user_id, vote, reason)
feedbacks     (id, catchup_id, user_id, rating, liked, disliked, comment)
memories      (id, user_id, scope, content, source, created_at)
```

## Comment la voix fonctionne (Gradbot)

**Lire `.claude/skills/gradbot-voice.md` AVANT de toucher à quoi que ce soit dans `src/voice/`.**

Résumé : Gradbot orchestre STT → LLM → TTS via WebSocket. L'utilisateur parle dans son navigateur, Gradbot transcrit, envoie au LLM, génère la réponse vocale, et gère les tours de parole automatiquement.

Notre pattern :
- `VoiceTask` = config (prompt + schema de sortie) — défini dans `src/voice/tasks.py`
- `VoiceService` = handler WebSocket unique — défini dans `src/voice/service.py`
- Un seul tool `save_result` — le LLM l'appelle quand il a extrait assez d'infos
- Les données extraites sont écrites en DB, le WebSocket se ferme, le front fait refetch

Règles critiques :
- `silence_timeout_s = 0.0` toujours (sinon l'agent se re-prompt lui-même)
- `parameters_json = json.dumps({...})` pas un dict brut
- Jamais `"type": "array"` dans les params tool — utiliser `"type": "string"` + "comma-separated"
- `handle.args` est déjà un dict — pas de json.loads() dessus

## Comment les agents fonctionnent

### Agent personnel (user_agent.py)
Chaque utilisateur a un agent ADK avec :
- Un system prompt personnalisé (injecté depuis `prompts.py` avec ses préférences)
- Des outils : `calendar_tool`, `tavily_tool`, `memory_tool`
- Un modèle : `gemini-2.5-flash` via Vertex AI

### Négociation A2A (negotiation.py)
Quand un catchup est lancé :
1. On crée un agent par membre du groupe
2. L'agent initiateur propose un créneau basé sur le calendrier de son user
3. Les autres agents répondent en défendant les préférences de leur user
4. Les échanges sont logués dans `negotiation_messages` (Supabase)
5. Le front lit ces messages en SSE pour afficher le dialogue en temps réel
6. Quand consensus → on crée une `proposal`

### Communication inter-agents
Pas de SDK A2A lourd. Communication HTTP simple entre agents dans le même process.
Format des messages : `{"agent": "marie_agent", "role": "propose|counter|accept|reject", "content": "...", "data": {...}}`
Pitch jury : "architecture conforme au standard A2A de Google".

## Commandes utiles
```bash
# Setup
uv sync

# Dev local
uv run uvicorn src.main:app --reload --port 8000

# Lancer un seul test
uv run pytest tests/test_agents.py -v

# Deploy Cloud Run
gcloud run deploy catchup-backend \
  --source . \
  --region europe-west1 \
  --min-instances 1 \
  --set-env-vars "$(cat .env | grep -v '^#' | xargs)"

# Voir les logs Cloud Run
gcloud run logs read catchup-backend --region europe-west1 --limit 50
```

## Règles pour Claude Code
1. **Plan mode** systématique pour les features non triviales
2. **Jamais** modifier le contrat d'API sans en discuter
3. **Toujours** tester un endpoint après l'avoir créé (curl ou pytest)
4. **Si un service externe échoue** (Tavily, Calendar, Gradium) : log l'erreur et retourner un fallback raisonnable, ne jamais crasher
5. **Chaque PR** doit laisser le serveur démarrable (`uvicorn src.main:app` ne crashe pas)
6. Utiliser les **subagents** Claude Code pour l'exploration (lire des docs, tester des libs) sans polluer le contexte principal
7. En cas de doute sur l'architecture → relire ce CLAUDE.md
