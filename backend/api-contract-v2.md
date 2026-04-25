# Catch-Up — API Contract v2

> Révisé après décisions architecture voix :
> - ❌ Pas d'appel téléphonique à l'ami sans compte (trop lent en démo)
> - ✅ Voice = Gradbot WebSocket pour onboarding + feedback
> - ✅ Invites restent en mode SMS/lien web uniquement
> - ✅ VoiceService générique (même interface pour tous les cas)

---

## Changelog v1 → v2

| #  | Changement | Raison |
|----|-----------|--------|
| 3  | **MODIFIÉ** `/onboarding/voice-session` → `/ws/voice/{task_type}/{user_id}` | WebSocket Gradbot unifié, connexion directe |
| 4  | **SUPPRIMÉ** `/onboarding/process-transcript` | Gradbot extrait les données en live via tool calling |
| 31 | **SIMPLIFIÉ** `/invites/:token` → `/invites/notify` | L'ami sans compte ne participe pas à la négociation, il reçoit juste un SMS post-finalisation |
| 32 | **SUPPRIMÉ** `/invites/:token/respond` | Plus de vote guest |
| 33 | **SUPPRIMÉ** `/invites/voice-call` | Pas d'appel vocal |
| 37 | **MODIFIÉ** `/feedbacks` POST | Peut aussi être soumis via le WebSocket vocal |
| 7  | **SUPPRIMÉ** `/users/me/preferences` | Fusionné dans `/memories` — les préférences sont des mémoires avec scope |
| NEW | **AJOUTÉ** `/ws/voice/{task_type}/{user_id}` | Endpoint WebSocket Gradbot unifié |

---

## Endpoints

### Auth (Supabase natif)

| #  | Endpoint | Method | Purpose | Notes |
|----|----------|--------|---------|-------|
| 1  | `/auth/sms/send` | POST | Envoi code SMS | Supabase Auth natif |
| 2  | `/auth/sms/verify` | POST | Vérification code → JWT | Supabase Auth natif |

### Voice (Gradbot WebSocket) — NOUVEAU

| #  | Endpoint | Method | Purpose | Inputs | Outputs | Notes |
|----|----------|--------|---------|--------|---------|-------|
| V1 | `/ws/voice/{task_type}/{user_id}` | **WS** | Session vocale Gradbot | task_type: `onboarding` ou `feedback`, user_id, (+ catchup_id en query param pour feedback) | Audio bidirectionnel + données extraites sauvées en DB à la fermeture | **Remplace #3 et #4.** Le front ouvre le WS, l'utilisateur parle, Gradbot extrait les infos via tool call, écrit en DB, le WS se ferme. Front fait `refetch()` à la fermeture. |

### Profile

| #  | Endpoint | Method | Purpose | Notes |
|----|----------|--------|---------|-------|
| 5  | `/users/me` | GET | Profil courant | — |
| 6  | `/users/:id` | GET | Profil public (limité) | Champs limités |
| ~~7~~ | ~~`/users/me/preferences`~~ | ~~GET / PATCH~~ | ~~Préférences perso~~ | **SUPPRIMÉ** — fusionné dans `/memories` (scope = `cuisine`, `schedule`, etc.) |
| 8  | `/users/sync-contacts` | POST | Match contacts téléphone | — |

### Friends

| #  | Endpoint | Method | Purpose | Notes |
|----|----------|--------|---------|-------|
| 9  | `/friends` | GET | Mes amis | — |
| 10 | `/friends` | POST | Ajouter ami par téléphone | — |
| 11 | `/friends/:id` | DELETE | Retirer un ami | — |

### Calendar

| #  | Endpoint | Method | Purpose | Notes |
|----|----------|--------|---------|-------|
| 12 | `/calendar/auth-link` | GET | URL OAuth Google | — |
| 13 | `/calendar/sync` | POST | Pull des busy slots | — |
| 14 | `/calendar/context` | GET | Résumé texte pour agent | Param `intent` ajouté. **Interne** — chaque agent appelle ce endpoint pour SON utilisateur uniquement, puis défend ses dispos dans la négociation A2A sans les exposer. |

### Groups

| #  | Endpoint | Method | Purpose | Notes |
|----|----------|--------|---------|-------|
| 16 | `/groups` | GET | Mes groupes | — |
| 17 | `/groups` | POST | Créer groupe | — |
| 18 | `/groups/:id` | GET | Détails groupe | — |
| 19 | `/groups/:id` | PATCH | Modifier groupe | — |
| 20 | `/groups/:id` | DELETE | Supprimer groupe | — |

