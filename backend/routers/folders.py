"""
routers/folders.py — Drive folder tree sync and retrieval.
GET  /folders          → cached folder_index for the user
POST /folders/refresh  → force re-sync from Drive
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import FolderIndex, User
from routers.deps import get_current_user
from workers.tasks import sync_folder_tree

router = APIRouter()


@router.get("/")
async def get_folders(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Return cached folder tree."""
    stmt = select(FolderIndex).where(FolderIndex.user_id == current_user.id).order_by(FolderIndex.path)
    result = await db.execute(stmt)
    folders = result.scalars().all()

    return [
        {
            "id": str(f.id),
            "drive_folder_id": f.drive_folder_id,
            "name": f.name,
            "parent_drive_id": f.parent_drive_id,
            "path": f.path,
            "last_synced": f.last_synced.isoformat(),
        }
        for f in folders
    ]


@router.post("/refresh")
async def refresh_folders(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Enqueue a folder tree re-sync from Drive."""
    if not current_user.refresh_token_encrypted:
        raise HTTPException(401, "Drive not connected — please sign in again")

    sync_folder_tree.delay(str(current_user.id), current_user.refresh_token_encrypted)
    return {"ok": True, "message": "Folder sync enqueued — refresh in a moment."}
