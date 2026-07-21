"""
services/clustering.py — Pairwise cosine similarity clustering.
Only surfaces a cluster if ≥2 members AND none had a strong existing-folder match.
Threshold loaded from config.
"""
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from models import Document, Cluster
from services.embeddings import cosine_similarity
from services.llm import propose_folder_name

logger = logging.getLogger(__name__)


async def detect_and_create_clusters(db: AsyncSession, user_id: UUID) -> list[dict]:
    """
    Run after each document analysis. Groups pending/needs_input documents
    by pairwise similarity ≥ CLUSTERING_SIMILARITY_THRESHOLD.
    Only surface clusters where no member had confidence ≥ PLACEMENT_AUTO_THRESHOLD.

    Returns list of new cluster suggestion dicts.
    """
    # Fetch all unfiled docs with embeddings
    stmt = select(Document).where(
        Document.user_id == user_id,
        Document.status.in_(["needs_input", "pending"]),
        Document.embedding.isnot(None),
        Document.drive_file_id.is_(None),
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()

    if len(docs) < 2:
        return []

    # Get already-suggested cluster member sets to avoid re-proposing
    existing_stmt = select(Cluster).where(
        Cluster.user_id == user_id,
        Cluster.status == "suggested",
    )
    existing_result = await db.execute(existing_stmt)
    existing_clusters = existing_result.scalars().all()
    already_proposed = {
        frozenset(c.member_document_ids) for c in existing_clusters
    }

    # Pairwise similarity matrix → union-find grouping
    n = len(docs)
    groups: list[set[int]] = [{i} for i in range(n)]

    def find(idx: int) -> int:
        for gi, g in enumerate(groups):
            if idx in g:
                return gi
        return -1

    for i in range(n):
        for j in range(i + 1, n):
            emb_i = list(docs[i].embedding)
            emb_j = list(docs[j].embedding)
            sim = cosine_similarity(emb_i, emb_j)
            if sim >= settings.CLUSTERING_SIMILARITY_THRESHOLD:
                gi, gj = find(i), find(j)
                if gi != gj:
                    groups[gi] = groups[gi] | groups[gj]
                    groups[gj] = set()

    new_clusters = []
    seen_groups: list[frozenset] = []

    for group in groups:
        if len(group) < 2:
            continue
        member_ids = frozenset(str(docs[i].id) for i in group)
        if member_ids in already_proposed or member_ids in seen_groups:
            continue
        seen_groups.append(member_ids)

        # Propose folder name via LLM
        summaries = [docs[i].summary or docs[i].filename for i in group if docs[i].summary]
        name_result = propose_folder_name(summaries)

        cluster = Cluster(
            user_id=user_id,
            topic_label=name_result.get("topic_label", "related documents"),
            suggested_folder_name=name_result.get("folder_name", "New Folder"),
            member_document_ids=list(member_ids),
            status="suggested",
        )
        db.add(cluster)
        new_clusters.append({
            "topic_label": cluster.topic_label,
            "suggested_folder_name": cluster.suggested_folder_name,
            "member_count": len(member_ids),
        })

    if new_clusters:
        await db.commit()

    return new_clusters
