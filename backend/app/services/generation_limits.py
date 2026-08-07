"""Per-user concurrent generation caps by plan tier (对标 Yapper pricing Limits)."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.services.entitlements import user_role

# Yapper Creator plan advertises 10 concurrent generations.
PLAN_CONCURRENT: dict[str, int] = {
    "guest": 1,
    "free": 2,
    "starter": 3,
    "personal": 5,
    "creator": 10,
    "pro": 15,
    "max": 15,
    "enterprise": 20,
    "admin": 30,
}

_ACTIVE_STATUSES = ("queued", "analyzing", "routing", "generating", "uploading")


def concurrent_cap_for_role(role: str | None) -> int:
    r = user_role(role)
    return PLAN_CONCURRENT.get(r, PLAN_CONCURRENT["free"])


async def count_active_generations(db: AsyncSession, user_id: int) -> int:
    r = await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id,
            Task.status.in_(_ACTIVE_STATUSES),
        )
    )
    return int(r.scalar() or 0)


async def enforce_concurrent_limit(
    db: AsyncSession,
    user_id: int,
    role: str | None,
    *,
    exclude_task_id: str | None = None,
) -> None:
    cap = concurrent_cap_for_role(role)
    if cap <= 0:
        return
    q = select(func.count()).select_from(Task).where(
        Task.user_id == user_id,
        Task.status.in_(_ACTIVE_STATUSES),
    )
    if exclude_task_id:
        q = q.where(Task.task_id != exclude_task_id)
    active = int((await db.execute(q)).scalar() or 0)
    if active >= cap:
        raise HTTPException(
            status_code=429,
            detail=f"并发任务已达上限 ({active}/{cap})，请等待当前任务完成或升级套餐",
        )
