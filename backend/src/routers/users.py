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


@router.patch("/me")
async def update_my_profile(
    body: dict,
    user_id: str = Depends(get_current_user_id),
):
    """Update writable fields on the current user. Currently just `name`."""
    updated = await db.update_user(user_id, body)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated


@router.get("/discoverable")
async def list_discoverable_users(user_id: str = Depends(get_current_user_id)):
    """Every other registered user — used by the New Group flow until we
    wire up real contact-list scanning. Returns id, name, phone."""
    return await db.list_other_users(user_id)


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
