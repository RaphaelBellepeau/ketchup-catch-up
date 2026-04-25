# Catch-Up API Reference

> **Base URL:** `https://<backend-url>` (local: `http://localhost:8000`)
>
> **Auth:** All authenticated routes require either:
> - `Authorization: Bearer <supabase-jwt>` (production)
> - `X-User-ID: <uuid>` header (development only)
>
> Routes marked 🔒 require auth. Routes marked 🌐 are public.

---

## Health

### 🌐 `GET /health`

```json
// Response 200
{ "status": "ok", "env": "development" }
```

---

## Auth (SMS OTP)

### 🌐 `POST /auth/sms/send`

Send an OTP code via SMS using Supabase Auth.

```json
// Request body
{ "phone": "+33612345678" }

// Response 200
{ "message": "OTP sent" }
```

> Supabase sends a 6-digit code to the phone number.

### 🌐 `POST /auth/sms/verify`

Verify the OTP code and get a JWT session.

```json
// Request body
{ "phone": "+33612345678", "code": "123456" }

// Response 200
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "v1.MjQ5ZDY2Mz...",
  "user": {
    "id": "4d18265b-0e60-409c-a026-89f087362c2c",
    "phone": "+33612345678"
  }
}

// Response 401
{ "detail": "Invalid or expired code" }
```

> Use the `access_token` as `Authorization: Bearer <token>` for all 🔒 routes.

---

## Users

### 🔒 `GET /users/me`

Returns the authenticated user's full profile.

```json
// Response 200
{
  "id": "4d18265b-0e60-409c-a026-89f087362c2c",
  "phone": "33612345678",
  "name": "TestUser",
  "created_at": "2026-04-25T20:26:16.541995+00:00"
}
```

### 🌐 `GET /users/{user_id}`

Returns a public (limited) profile for any user.

```json
// Response 200
{
  "id": "acc04bfc-343b-4c87-a34a-65fa422831df",
  "name": "Marie"
}
```

### 🔒 `POST /users/sync-contacts`

Match a list of phone numbers against registered users.

```json
// Request body
{ "phones": ["+33612345678", "+33698765432"] }

// Response 200
{
  "matches": [
    { "id": "4d18265b-...", "name": "TestUser", "phone": "+33612345678" },
    { "id": "acc04bfc-...", "name": "Marie", "phone": "+33698765432" }
  ]
}
```

---

## Friends

### 🔒 `GET /friends`

Returns all friends of the authenticated user.

```json
// Response 200
[
  {
    "id": "8aaf73d6-1968-4335-9df6-4d52594ffcc7",
    "user_id": "4d18265b-...",
    "friend_id": null,
    "name": "Marie",
    "phone": "+33698765432",
    "is_on_app": false,
    "created_at": "2026-04-25T20:26:54.296244+00:00"
  }
]
```

> `friend_id` is the UUID of the friend's account if they're on the app, `null` otherwise.
> `is_on_app` indicates whether the phone number matches a registered user.

### 🔒 `POST /friends`

Add a friend by phone number.

```json
// Request body
{ "phone": "+33698765432", "name": "Marie" }

// Response 201
{
  "id": "8aaf73d6-...",
  "user_id": "4d18265b-...",
  "friend_id": null,
  "name": "Marie",
  "phone": "+33698765432",
  "is_on_app": false,
  "created_at": "2026-04-25T20:26:54.296244+00:00"
}
```

### 🔒 `DELETE /friends/{friend_id}`

Remove a friend. Returns `204 No Content` on success, `404` if not found.

---

## Groups

### 🔒 `GET /groups`

Returns all groups the authenticated user belongs to.

```json
// Response 200
[
  {
    "id": "abcce863-6a4b-468c-aa7a-fa76c0dc1398",
    "name": "Crew",
    "created_by": "4d18265b-...",
    "created_at": "2026-04-25T20:26:54.5003+00:00"
  }
]
```

### 🔒 `POST /groups`

Create a group and add members. The creator is automatically added.

```json
// Request body
{
  "name": "Crew",
  "member_ids": ["acc04bfc-..."]
}

// Response 201
{
  "id": "abcce863-...",
  "name": "Crew",
  "created_by": "4d18265b-...",
  "created_at": "2026-04-25T20:26:54.5003+00:00",
  "members": ["acc04bfc-...", "4d18265b-..."]
}
```

