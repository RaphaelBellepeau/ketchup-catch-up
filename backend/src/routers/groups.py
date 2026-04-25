"""Groups management routes."""

from fastapi import APIRouter, Depends, HTTPException

from src.deps import get_current_user_id
from src.models.schemas import CreateGroupRequest
from src.services import supabase_client as db

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("")
async def list_groups(user_id: str = Depends(get_current_user_id)):
    return await db.get_user_groups(user_id)


@router.post("", status_code=201)
async def create_group(
    body: CreateGroupRequest,
    user_id: str = Depends(get_current_user_id),
):
    group = await db.create_group(user_id, body.name, body.member_ids)
    return group


@router.get("/{group_id}")
async def get_group(group_id: str, user_id: str = Depends(get_current_user_id)):
    group = await db.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.patch("/{group_id}")
async def update_group(
    group_id: str,
    body: dict,
    user_id: str = Depends(get_current_user_id),
):
    updated = await db.update_group(group_id, body)
    if not updated:
        raise HTTPException(status_code=404, detail="Group not found")
    return updated


@router.delete("/{group_id}", status_code=204)
async def delete_group(group_id: str, user_id: str = Depends(get_current_user_id)):
    await db.delete_group(group_id)
