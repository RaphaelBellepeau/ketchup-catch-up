"""Friends management routes."""

from fastapi import APIRouter, Depends, HTTPException

from src.deps import get_current_user_id
from src.models.schemas import AddFriendRequest
from src.services import supabase_client as db

router = APIRouter(prefix="/friends", tags=["friends"])


@router.get("")
async def list_friends(user_id: str = Depends(get_current_user_id)):
    return await db.get_friends(user_id)


@router.post("", status_code=201)
async def add_friend(
    body: AddFriendRequest,
    user_id: str = Depends(get_current_user_id),
):
    friend = await db.add_friend(user_id, body.phone, body.name)
    return friend


@router.delete("/{friend_id}", status_code=204)
async def remove_friend(
    friend_id: str,
    user_id: str = Depends(get_current_user_id),
):
    deleted = await db.delete_friend(user_id, friend_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Friend not found")
