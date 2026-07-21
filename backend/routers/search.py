"""
routers/search.py — Semantic search over filed documents.
GET /search?q=...&doc_type=...&limit=20
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from database import get_db
from models import Document, FolderIndex, User
from routers.deps import get_current_user
from services.embeddings import embed_text, cosine_similarity

router = APIRouter()


@router.get("/")
async def semantic_search(
    q: str = Query(..., min_length=1),
    doc_type: str | None = None,
    limit: int = Query(default=20, le=100),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Semantic search: embed the query, score against document embeddings,
    return top results with snippet, path, and Drive deep link.
    """
    query_embedding = await embed_text(q)

    stmt = select(Document).where(
        Document.user_id == current_user.id,
        Document.status == "placed",
        Document.embedding.isnot(None),
    )
    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)

    result = await db.execute(stmt)
    docs = result.scalars().all()

    if not query_embedding:
        # Fallback: simple keyword search in summary/filename
        keyword = q.lower()
        scored = [
            d for d in docs
            if keyword in (d.filename or "").lower()
            or keyword in (d.summary or "").lower()
        ]
        scored = scored[:limit]
    else:
        scored_docs = []
        for doc in docs:
            sim = cosine_similarity(query_embedding, list(doc.embedding))
            scored_docs.append((sim, doc))
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        scored = [d for _, d in scored_docs[:limit]]

    # Fetch folder paths
    folder_ids = {d.drive_file_id for d in scored if d.drive_file_id}
    folder_map: dict[str, str] = {}

    results = []
    for doc in scored:
        snippet = ""
        if doc.extracted_text:
            # Find where query term appears
            idx = (doc.extracted_text or "").lower().find(q.lower())
            if idx >= 0:
                snippet = doc.extracted_text[max(0, idx - 80): idx + 160].strip()
            else:
                snippet = (doc.extracted_text or "")[:240].strip()

        results.append({
            "id": str(doc.id),
            "filename": doc.filename,
            "doc_type": doc.doc_type,
            "summary": doc.summary,
            "snippet": snippet,
            "drive_file_id": doc.drive_file_id,
            "drive_link": f"https://drive.google.com/file/d/{doc.drive_file_id}/view" if doc.drive_file_id else None,
            "created_at": doc.created_at.isoformat(),
        })

    return {"query": q, "results": results, "total": len(results)}
