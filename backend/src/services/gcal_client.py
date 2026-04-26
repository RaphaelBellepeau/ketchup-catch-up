"""Google Calendar OAuth + Free/Busy client.

Connect flow (server-side authorization code with refresh token):
  1. Frontend hits /calendar/auth-link → backend signs a short-lived JWT
     state containing the user_id and returns the consent URL.
  2. User authorizes on Google → redirected to /calendar/callback with
     ?code=... and ?state=<jwt>.
  3. Backend verifies the JWT, exchanges the code for access + refresh
     tokens via /token, and persists them in `google_oauth_tokens`.
  4. Backend bounces the user back to ${FRONTEND_BASE_URL}/onboarding/permissions?calendar=connected.

After connect, get_busy_slots(user_id, ...) auto-refreshes the access
token if it's expired before calling /freeBusy.
"""

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt

from src.config import settings
from src.services import supabase_client as db

logger = logging.getLogger(__name__)

OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "openid",
    "email",
]
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
FREEBUSY_URL = "https://www.googleapis.com/calendar/v3/freeBusy"
EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
DEFAULT_TIMEZONE = "Europe/Paris"

# Short TTL for the OAuth state JWT — the consent dance should be fast.
STATE_TTL_SECONDS = 600


def _redirect_uri() -> str:
    """The exact value registered in Google Cloud Console."""
    return f"{settings.backend_base_url.rstrip('/')}/calendar/callback"


def _frontend_return_url(connected: bool) -> str:
    """Where to bounce the user after the OAuth dance completes."""
    qs = "calendar=connected" if connected else "calendar=error"
    return f"{settings.frontend_base_url.rstrip('/')}/onboarding/permissions?{qs}"


def _state_secret() -> str:
    """Reuse the Supabase JWT secret for signing OAuth state — same trust
    boundary, no new key to manage at hackathon scale.
    """
    if not settings.supabase_jwt_secret:
        raise RuntimeError(
            "SUPABASE_JWT_SECRET must be set to sign Google OAuth state",
        )
    return settings.supabase_jwt_secret


