"""Shared FastAPI dependencies."""

import logging

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config import settings
from src.services.supabase_client import get_client

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


def _try_local_decode(token: str) -> str | None:
    """Try to decode the JWT locally with the configured HS256 secret.

    Returns the user id on success, None if the secret is missing/wrong/
    the algo doesn't match (e.g. Supabase asymmetric ES256 keys).
    """
    if not settings.supabase_jwt_secret:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        # Token is genuinely expired — let the caller surface a 401.
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        # Wrong secret or different algo — fall back to remote verification.
        return None


def _verify_via_supabase(token: str) -> str | None:
    """Verify the JWT by asking Supabase Auth itself. Works regardless of
    whether the project uses legacy HS256 secrets or the new asymmetric
    JWT signing keys.
    """
    try:
        client = get_client()
        result = client.auth.get_user(token)
        user = getattr(result, "user", None)
        if user and getattr(user, "id", None):
            return user.id
    except Exception as exc:  # supabase-py raises various error subclasses
        logger.warning("Supabase token verification failed: %s", exc)
    return None


async def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Resolve the authenticated user id from the request.

    Resolution order:
      1. Bearer token, locally decoded (HS256, fast path).
      2. Bearer token, verified by Supabase Auth (works for ES256 too).
      3. X-User-ID header (dev only).
    """
    if credentials:
        token = credentials.credentials
        user_id = _try_local_decode(token) or _verify_via_supabase(token)
        if user_id:
            return user_id
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if settings.env == "development":
        user_id = request.headers.get("x-user-id", "")
        if user_id:
            logger.warning("Using X-User-ID header (dev only)")
            return user_id

    raise HTTPException(status_code=401, detail="Missing authorization")