### 🔒 `GET /groups/{group_id}`

```json
// Response 200
{
  "id": "abcce863-...",
  "name": "Crew",
  "created_by": "4d18265b-...",
  "created_at": "2026-04-25T20:26:54.5003+00:00",
  "members": ["acc04bfc-...", "4d18265b-..."]
}
```

### 🔒 `PATCH /groups/{group_id}`

```json
// Request body (partial update)
{ "name": "New Name" }

// Response 200 — updated group object
```

### 🔒 `DELETE /groups/{group_id}`

Returns `204 No Content`.

---

## Catchups

### 🔒 `GET /catchups`

List catchups for the authenticated user's groups. Optional query params: `?status=pending&group_id=...`

```json
// Response 200
[
  {
    "id": "d10e174d-efcc-42d1-b62c-ca7017267b9a",
    "group_id": "abcce863-...",
    "created_by": "4d18265b-...",
    "type": "one_shot",
    "status": "pending",
    "time_window": "next weekend",
    "vibe": "dinner",
    "created_at": "2026-04-25T20:28:10.714269+00:00"
  }
]
```

> **Status values:** `pending` → `negotiating` → `proposed` → `accepted` → `done`

### 🔒 `POST /catchups`

```json
// Request body
{
  "group_id": "abcce863-...",
  "type": "one_shot",
  "time_window": "next weekend",
  "vibe": "dinner"
}

// Response 201 — catchup object (same shape as GET)
```

> `type`: `"one_shot"` or `"recurring"` (recurring is mocked UI-only for now)

### 🌐 `GET /catchups/{catchup_id}`

```json
// Response 200 — single catchup object
```

### 🔒 `PATCH /catchups/{catchup_id}`

```json
// Request body (partial)
{ "vibe": "drinks", "time_window": "next friday" }

// Response 200 — updated catchup object
```

### 🔒 `DELETE /catchups/{catchup_id}`

Returns `204 No Content`.

---

## Negotiation

### 🔒 `POST /catchups/{catchup_id}/negotiate`

Launch A2A negotiation. Creates a negotiation record and starts the agent loop.

```json
// Response 200
{
  "id": "913ccd24-8d50-4dc2-aab2-a2343f4730b4",
  "catchup_id": "d10e174d-...",
  "status": "active",
  "started_at": "2026-04-25T20:48:07.940528+00:00",
  "ended_at": null
}
```

### 🌐 `GET /catchups/{catchup_id}/negotiate/stream`

**SSE (Server-Sent Events)** stream of agent dialogue messages. Connect with `EventSource`.

```
event: message
data: {"agent_name": "marie_agent", "role": "propose", "content": "How about Saturday at 7pm?", "data": {}, "timestamp": "..."}

event: message
data: {"agent_name": "paul_agent", "role": "counter", "content": "I prefer Sunday, I'm busy Saturday.", "data": {}, "timestamp": "..."}

event: message
data: {"agent_name": "marie_agent", "role": "accept", "content": "Sunday works! Let me find a place...", "data": {}, "timestamp": "..."}
```

> **Message roles:** `propose`, `counter`, `accept`, `reject`, `info`

### 🌐 `GET /catchups/{catchup_id}/proposal`

Get the current AI proposal for a catchup.

```json
// Response 200
{
  "id": "a1b2c3d4-...",
  "catchup_id": "d10e174d-...",
  "venue": "Kodawari Ramen, Paris 6e",
  "time": "Sunday 7pm",
  "activity": "dinner",
  "justification": "Marie loves ramen, Paul prefers Sunday. Budget-friendly in an area both like.",
  "created_at": "2026-04-25T21:00:00+00:00"
}

// Response 404
{ "detail": "No proposal yet" }
```

### 🔒 `POST /catchups/{catchup_id}/vote`

Accept or reject the current proposal.

```json
// Request body
{ "vote": "accept", "reason": "Looks great!" }

// Response 200
{
  "id": "89e8736f-...",
  "catchup_id": "d10e174d-...",
  "user_id": "4d18265b-...",
  "vote": "accept",
  "reason": "Looks great!",
  "created_at": "2026-04-25T20:48:08.259263+00:00"
}
```

> `vote`: `"accept"` or `"reject"`

### 🔒 `POST /catchups/{catchup_id}/finalize`

Push the accepted event to all members' Google Calendars.

