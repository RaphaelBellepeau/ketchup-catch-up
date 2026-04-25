"""Feedback routes."""

from fastapi import APIRouter, Depends

from src.deps import get_current_user_id
from src.models.schemas import FeedbackRequest
from src.services import supabase_client as db

router = APIRouter(prefix="/feedbacks", tags=["feedbacks"])


@router.post("", status_code=201)
async def submit_feedback(
    body: FeedbackRequest,
    user_id: str = Depends(get_current_user_id),
):
    data = body.model_dump()
    data["user_id"] = user_id
    feedback = await db.save_feedback(data)
    return feedback


@router.get("")
async def list_feedbacks(
    catchup_id: str = "",
    user_id: str = Depends(get_current_user_id),
):
    return await db.get_feedbacks(user_id, catchup_id=catchup_id)
