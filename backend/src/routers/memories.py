"""Agent memory routes."""

from fastapi import APIRouter, Depends, HTTPException

from src.deps import get_current_user_id
from src.services import supabase_client as db

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("")
async def list_memories(
    scope: str = "",
    user_id: str = Depends(get_current_user_id),
):
    return await db.get_memories(user_id, scope=scope)


@router.patch("/{memory_id}")
async def update_memory(
    memory_id: str,
    body: dict,
    user_id: str = Depends(get_current_user_id),
):
    updated = await db.update_memory(memory_id, body)
    if not updated:
        raise HTTPException(status_code=404, detail="Memory not found")
    return updated


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user_id),
):
    await db.delete_memory(memory_id)
