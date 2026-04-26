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


# Backwards-compatible stub kept until the agents migrate to the new API.
async def create_event(
    user_id: str,
    title: str,
    start_time: str,
    end_time: str,
    location: str = "",
    attendees: list[str] | None = None,
) -> dict:
    """TODO: implement event creation when negotiations finalize."""
    logger.info("Calendar event creation stub: %s for user %s", title, user_id)
    return {
        "status": "stub",
        "event_id": None,
        "message": f"Event '{title}' would be created",
    }
