"""
routers/rules.py — View and delete learned placement rules (settings page).
GET    /rules        → list user's placement rules
DELETE /rules/:id    → remove a rule
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import PlacementRule, User
from routers.deps import get_current_user

router = APIRouter()


@router.get("/")
async def list_rules(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PlacementRule).where(PlacementRule.user_id == current_user.id).order_by(
        PlacementRule.hit_count.desc()
    )
    result = await db.execute(stmt)
    rules = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "pattern_label": r.pattern_label,
            "target_folder_name": r.target_folder_name,
            "hit_count": r.hit_count,
            "created_at": r.created_at.isoformat(),
        }
        for r in rules
    ]


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PlacementRule).where(
        PlacementRule.id == rule_id, PlacementRule.user_id == current_user.id
    )
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")
    await db.delete(rule)
    await db.commit()
    return {"ok": True}
