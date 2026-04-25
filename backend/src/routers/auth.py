"""Auth routes — SMS OTP via Supabase Auth."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import settings
from src.services.supabase_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/sms", tags=["auth"])


class SmsSendRequest(BaseModel):
    phone: str


class SmsSendResponse(BaseModel):
    message: str


class SmsVerifyRequest(BaseModel):
    phone: str
    code: str


class SmsVerifyResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict


@router.post("/send", response_model=SmsSendResponse)
async def sms_send(body: SmsSendRequest):
    """Send an OTP code via SMS using Supabase Auth."""
    try:
        client = get_client()
        client.auth.sign_in_with_otp({"phone": body.phone})
        return SmsSendResponse(message="OTP sent")
    except Exception as exc:
        logger.exception("SMS send failed for %s", body.phone)
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/verify", response_model=SmsVerifyResponse)
async def sms_verify(body: SmsVerifyRequest):
    """Verify OTP code and return JWT session."""
    try:
        client = get_client()
        response = client.auth.verify_otp(
            {"phone": body.phone, "token": body.code, "type": "sms"}
        )
        session = response.session
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired code")

        return SmsVerifyResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user={
                "id": response.user.id,
                "phone": response.user.phone,
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("SMS verify failed for %s", body.phone)
        raise HTTPException(status_code=401, detail=str(exc))
