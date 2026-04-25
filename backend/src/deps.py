"""Shared FastAPI dependencies."""

import logging

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config import settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


async def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Decode Supabase JWT and return the user id (sub claim).

    Falls back to X-User-ID header in development for easy testing.
    """
    # Try Bearer token first
    if credentials:
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
            return payload["sub"]
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    # Dev fallback: X-User-ID header
    if settings.env == "development":
        user_id = request.headers.get("x-user-id", "")
        if user_id:
            logger.warning("Using X-User-ID header (dev only)")
            return user_id

    raise HTTPException(status_code=401, detail="Missing authorization")
