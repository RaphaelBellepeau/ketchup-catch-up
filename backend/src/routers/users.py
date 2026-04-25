"""User profile routes."""

from fastapi import APIRouter, Depends, HTTPException

from src.deps import get_current_user_id
from src.services import supabase_client as db

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_my_profile(user_id: str = Depends(get_current_user_id)):
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{user_id}")
async def get_user_profile(user_id: str):
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user["id"], "name": user.get("name", "")}


@router.post("/sync-contacts")
async def sync_contacts(
    phones: list[str],
    user_id: str = Depends(get_current_user_id),
):
    """Match a list of phone numbers against registered users."""
    matches = await db.find_users_by_phones(phones)
    return {"matches": matches}