### Catchups

| #  | Endpoint | Method | Purpose | Notes |
|----|----------|--------|---------|-------|
| 21 | `/catchups` | GET | Mes catchups (filtre status) | — |
| 22 | `/catchups` | POST | Lancer un catchup | — |
| 23 | `/catchups/:id` | GET | Détails catchup | — |
| 24 | `/catchups/:id` | PATCH | Modifier catchup | — |
| 25 | `/catchups/:id` | DELETE | Annuler catchup | — |

### Agent / Négociation

| #  | Endpoint | Method | Purpose | Notes |
|----|----------|--------|---------|-------|
| 26 | `/catchups/:id/negotiate` | POST | Lancer négociation A2A | — |
| 27 | `/catchups/:id/negotiate/stream` | GET (SSE) | Stream des messages agents | **CRITIQUE** pour la démo |
| 28 | `/catchups/:id/proposal` | GET | Proposition IA courante | — |
| 29 | `/catchups/:id/vote` | POST | Accepter/refuser | — |
| 30 | `/catchups/:id/finalize` | POST | Push event Google Calendar | — |

### Invites (simplifié)

| #  | Endpoint | Method | Purpose | Notes |
|----|----------|--------|---------|-------|
| 31 | `/invites/notify` | POST | Envoie SMS à l'ami non inscrit | **Interne** — appelé par l'agent après finalisation. SMS = résumé + lien inscription. **Bonus**, pas critique pour la démo. |
| ~~32~~ | ~~`/invites/:token/respond`~~ | ~~POST~~ | ~~Guest vote~~ | **SUPPRIMÉ** — l'ami sans compte ne participe pas à la négociation |
| ~~33~~ | ~~`/invites/voice-call`~~ | ~~POST~~ | ~~Appel vocal sortant~~ | **SUPPRIMÉ** |

### Memory

| #  | Endpoint | Method | Purpose | Notes |
|----|----------|--------|---------|-------|
| 34 | `/memories` | GET | Ce que mon agent sait | — |
| 35 | `/memories/:id` | PATCH | Corriger une mémoire | — |
| 36 | `/memories/:id` | DELETE | Oublier une mémoire | — |

### Feedback

| #  | Endpoint | Method | Purpose | Notes |
|----|----------|--------|---------|-------|
| 37 | `/feedbacks` | POST | Soumettre feedback | Aussi possible via `/ws/voice/feedback/{user_id}` |
| 38 | `/feedbacks` | GET | Historique feedbacks | — |
| 39 | *enrichment job* | — | Job interne sur insert feedback | DB trigger, pas d'endpoint |

### Realtime

| #  | Endpoint | Method | Purpose | Notes |
|----|----------|--------|---------|-------|
| 40 | Supabase Realtime | WS | Subscribe aux changements | Tables: catchups, proposals, memories |

---

## Architecture Voice — résumé

```
Browser (Lovable)
    │
    │ WebSocket audio (micro navigateur)
    ▼
FastAPI: /ws/voice/{task_type}/{user_id}
    │
    │ VoiceTask (prompt + schema selon task_type)
    ▼
VoiceService → Gradbot (Gradium STT → LLM → Gradium TTS)
    │
    │ Tool call "save_result" → données structurées
    ▼
Supabase (write profile ou feedback)
    │
    │ WebSocket se ferme
    ▼
Front: refetch() → UI mise à jour
```

**Futur (post-hackathon)** : ajouter `/twilio-media` et `POST /api/voice/call` pour les appels téléphoniques. Le VoiceService reste identique, seul le transport audio change.

---

## Ce qui est implémenté au hackathon vs mocké

| Feature | Statut |
|---------|--------|
| Onboarding vocal (Gradbot) | ✅ Implémenté |
| Négociation A2A + stream SSE | ✅ Implémenté |
| Google Calendar read/write | ✅ Implémenté |
| Tavily recherche lieux | ✅ Implémenté |
| Feedback vocal | ⚡ Si le temps |
| Recurring catchups | 🎨 Mocké UI |
| Appel téléphonique ami | ❌ Hors scope |
| Réservation TheFork (Holo) | ⚡ Bonus |