```json
// Response 200
{ "status": "finalized", "catchup_id": "d10e174d-..." }
```

---

## Memories

All user knowledge (preferences, habits, feedback learnings) is stored as free-text memories. These are injected into agent system prompts during negotiation.

### 🔒 `GET /memories`

Optional query param: `?scope=cuisine`

```json
// Response 200
[
  {
    "id": "f1e2d3c4-...",
    "user_id": "4d18265b-...",
    "scope": "cuisine",
    "content": "Loves Japanese food, especially ramen. Vegetarian.",
    "source": "onboarding",
    "created_at": "2026-04-25T20:30:00+00:00"
  },
  {
    "id": "a9b8c7d6-...",
    "user_id": "4d18265b-...",
    "scope": "schedule",
    "content": "Usually free on weekends. Works late on Wednesdays.",
    "source": "onboarding",
    "created_at": "2026-04-25T20:30:00+00:00"
  }
]
```

> **Scopes:** `general`, `cuisine`, `schedule`, `social`, `budget`
> **Sources:** `onboarding` (voice), `feedback` (post-catchup), `manual` (user edit)

### 🔒 `PATCH /memories/{memory_id}`

```json
// Request body
{ "content": "Updated memory text", "scope": "cuisine" }

// Response 200 — updated memory object
```

### 🔒 `DELETE /memories/{memory_id}`

Returns `204 No Content`.

---

## Feedbacks

### 🔒 `POST /feedbacks`

Submit feedback after a catchup. Can also be submitted via voice WebSocket.

```json
// Request body
{
  "catchup_id": "d10e174d-...",
  "rating": 4,
  "tags": ["good food", "fun"],
  "comment": "Great dinner!"
}

// Response 201
{
  "id": "8778760e-...",
  "catchup_id": "d10e174d-...",
  "user_id": "4d18265b-...",
  "rating": 4,
  "tags": ["good food", "fun"],
  "liked": [],
  "disliked": [],
  "comment": "Great dinner!",
  "created_at": "2026-04-25T20:48:08.461475+00:00"
}
```

> `rating`: integer 1–5
> `liked`/`disliked`: populated by enrichment job post-insert (extracted from comment)

### 🔒 `GET /feedbacks`

Optional query param: `?catchup_id=...`

```json
// Response 200 — array of feedback objects
```

---

## Calendar (stubs)

### 🌐 `GET /calendar/auth-link`

Returns Google OAuth URL for calendar access. *Not yet implemented.*

### 🔒 `POST /calendar/sync`

Pull busy slots from Google Calendar. *Not yet implemented.*

### 🌐 `GET /calendar/context?user_id=...&date_range=...&intent=...`

Internal endpoint for agents. Returns text summary of user's schedule. *Not yet implemented.*

---

## Invites (bonus)

### 🔒 `POST /invites/notify`

Send SMS to non-member friend with meetup summary. *Not yet implemented — bonus feature.*

---

## Voice (WebSocket)

### `WS /ws/voice/{task_type}/{user_id}`

Gradbot voice session. Opens a bidirectional audio WebSocket.

- **task_type:** `"onboarding"` or `"feedback"`
- **user_id:** UUID of the user
- For feedback: add query param `?catchup_id=...`

**Flow:**
1. Frontend opens WebSocket
2. User speaks → Gradbot transcribes → LLM processes → Gradbot speaks back
3. LLM calls `save_result` tool when enough info is extracted
4. Data is saved to DB (memories for onboarding, feedback for feedback)
5. WebSocket closes
6. Frontend calls `refetch()` to update UI

---

## Supabase Realtime

Subscribe to real-time changes on these tables via Supabase client:
- `catchups` — status changes
- `proposals` — new proposals from negotiation
- `negotiation_messages` — live agent dialogue
- `memories` — new memories added

```typescript
// Example (Supabase JS client)
supabase
  .channel('catchup-updates')
  .on('postgres_changes', {
    event: '*',
    schema: 'public',
    table: 'negotiation_messages',
    filter: `negotiation_id=eq.${negotiationId}`
  }, (payload) => {
    // Append new message to chat UI
  })
  .subscribe()
```

---

## Error Responses

All errors follow this format:

```json
{ "detail": "Error message here" }
```

| Status | Meaning |
|--------|---------|
| 401 | Missing or invalid auth |
| 404 | Resource not found |
| 422 | Validation error (bad request body) |
| 500 | Server error |
