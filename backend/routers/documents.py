"""
routers/documents.py — Upload, status, clarifying answers, and placement confirmation.
"""
import os
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from database import get_db
from models import Document, Placement, User
from routers.deps import get_current_user
from services.drive import refresh_access_token, upload_file, list_files_in_folder
from services.placement import find_best_placement, record_placement_rule
from workers.tasks import process_document

logger = logging.getLogger(__name__)
router = APIRouter()

# ── WebSocket manager for live job updates ────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}  # user_id → ws

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self.active[user_id] = ws

    def disconnect(self, user_id: str):
        self.active.pop(user_id, None)

    async def send(self, user_id: str, data: dict):
        ws = self.active.get(user_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(user_id)


manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def ws_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive pings
    except WebSocketDisconnect:
        manager.disconnect(user_id)


# ── Upload ─────────────────────────────────────────────────────────────────────
@router.post("/upload")
async def upload_document(
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if file.size and file.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.MAX_UPLOAD_MB}MB limit")

    # Save to temp file (cleaned up by Celery task after processing)
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    suffix = os.path.splitext(file.filename or "upload")[1]
    with tempfile.NamedTemporaryFile(
        dir=settings.TEMP_DIR, suffix=suffix, delete=False
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    doc = Document(
        user_id=current_user.id,
        filename=file.filename or "upload",
        mime_type=file.content_type,
        status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Enqueue background processing
    process_document.delay(
        str(doc.id),
        str(current_user.id),
        tmp_path,
        file.filename or "upload",
        file.content_type or "application/octet-stream",
    )

    return {"document_id": str(doc.id), "status": "pending"}


# ── Status + placement result ──────────────────────────────────────────────────
@router.get("/{document_id}")
async def get_document(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document).where(
        Document.id == document_id, Document.user_id == current_user.id
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    payload: dict = {
        "id": str(doc.id),
        "filename": doc.filename,
        "status": doc.status,
        "doc_type": doc.doc_type,
        "summary": doc.summary,
        "entities": doc.entities,
        "suggested_topic": doc.suggested_topic,
        "error_message": doc.error_message,
        "created_at": doc.created_at.isoformat(),
    }

    # Include placement suggestion if ready
    if doc.embedding and doc.status in ("needs_input", "pending"):
        placement = await find_best_placement(
            db, current_user.id, list(doc.embedding), doc.summary or doc.filename
        )
        payload["placement"] = placement

    return payload


@router.get("/")
async def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
):
    stmt = select(Document).where(Document.user_id == current_user.id)
    if status:
        stmt = stmt.where(Document.status == status)
    stmt = stmt.order_by(Document.created_at.desc())
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "status": d.status,
            "doc_type": d.doc_type,
            "summary": d.summary,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


# ── Answer clarifying question ────────────────────────────────────────────────
class AnswerRequest(BaseModel):
    chosen_folder_id: str
    chosen_folder_name: str


@router.post("/{document_id}/answer")
async def answer_question(
    document_id: UUID,
    body: AnswerRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """User answered the clarifying question — record chosen folder as suggestion."""
    stmt = select(Document).where(
        Document.id == document_id, Document.user_id == current_user.id
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    placement = Placement(
        document_id=doc.id,
        suggested_folder_id=body.chosen_folder_id,
        confidence=0.75,  # user answered → treat as medium confidence
        why_explanation=f"You selected: {body.chosen_folder_name}",
    )
    db.add(placement)
    doc.status = "pending"  # ready to confirm
    await db.commit()

    return {"ok": True, "suggested_folder_id": body.chosen_folder_id}


# ── Confirm placement (Drive upload) ─────────────────────────────────────────
class ConfirmRequest(BaseModel):
    folder_id: str
    folder_name: str
    replace_file_id: str | None = None  # for duplicate Replace option


@router.post("/{document_id}/confirm")
async def confirm_placement(
    document_id: UUID,
    body: ConfirmRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Upload the file to Drive. Never auto-commits — always requires this explicit call.
    Checks for duplicates first.
    """
    stmt = select(Document).where(
        Document.id == document_id, Document.user_id == current_user.id
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    if not current_user.refresh_token_encrypted:
        raise HTTPException(401, "Drive not connected — please sign in again")

    access_token = await refresh_access_token(current_user.refresh_token_encrypted)

    # ── Duplicate check ─────────────────────────────────────────────────────
    if not body.replace_file_id:
        existing = await list_files_in_folder(access_token, body.folder_id)
        duplicates = [f for f in existing if f["name"] == doc.filename]
        if duplicates:
            return {
                "duplicate": True,
                "existing_file": duplicates[0],
                "options": ["replace", "keep_both", "version"],
            }

    # ── Read original file bytes from permanent store ────────────────────────
    import aiofiles
    from workers.tasks import delete_stored_file

    if doc.stored_file_path and os.path.exists(doc.stored_file_path):
        # Happy path: upload the original file bytes to Drive
        async with aiofiles.open(doc.stored_file_path, "rb") as f:
            file_bytes = await f.read()
        mime_type_to_use = doc.mime_type or "application/octet-stream"
    else:
        # Graceful fallback: upload extracted text if original no longer exists
        logger.warning(
            "Original stored file not found for doc %s (path: %s) — uploading extracted text",
            doc.id, doc.stored_file_path,
        )
        file_bytes = (doc.extracted_text or "").encode("utf-8")
        mime_type_to_use = "text/plain"

    drive_result = await upload_file(
        access_token,
        doc.filename,
        file_bytes,
        mime_type_to_use,
        body.folder_id,
    )

    doc.drive_file_id = drive_result["id"]
    doc.status = "placed"

    # Record placement for audit + learning loop
    placement = Placement(
        document_id=doc.id,
        final_folder_id=body.folder_id,
        confidence=1.0,
        was_corrected=False,
    )
    db.add(placement)

    # Feed into learning loop if embedding exists
    if doc.embedding:
        await record_placement_rule(
            db,
            current_user.id,
            list(doc.embedding),
            doc.suggested_topic or doc.doc_type or doc.filename,
            body.folder_id,
            body.folder_name,
        )

    await db.commit()

    # ── Clean up stored original now that Drive has the file ──────────────────
    delete_stored_file(str(doc.id), doc.filename)

    return {
        "ok": True,
        "drive_file_id": drive_result["id"],
        "web_view_link": drive_result.get("webViewLink"),
    }
