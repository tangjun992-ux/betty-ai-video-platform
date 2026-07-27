"""
Moderation admin API — list pending community reports and approve / takedown.
Requires admin (preferred) or at least an authenticated user.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.db import get_db
from app.models.user import User
from app.services.moderation import score_prompt

router = APIRouter()

_MOD_DDL = (
    "CREATE TABLE IF NOT EXISTS gallery_moderation "
    "(item_key TEXT PRIMARY KEY, reports INTEGER NOT NULL DEFAULT 0, "
    "hidden INTEGER NOT NULL DEFAULT 0, reason TEXT, "
    "status TEXT NOT NULL DEFAULT 'pending', risk_score REAL NOT NULL DEFAULT 0, "
    "categories TEXT)"
)


async def _ensure_mod_table(db: AsyncSession) -> None:
    await db.execute(text(_MOD_DDL))
    # Best-effort column upgrades for older SQLite schemas.
    for ddl in (
        "ALTER TABLE gallery_moderation ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'",
        "ALTER TABLE gallery_moderation ADD COLUMN risk_score REAL NOT NULL DEFAULT 0",
        "ALTER TABLE gallery_moderation ADD COLUMN categories TEXT",
    ):
        try:
            await db.execute(text(ddl))
        except Exception:
            pass


async def _require_moderator(
    user: User = Depends(require_admin),
) -> User:
    """Moderation actions require admin privileges."""
    return user


class ScoreRequest(BaseModel):
    text: str = Field(..., min_length=1)


class DecisionRequest(BaseModel):
    reason: str | None = None


@router.get("/pending", summary="待审举报列表")
async def list_pending(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_moderator),
):
    await _ensure_mod_table(db)
    rows = await db.execute(
        text(
            "SELECT item_key, reports, hidden, reason, "
            "COALESCE(status, CASE WHEN hidden=1 THEN 'hidden' ELSE 'pending' END) AS status, "
            "COALESCE(risk_score, 0) AS risk_score, categories "
            "FROM gallery_moderation "
            "WHERE COALESCE(status, 'pending') = 'pending' OR (hidden = 0 AND reports > 0) "
            "ORDER BY reports DESC, item_key ASC LIMIT :lim"
        ),
        {"lim": min(max(limit, 1), 200)},
    )
    items = []
    for r in rows.mappings().all():
        cats = []
        if r["categories"]:
            cats = [c for c in str(r["categories"]).split(",") if c]
        items.append({
            "item_key": r["item_key"],
            "reports": int(r["reports"] or 0),
            "hidden": bool(r["hidden"]),
            "reason": r["reason"],
            "status": r["status"] or "pending",
            "risk_score": float(r["risk_score"] or 0),
            "categories": cats,
        })
    return {"items": items, "count": len(items)}


@router.post("/{item_key}/approve", summary="人工通过（恢复展示）")
async def approve_item(
    item_key: str,
    body: DecisionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_require_moderator),
):
    await _ensure_mod_table(db)
    reason = (body.reason if body else None) or f"approved_by:{user.username}"
    await db.execute(
        text(
            "INSERT INTO gallery_moderation (item_key, reports, hidden, reason, status) "
            "VALUES (:k, 0, 0, :r, 'approved') "
            "ON CONFLICT(item_key) DO UPDATE SET hidden = 0, status = 'approved', reason = :r"
        ),
        {"k": item_key, "r": reason},
    )
    await db.commit()
    return {"item_key": item_key, "status": "approved", "hidden": False}


@router.post("/{item_key}/takedown", summary="人工下架")
async def takedown_item(
    item_key: str,
    body: DecisionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_require_moderator),
):
    await _ensure_mod_table(db)
    reason = (body.reason if body else None) or f"takedown_by:{user.username}"
    await db.execute(
        text(
            "INSERT INTO gallery_moderation (item_key, reports, hidden, reason, status) "
            "VALUES (:k, 1, 1, :r, 'takedown') "
            "ON CONFLICT(item_key) DO UPDATE SET hidden = 1, status = 'takedown', reason = :r"
        ),
        {"k": item_key, "r": reason},
    )
    await db.commit()
    return {"item_key": item_key, "status": "takedown", "hidden": True}


@router.post("/score", summary="对文本打风险分（调试/运营）")
async def score_text(req: ScoreRequest, _: User = Depends(_require_moderator)):
    return score_prompt(req.text)


@router.get("/admin-only/ping", summary="管理员探针")
async def admin_ping(_: User = Depends(require_admin)):
    return {"ok": True, "role": "admin"}