def build_auth_url(user_id: str) -> str:
    """Build the Google consent URL for the given user."""
    if not settings.google_calendar_client_id:
        raise RuntimeError("GOOGLE_CALENDAR_CLIENT_ID is not set")

    now = datetime.now(timezone.utc)
    state = jwt.encode(
        {
            "sub": user_id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=STATE_TTL_SECONDS)).timestamp()),
            "purpose": "google_calendar_oauth",
        },
        _state_secret(),
        algorithm="HS256",
    )

    params = {
        "client_id": settings.google_calendar_client_id,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": " ".join(OAUTH_SCOPES),
        # offline + consent are what guarantee a refresh_token on every
        # authorization (Google omits it on subsequent silent grants).
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def _decode_state(state: str) -> str:
    """Verify the state JWT and return the user_id (sub)."""
    payload = jwt.decode(state, _state_secret(), algorithms=["HS256"])
    if payload.get("purpose") != "google_calendar_oauth":
        raise ValueError("State JWT has wrong purpose")
    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("State JWT missing sub")
    return user_id


async def handle_oauth_callback(code: str, state: str) -> tuple[str, bool]:
    """Exchange the authorization code for tokens and persist them.

    Returns ``(user_id, success)``. The router wraps this in a redirect
    back to the frontend.
    """
    user_id = _decode_state(state)

    payload = {
        "code": code,
        "client_id": settings.google_calendar_client_id,
        "client_secret": settings.google_calendar_client_secret,
        "redirect_uri": _redirect_uri(),
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data=payload)

    if resp.status_code != 200:
        logger.warning(
            "Google token exchange failed: status=%s body=%s",
            resp.status_code, resp.text[:300],
        )
        return user_id, False

    data = resp.json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    expires_in = int(data.get("expires_in", 3600))
    scopes = (data.get("scope") or "").split()

    if not access_token:
        logger.warning("Google token exchange missing access_token: %s", data)
        return user_id, False
    if not refresh_token:
        # This happens if the user previously authorized — Google then
        # only returns access_token. We force prompt=consent above so this
        # should be rare; if it does happen, we keep the existing refresh
        # token (if any) instead of clobbering with NULL.
        existing = await db.get_calendar_tokens(user_id)
        refresh_token = existing.get("refresh_token") if existing else None
        if not refresh_token:
            logger.warning("No refresh_token returned and none stored")
            return user_id, False

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    await db.save_calendar_tokens(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at.isoformat(),
        scopes=scopes,
    )
    logger.info("Google Calendar connected for user=%s scopes=%s", user_id, scopes)
    return user_id, True


async def _refresh_access_token(user_id: str, refresh_token: str) -> str | None:
    """Use the stored refresh token to mint a fresh access token. Persists
    the new access_token + expires_at and returns the access_token, or
    None on failure.
    """
    payload = {
        "client_id": settings.google_calendar_client_id,
        "client_secret": settings.google_calendar_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data=payload)
    if resp.status_code != 200:
        logger.warning(
            "Google refresh failed user=%s status=%s body=%s",
            user_id, resp.status_code, resp.text[:300],
        )
        return None
    data = resp.json()
    access_token = data.get("access_token")
    expires_in = int(data.get("expires_in", 3600))
    if not access_token:
        return None
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    await db.update_calendar_access_token(
        user_id=user_id,
        access_token=access_token,
        expires_at=expires_at.isoformat(),
    )
    return access_token


async def _ensure_access_token(user_id: str) -> str | None:
    """Return a valid access token for the user, refreshing if needed."""
    tokens = await db.get_calendar_tokens(user_id)
    if not tokens:
        return None
    expires_at_raw = tokens.get("expires_at")
    if not expires_at_raw:
        return None
    expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
    # Refresh a minute early to dodge clock skew.
    if expires_at - datetime.now(timezone.utc) < timedelta(seconds=60):
        return await _refresh_access_token(user_id, tokens["refresh_token"])
    return tokens["access_token"]


async def is_connected(user_id: str) -> bool:
    """True iff we have at least one stored refresh token for the user."""
    tokens = await db.get_calendar_tokens(user_id)
    return bool(tokens and tokens.get("refresh_token"))


async def disconnect(user_id: str) -> bool:
    """Revoke the user's tokens with Google and delete them locally."""
    tokens = await db.get_calendar_tokens(user_id)
    if not tokens:
        return False
    refresh_token = tokens.get("refresh_token")
    if refresh_token:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(
                    GOOGLE_REVOKE_URL,
                    data={"token": refresh_token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except Exception:
            logger.exception("Google revoke call failed (best-effort)")
    await db.delete_calendar_tokens(user_id)
    return True


async def push_catchup_to_calendars(catchup_id: str) -> dict:
    """Create a Google Calendar event for every group member who has
    connected their calendar. Best-effort: failures for one user don't
    block the others.

    Returns ``{"created": int, "skipped": int, "errors": int}``.
    """
    from src.services import supabase_client as db  # avoid circular import

    catchup = await db.get_catchup(catchup_id)
    if not catchup:
        return {"created": 0, "skipped": 0, "errors": 0}
    proposal = await db.get_proposal(catchup_id)
    if not proposal:
        return {"created": 0, "skipped": 0, "errors": 0}

    start_raw = proposal.get("start_at")
    if not start_raw:
        logger.info("No start_at on proposal — skipping calendar push")
        return {"created": 0, "skipped": 0, "errors": 0}

    try:
        start_at = datetime.fromisoformat(str(start_raw).replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Could not parse proposal.start_at=%r", start_raw)
        return {"created": 0, "skipped": 0, "errors": 0}

    try:
        duration_minutes = int(proposal.get("duration_minutes") or 120)
    except (TypeError, ValueError):
        duration_minutes = 120
    end_at = start_at + timedelta(minutes=duration_minutes)

    members = await db.get_group_members(catchup["group_id"])
    group = await db.get_group(catchup["group_id"]) or {}
    group_name = group.get("name") or "your group"

    venue = proposal.get("venue") or "TBD"
    activity = proposal.get("activity") or "Catch-up"
    title = f"{activity.title()} with {group_name} — {venue}"
    description_lines = [
        f"Venue: {venue}",
        f"Why: {proposal.get('justification') or '—'}",
        "Planned via Catch-Up.",
    ]
    description = "\n".join(description_lines)

    created = skipped = errors = 0
    for m in members:
        user_id = m.get("user_id")
        if not user_id:
            continue
        try:
            res = await create_event(
                user_id=user_id,
                title=title,
                start_at=start_at,
                end_at=end_at,
                description=description,
                location=venue,
            )
            status = res.get("status")
            if status == "success":
                created += 1
            elif status == "skipped":
                skipped += 1
            else:
                errors += 1
        except Exception:
            logger.exception("Calendar push failed for user=%s", user_id)
            errors += 1

    logger.info(
        "Calendar push for catchup=%s: created=%d skipped=%d errors=%d",
        catchup_id, created, skipped, errors,
    )
    return {"created": created, "skipped": skipped, "errors": errors}


async def get_busy_slots(
    user_id: str,
    time_min: datetime,
    time_max: datetime,
    calendars: list[str] | None = None,
) -> list[dict]:
    """Return [{start, end}] busy windows from the user's primary calendar.

    Returns an empty list (not an error) if the user hasn't connected
    Calendar yet — callers should treat that as "no constraints known".
    """
    access_token = await _ensure_access_token(user_id)
    if not access_token:
        return []

    body = {
        "timeMin": time_min.isoformat(),
        "timeMax": time_max.isoformat(),
        "items": [{"id": cid} for cid in (calendars or ["primary"])],
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(FREEBUSY_URL, headers=headers, json=body)
    if resp.status_code != 200:
        logger.warning(
            "freeBusy failed user=%s status=%s body=%s",
            user_id, resp.status_code, resp.text[:300],
        )
        return []
    data = resp.json()
    busy: list[dict] = []
    for cal_data in (data.get("calendars") or {}).values():
        busy.extend(cal_data.get("busy") or [])
    return busy


async def create_event(
    user_id: str,
    *,
    title: str,
    start_at: datetime,
    end_at: datetime,
    description: str = "",
    location: str = "",
    timezone: str = DEFAULT_TIMEZONE,
    attendees: list[str] | None = None,
) -> dict:
    """Create an event on the user's primary Google Calendar.

    Returns ``{"status": "success" | "skipped" | "error", "event_id": str|None,
    "html_link": str|None, "message": str}``. ``skipped`` means the user
    has not connected their calendar — callers should treat that as a
    soft no-op, not a failure.
    """
    access_token = await _ensure_access_token(user_id)
    if not access_token:
        return {
            "status": "skipped",
            "event_id": None,
            "html_link": None,
            "message": "Calendar not connected",
        }

    body: dict = {
        "summary": title,
        "start": {"dateTime": _isoformat_with_tz(start_at), "timeZone": timezone},
        "end": {"dateTime": _isoformat_with_tz(end_at), "timeZone": timezone},
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location
    if attendees:
        body["attendees"] = [{"email": a} for a in attendees if a]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(EVENTS_URL, headers=headers, json=body)
    except Exception as exc:
        logger.exception("Calendar event POST failed for user=%s", user_id)
        return {"status": "error", "event_id": None, "html_link": None, "message": str(exc)}

    if resp.status_code not in (200, 201):
        logger.warning(
            "Calendar event create non-2xx user=%s status=%s body=%s",
            user_id, resp.status_code, resp.text[:300],
        )
        return {
            "status": "error",
            "event_id": None,
            "html_link": None,
            "message": f"Google returned {resp.status_code}",
        }

    data = resp.json()
    return {
        "status": "success",
        "event_id": data.get("id"),
        "html_link": data.get("htmlLink"),
        "message": "Event created",
    }


def _isoformat_with_tz(dt: datetime) -> str:
    """Produce an RFC3339 datetime string Google's API likes."""
    if dt.tzinfo is None:
        # Treat naive datetimes as already in the user's timezone — Google
        # uses the `timeZone` field next to it.
        return dt.isoformat()
    return dt.isoformat()
