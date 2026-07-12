"""
Dashboard API — aggregated stats, recent items, models for the dashboard view.
In LOCAL_MODE, returns data for user_id=1 (local dev user).
"""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db import get_db
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.models.billing import UserBalance
from app.config import settings
from app.auth import resolve_user_id

router = APIRouter()


class DashboardStats(BaseModel):
    credits_remaining: int = 0
    assets_generated: int = 0
    recent_generations: int = 0
    success_rate: float = 0.0  # 0-100
    total_spent: int = 0


class RecentItem(BaseModel):
    task_id: str
    prompt: str
    media_type: str
    status: str
    model: Optional[str] = None
    thumbnail_url: Optional[str] = None
    media_url: Optional[str] = None
    duration: Optional[float] = None
    created_at: Optional[str] = None


class DashboardModel(BaseModel):
    name: str
    type: str  # image | video
    provider: str
    badge: Optional[str] = None


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_items: List[RecentItem]
    models: List[DashboardModel]


# ─── Model registry (matches frontend MODELS array) ──────

AVAILABLE_MODELS = [
    {"name": "Seedance 2.0", "type": "video", "provider": "ByteDance", "badge": "Pro"},
    {"name": "GPT Image 2", "type": "image", "provider": "OpenAI", "badge": "New"},
    {"name": "Kling 3.0", "type": "video", "provider": "Kuaishou", "badge": "Hot"},
    {"name": "Runway Gen-3", "type": "video", "provider": "Runway", "badge": None},
    {"name": "Flux 1.1 Pro", "type": "image", "provider": "Black Forest", "badge": None},
    {"name": "Veo 3.1", "type": "video", "provider": "Google", "badge": None},
    {"name": "Sora 2", "type": "video", "provider": "OpenAI", "badge": None},
    {"name": "WAN 2.1", "type": "video", "provider": "Alibaba", "badge": None},
    {"name": "LTX-2", "type": "video", "provider": "Lightricks", "badge": "Local"},
]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    """Aggregated dashboard data scoped to the effective account: logged-in
    users see their own stats/recent items; anonymous usage falls back to the
    shared guest account (0)."""

    # ─── Stats ──────────────────────────────────────────
    # Credit balance
    balance_result = await db.execute(
        select(UserBalance).where(UserBalance.user_id == user_id).limit(1)
    )
    balance = balance_result.scalar_one_or_none()

    # Task counts
    total_tasks_result = await db.execute(
        select(func.count(Task.id)).where(
            and_(Task.user_id == user_id,
                 Task.status != TaskStatus.CANCELLED)
        )
    )
    total_tasks = total_tasks_result.scalar() or 0

    completed_result = await db.execute(
        select(func.count(Task.id)).where(
            and_(Task.user_id == user_id, Task.status == TaskStatus.COMPLETED)
        )
    )
    completed = completed_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count(Task.id)).where(
            and_(Task.user_id == user_id, Task.status == TaskStatus.FAILED)
        )
    )
    failed = failed_result.scalar() or 0

    # Recent 7-day generations
    seven_days_ago = datetime.now(timezone.utc).replace(tzinfo=None)
    from datetime import timedelta
    seven_days_ago = seven_days_ago - timedelta(days=7)
    recent_count_result = await db.execute(
        select(func.count(Task.id)).where(
            and_(Task.user_id == user_id,
                 Task.created_at >= seven_days_ago,
                 Task.status != TaskStatus.CANCELLED)
        )
    )
    recent_count = recent_count_result.scalar() or 0

    success_rate = 0.0
    if completed + failed > 0:
        success_rate = round(completed / (completed + failed) * 100, 1)

    stats = DashboardStats(
        credits_remaining=(balance.credits + balance.daily_credits) if balance else 0,
        assets_generated=completed,
        recent_generations=recent_count,
        success_rate=success_rate,
        total_spent=balance.total_spent if balance else 0,
    )

    # ─── Recent Items ──────────────────────────────────
    tasks_result = await db.execute(
        select(Task)
        .where(and_(Task.user_id == user_id,
                    Task.status.in_([TaskStatus.COMPLETED, TaskStatus.GENERATING, TaskStatus.QUEUED])))
        .order_by(Task.updated_at.desc())
        .limit(limit)
    )
    tasks = tasks_result.scalars().all()

    recent_items = []
    for t in tasks:
        thumbnail = None
        media_url = None
        duration = None
        results = t.results
        if isinstance(results, str):
            import json as _json
            try:
                results = _json.loads(results)
            except Exception:
                results = None
        if isinstance(results, list) and results and isinstance(results[0], dict):
            r = results[0]
            media_url = r.get("url") or r.get("media_url")
            # Images have no separate thumbnail — fall back to the media itself.
            thumbnail = r.get("thumbnail") or media_url
            duration = r.get("duration")

        recent_items.append(RecentItem(
            task_id=t.task_id,
            prompt=t.prompt[:120] if t.prompt else "",
            media_type=t.media_type or "image",
            status=t.status,
            model=t.selected_model or t.requested_model,
            thumbnail_url=thumbnail,
            media_url=media_url,
            duration=duration,
            created_at=t.created_at.isoformat() if t.created_at else None,
        ))

    # ─── Models ─────────────────────────────────────────
    models = [DashboardModel(**m) for m in AVAILABLE_MODELS]

    return DashboardResponse(stats=stats, recent_items=recent_items, models=models)
