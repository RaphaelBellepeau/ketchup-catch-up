"""Google Calendar OAuth + status endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from src.deps import get_current_user_id
from src.services import gcal_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])


class AuthLinkResponse(BaseModel):
    url: str


class CalendarStatusResponse(BaseModel):
    connected: bool


@router.get("/auth-link", response_model=AuthLinkResponse)
async def calendar_auth_link(user_id: str = Depends(get_current_user_id)):
    """Return the Google consent URL for the current user.

    The frontend should `window.location.href = url` to start the dance.
    """
    try:
        url = gcal_client.build_auth_url(user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return AuthLinkResponse(url=url)


@router.get("/callback", include_in_schema=False)
async def calendar_callback(code: str | None = None, state: str | None = None,
                             error: str | None = None):
    """OAuth redirect target — exchanges the code, persists tokens, and
    bounces the user back to the frontend permissions screen.

    This endpoint is hit by Google's redirect (NO Authorization header) so
    we authenticate the user via the signed `state` JWT we issued in
    /calendar/auth-link.
    """
    if error or not code or not state:
        logger.warning("OAuth callback missing data: error=%s code?=%s state?=%s",
                       error, bool(code), bool(state))
        return RedirectResponse(gcal_client._frontend_return_url(connected=False))

    try:
        _user_id, success = await gcal_client.handle_oauth_callback(code, state)
    except Exception:
        logger.exception("OAuth callback handler crashed")
        return RedirectResponse(gcal_client._frontend_return_url(connected=False))

    return RedirectResponse(gcal_client._frontend_return_url(connected=success))


@router.get("/status", response_model=CalendarStatusResponse)
async def calendar_status(user_id: str = Depends(get_current_user_id)):
    connected = await gcal_client.is_connected(user_id)
    return CalendarStatusResponse(connected=connected)


@router.post("/disconnect", response_model=CalendarStatusResponse)
async def calendar_disconnect(user_id: str = Depends(get_current_user_id)):
    await gcal_client.disconnect(user_id)
    return CalendarStatusResponse(connected=False)
