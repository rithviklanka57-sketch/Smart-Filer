"""
workers/tasks.py — Celery tasks for async document processing pipeline.
Each task updates the document status so the frontend can track progress via WebSocket.

Phase 7 note: original file bytes are preserved in STORE_DIR/<document_id><ext>
so the /confirm endpoint can upload the real file to Drive (not just extracted text).
The Celery temp upload file is still deleted after reading.
"""
import asyncio
import logging
import os
import shutil
from pathlib import Path
from uuid import UUID

from workers.celery_app import celery_app
from config import settings

logger = logging.getLogger(__name__)

# Permanent per-document file store (survives until Drive upload confirms)
STORE_DIR = os.path.join(settings.TEMP_DIR, "store")


def _get_stored_path(document_id: str, filename: str) -> str:
    """Return the permanent store path for a document's original bytes."""
    os.makedirs(STORE_DIR, exist_ok=True)
    ext = Path(filename).suffix
    return os.path.join(STORE_DIR, f"{document_id}{ext}")


def delete_stored_file(document_id: str, filename: str) -> None:
    """Remove the stored original after successful Drive upload."""
    path = _get_stored_path(document_id, filename)
    if os.path.exists(path):
        os.unlink(path)
        logger.info("Deleted stored file: %s", path)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def process_document(self, document_id: str, user_id: str, file_path: str, filename: str, mime_type: str):
    """
    Full analysis pipeline for a single document:
    1. Copy original bytes to permanent store (for Drive upload on /confirm)
    2. Extract text from temp file
    3. LLM classify + summarize
    4. Generate embedding
    5. Run placement matching
    6. Run clustering check
    7. Delete temp upload file (permanent store is kept until /confirm)
    """
    try:
        # ── Preserve original bytes BEFORE any processing ─────────────────────
        stored_path = _get_stored_path(document_id, filename)
        shutil.copy2(file_path, stored_path)
        logger.info("Stored original file: %s", stored_path)

        _run_async(_async_process_document(document_id, user_id, file_path, filename, mime_type))
    except Exception as exc:
        logger.error("process_document failed for %s: %s", document_id, exc)
        _run_async(_update_status(document_id, "error", str(exc)))
        raise self.retry(exc=exc)
    finally:
        # Always clean up temp upload file; permanent store is kept separately
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.info("Cleaned up temp file: %s", file_path)


async def _update_status(document_id: str, status: str, error_msg: str = None):
    from database import AsyncSessionLocal
    from models import Document
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        stmt = select(Document).where(Document.id == UUID(document_id))
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()
        if doc:
            doc.status = status
            if error_msg:
                doc.error_message = error_msg
            await db.commit()
            # Push live status update via WebSocket
            await _ws_push(str(doc.user_id), document_id, status)


async def _ws_push(user_id: str, document_id: str, status: str):
    """Send a live status event to the user's WebSocket connection (if open)."""
    try:
        from routers.documents import manager
        await manager.send(user_id, {"document_id": document_id, "status": status})
    except Exception:
        pass  # WS not connected — frontend falls back to polling


async def _async_process_document(
    document_id: str, user_id: str, file_path: str, filename: str, mime_type: str
):
    from database import AsyncSessionLocal
    from models import Document
    from sqlalchemy import select
    from services.extraction import extract_text
    from services.llm import classify_document
    from services.embeddings import embed_text
    from services.placement import find_best_placement
    from services.clustering import detect_and_create_clusters

    async with AsyncSessionLocal() as db:
        # ── Fetch doc ─────────────────────────────────────────────────────────
        stmt = select(Document).where(Document.id == UUID(document_id))
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            logger.error("Document %s not found", document_id)
            return

        # ── Step 1: Extract text ──────────────────────────────────────────────
        doc.status = "extracting"
        await db.commit()
        await _ws_push(user_id, document_id, "extracting")

        import aiofiles
        async with aiofiles.open(file_path, "rb") as f:
            file_bytes = await f.read()

        extracted = extract_text(file_bytes, filename, mime_type)
        doc.extracted_text = extracted or "(no text extracted)"
        # Store the path to the preserved original so /confirm can retrieve it
        doc.stored_file_path = _get_stored_path(document_id, filename)

        # ── Step 2: LLM classification ────────────────────────────────────────
        doc.status = "classifying"
        await db.commit()
        await _ws_push(user_id, document_id, "classifying")

        if extracted:
            classification = classify_document(extracted)
            doc.doc_type = classification.get("doc_type", "unknown")
            doc.summary = classification.get("summary", "")
            doc.entities = classification.get("entities", {})
            doc.suggested_topic = classification.get("suggested_topic", "")

        # ── Step 3: Embedding ─────────────────────────────────────────────────
        embed_input = f"{doc.summary or ''} {doc.suggested_topic or ''} {doc.doc_type or ''}"
        embedding = await embed_text(embed_input.strip())
        if embedding:
            doc.embedding = embedding

        # ── Step 4: Placement matching ────────────────────────────────────────
        if embedding:
            placement_result = await find_best_placement(
                db, UUID(user_id), embedding, doc.summary or filename
            )
            doc.status = "needs_input" if placement_result["mode"] != "auto" else "pending"
        else:
            placement_result = None
            doc.status = "needs_input"

        await db.commit()
        await _ws_push(user_id, document_id, doc.status)

        # ── Step 5: Clustering ────────────────────────────────────────────────
        await detect_and_create_clusters(db, UUID(user_id))

        logger.info("Processed document %s: type=%s, status=%s", document_id, doc.doc_type, doc.status)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def sync_folder_tree(self, user_id: str, refresh_token_encrypted: str):
    """Sync Drive folder tree into folder_index table."""
    try:
        _run_async(_async_sync_folders(user_id, refresh_token_encrypted))
    except Exception as exc:
        logger.error("sync_folder_tree failed for user %s: %s", user_id, exc)
        raise self.retry(exc=exc)


async def _async_sync_folders(user_id: str, refresh_token_encrypted: str):
    from database import AsyncSessionLocal
    from models import FolderIndex
    from services.drive import refresh_access_token, list_folders
    from services.embeddings import embed_text
    from sqlalchemy import delete

    access_token = await refresh_access_token(refresh_token_encrypted)
    folders = await list_folders(access_token)

    # Build id→name map for path resolution
    id_to_name: dict[str, str] = {f["id"]: f["name"] for f in folders}
    id_to_parents: dict[str, list[str]] = {f["id"]: f.get("parents", []) for f in folders}

    def build_path(folder_id: str, depth: int = 0) -> str:
        if depth > 10:
            return id_to_name.get(folder_id, folder_id)
        parents = id_to_parents.get(folder_id, [])
        if not parents or parents[0] not in id_to_name:
            return id_to_name.get(folder_id, folder_id)
        return build_path(parents[0], depth + 1) + "/" + id_to_name.get(folder_id, folder_id)

    async with AsyncSessionLocal() as db:
        # Clear existing index for user
        await db.execute(delete(FolderIndex).where(FolderIndex.user_id == UUID(user_id)))

        for folder in folders:
            path = build_path(folder["id"])
            embedding = await embed_text(f"{folder['name']} {path}")
            fi = FolderIndex(
                user_id=UUID(user_id),
                drive_folder_id=folder["id"],
                name=folder["name"],
                parent_drive_id=(folder.get("parents") or [None])[0],
                path=path,
                embedding=embedding,
            )
            db.add(fi)

        await db.commit()
        logger.info("Synced %d folders for user %s", len(folders), user_id)
