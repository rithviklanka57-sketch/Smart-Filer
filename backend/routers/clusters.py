"""
routers/clusters.py — Cluster suggestions: accept (create folder + move) or dismiss.
GET  /clusters          → pending cluster suggestions
POST /clusters/:id/accept  → create folder + move members
POST /clusters/:id/dismiss → mark dismissed
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Cluster, Document, User
from routers.deps import get_current_user
from services.drive import refresh_access_token, create_folder, upload_file

router = APIRouter()


@router.get("/")
async def list_clusters(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Cluster).where(
        Cluster.user_id == current_user.id,
        Cluster.status == "suggested",
    ).order_by(Cluster.created_at.desc())
    result = await db.execute(stmt)
    clusters = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "topic_label": c.topic_label,
            "suggested_folder_name": c.suggested_folder_name,
            "member_count": len(c.member_document_ids),
            "member_document_ids": c.member_document_ids,
            "created_at": c.created_at.isoformat(),
        }
        for c in clusters
    ]


class AcceptRequest(BaseModel):
    folder_name: str  # user can edit the suggested name
    parent_folder_id: str | None = None


@router.post("/{cluster_id}/accept")
async def accept_cluster(
    cluster_id: UUID,
    body: AcceptRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Create the Drive folder and move all member documents into it."""
    stmt = select(Cluster).where(
        Cluster.id == cluster_id, Cluster.user_id == current_user.id
    )
    result = await db.execute(stmt)
    cluster = result.scalar_one_or_none()
    if not cluster:
        raise HTTPException(404, "Cluster not found")
    if cluster.status != "suggested":
        raise HTTPException(400, "Cluster already processed")

    if not current_user.refresh_token_encrypted:
        raise HTTPException(401, "Drive not connected")

    access_token = await refresh_access_token(current_user.refresh_token_encrypted)

    # Create the new Drive folder
    folder = await create_folder(access_token, body.folder_name, body.parent_folder_id)
    cluster.created_folder_id = folder["id"]
    cluster.status = "accepted"
    cluster.suggested_folder_name = body.folder_name

    # Upload/move each member document
    for doc_id_str in cluster.member_document_ids:
        doc_stmt = select(Document).where(Document.id == UUID(doc_id_str))
        doc_result = await db.execute(doc_stmt)
        doc = doc_result.scalar_one_or_none()
        if doc and doc.status != "placed":
            # Upload to new folder
            file_bytes = (doc.extracted_text or "").encode()
            drive_result = await upload_file(
                access_token,
                doc.filename,
                file_bytes,
                doc.mime_type or "application/octet-stream",
                folder["id"],
            )
            doc.drive_file_id = drive_result["id"]
            doc.status = "placed"

    await db.commit()
    return {
        "ok": True,
        "folder_id": folder["id"],
        "folder_name": body.folder_name,
        "member_count": len(cluster.member_document_ids),
    }


@router.post("/{cluster_id}/dismiss")
async def dismiss_cluster(
    cluster_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Cluster).where(
        Cluster.id == cluster_id, Cluster.user_id == current_user.id
    )
    result = await db.execute(stmt)
    cluster = result.scalar_one_or_none()
    if not cluster:
        raise HTTPException(404, "Cluster not found")

    cluster.status = "dismissed"
    await db.commit()
    return {"ok": True}
