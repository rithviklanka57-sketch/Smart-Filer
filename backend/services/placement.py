"""
services/placement.py — Confidence-gated folder matching + learning loop short-circuit.
Thresholds are loaded from config — NOT hardcoded here.
"""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from models import FolderIndex, PlacementRule
from services.embeddings import cosine_similarity
from services.llm import generate_clarifying_question, explain_placement

logger = logging.getLogger(__name__)


async def find_best_placement(
    db: AsyncSession,
    user_id: UUID,
    doc_embedding: list[float] | None,
    doc_summary: str,
) -> dict:
    """
    Phase 5 logic: check learning-loop rules first, then folder similarity.
    Returns a placement result dict with:
      - mode: "auto" | "question" | "fallback"
      - candidates: list of {folder_id, folder_name, path, confidence}
      - question / options (if mode == "question")
      - why: explanation string
    """
    # ── Step 1: Check placement rules (learning loop, Phase 8) ───────────────
    if doc_embedding:
        rule_result = await _check_placement_rules(db, user_id, doc_embedding)
        if rule_result:
            return rule_result

    # ── Step 2: Score all indexed folders ────────────────────────────────────
    stmt = select(FolderIndex).where(FolderIndex.user_id == user_id)
    result = await db.execute(stmt)
    folders = result.scalars().all()

    if not folders:
        return {"mode": "fallback", "candidates": [], "why": "No folders found in your Drive cache. Click Settings to sync your Drive folders."}

    scored = []
    for folder in folders:
        if doc_embedding and folder.embedding:
            sim = cosine_similarity(doc_embedding, list(folder.embedding))
        else:
            sim = 0.0
        scored.append({
            "folder_id": folder.drive_folder_id,
            "folder_name": folder.name,
            "path": folder.path or folder.name,
            "confidence": sim,
        })

    scored.sort(key=lambda x: x["confidence"], reverse=True)
    top = scored[:5]
    best = top[0] if top else None

    if not best:
        return {"mode": "fallback", "candidates": top, "why": "No matching folders found."}

    best_conf = best["confidence"]

    # ── Step 3: Apply confidence bands ──────────────────────────────────────
    if best_conf >= settings.PLACEMENT_AUTO_THRESHOLD:
        why = explain_placement(doc_summary, best["path"], best_conf)
        return {
            "mode": "auto",
            "candidates": top,
            "why": why,
        }
    elif best_conf >= settings.PLACEMENT_QUESTION_THRESHOLD:
        question_data = generate_clarifying_question(doc_summary, top)
        return {
            "mode": "question",
            "candidates": top,
            "question": question_data.get("question", "Which folder should this go in?"),
            "options": question_data.get("options", [c["path"] for c in top]),
            "why": f"Confidence {best_conf:.0%} — I need one more piece of info.",
        }
    else:
        return {
            "mode": "fallback",
            "candidates": top,
            "why": f"Low confidence ({best_conf:.0%}) — please choose or type a folder.",
        }


async def _check_placement_rules(
    db: AsyncSession, user_id: UUID, doc_embedding: list[float]
) -> Optional[dict]:
    """
    Check if any learned rule matches with ≥ RULE_MATCH_THRESHOLD similarity.
    Rules with ≥ RULE_CONFIDENCE_MIN_HITS are treated as high-confidence auto-suggestions.
    """
    stmt = select(PlacementRule).where(PlacementRule.user_id == user_id)
    result = await db.execute(stmt)
    rules = result.scalars().all()

    best_rule = None
    best_sim = 0.0
    for rule in rules:
        if rule.pattern_embedding:
            sim = cosine_similarity(doc_embedding, list(rule.pattern_embedding))
            if sim >= settings.RULE_MATCH_THRESHOLD and sim > best_sim:
                best_sim = sim
                best_rule = rule

    if best_rule:
        mode = "auto" if best_rule.hit_count >= settings.RULE_CONFIDENCE_MIN_HITS else "question"
        return {
            "mode": mode,
            "candidates": [{
                "folder_id": best_rule.target_folder_id,
                "folder_name": best_rule.target_folder_name or "Learned folder",
                "path": best_rule.target_folder_name or "Learned folder",
                "confidence": best_sim,
            }],
            "why": f"Based on your past choices ({best_rule.hit_count} similar files filed here).",
            "rule_id": str(best_rule.id),
        }
    return None


async def record_placement_rule(
    db: AsyncSession,
    user_id: UUID,
    doc_embedding: list[float],
    pattern_label: str,
    target_folder_id: str,
    target_folder_name: str,
) -> None:
    """Called on any manual override — stores/updates a placement rule."""
    # Check if a very similar rule already exists
    existing_result = await _check_placement_rules(db, user_id, doc_embedding)
    if existing_result and existing_result.get("rule_id"):
        # Increment hit count on the existing rule
        stmt = select(PlacementRule).where(
            PlacementRule.id == UUID(existing_result["rule_id"])
        )
        res = await db.execute(stmt)
        rule = res.scalar_one_or_none()
        if rule:
            rule.hit_count += 1
            await db.commit()
            return

    rule = PlacementRule(
        user_id=user_id,
        pattern_label=pattern_label,
        pattern_embedding=doc_embedding,
        target_folder_id=target_folder_id,
        target_folder_name=target_folder_name,
        hit_count=1,
    )
    db.add(rule)
    await db.commit()
