"""Plan-tier concurrent generation quotas — 对标 Yapper Starter/Personal/Creator/Max.

Limits (active queued+generating jobs per user):
  guest     2
  starter / free  4
  personal  6
  creator   10
  max / pro / admin / enterprise  40

Redis SET tracks in-flight slots; DB count of queued+generating is the
authoritative fallback so a Redis blip cannot silently over-admit. Over-limit
returns HTTP 429 with retry_after + upgrade hint — never a silent queue.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("queued", "generating")

# Plan / role → max concurrent jobs. Guest 1–2 → we take the honest upper bound (2).
PLAN_CONCURRENCY: dict[str, int] = {
    "guest": 2,
    "system": 2,
    "free": 4,
    "starter": 4,
    "personal": 6,
    "creator": 10,
    "pro": 40,
    "max": 40,
    "enterprise": 40,
    "admin": 40,
}

NEXT_PLAN: dict[str, tuple[str, str]] = {
    "guest": ("starter", "注册并升级 Starter 可同时跑 4 个任务"),
    "system": ("starter", "注册并升级 Starter 可同时跑 4 个任务"),
    "free": ("personal", "升级 Personal 可同时跑 6 个任务"),
    "starter": ("personal", "升级 Personal 可同时跑 6 个任务"),
    "personal": ("creator", "升级 Creator 可同时跑 10 个任务"),
    "creator": ("max", "升级 Max 可同时跑 40 个任务"),
}

_SLOT_TTL_S = 2 * 60 * 60  # 2h — leaked slots expire even if a worker dies
_KEY_PREFIX = "betty:conc:u:"

_local_lock = threading.Lock()
_local_slots: dict[int, set[str]] = {}


class ConcurrencyLimitError(Exception):
    def __init__(
        self,
        *,
        used: int,
        limit: int,
        role: str,
        retry_after: int = 30,
        upgrade_plan: str | None = None,
        upgrade_hint: str = "",
    ):
        self.used = used
        self.limit = limit
        self.role = role
        self.retry_after = retry_after
        self.upgrade_plan = upgrade_plan
        self.upgrade_hint = upgrade_hint
        super().__init__(
            f"并发已满（{used}/{limit}）。{upgrade_hint or '请等待进行中的任务完成后再提交。'}"
        )


def concurrency_limit(role: str | None) -> int:
    from app.services.entitlements import user_role

    r = user_role(role)
    if r in PLAN_CONCURRENCY:
        return PLAN_CONCURRENCY[r]
    # Unknown roles inherit the nearest rank's cap.
    return PLAN_CONCURRENCY.get("free", 4)


def upgrade_hint_for(role: str | None) -> tuple[str | None, str]:
    from app.services.entitlements import user_role

    r = user_role(role)
    if r in ("pro", "max", "admin", "enterprise"):
        return None, "已达最高并发档，请等待进行中的任务完成。"
    plan, hint = NEXT_PLAN.get(r, NEXT_PLAN["free"])
    return plan, hint


def concurrency_http_exception(err: ConcurrencyLimitError) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail={
            "error": "concurrency_limit",
            "message": str(err),
            "retry_after": err.retry_after,
            "concurrent_used": err.used,
            "concurrent_limit": err.limit,
            "role": err.role,
            "upgrade_url": "/pricing",
            "upgrade_plan": err.upgrade_plan,
            "upgrade_hint": err.upgrade_hint,
        },
        headers={"Retry-After": str(err.retry_after)},
    )


def _redis():
    try:
        import redis
        from app.config import settings

        return redis.Redis.from_url(
            settings.REDIS_URL, decode_responses=True, socket_timeout=1,
        )
    except Exception:
        return None


def _redis_key(user_id: int) -> str:
    return f"{_KEY_PREFIX}{int(user_id)}"


def _local_count(user_id: int) -> int:
    with _local_lock:
        return len(_local_slots.get(int(user_id), set()))


def _local_add(user_id: int, slot_id: str) -> None:
    uid = int(user_id)
    with _local_lock:
        _local_slots.setdefault(uid, set()).add(slot_id)


def _local_discard(user_id: int, slot_id: str) -> None:
    uid = int(user_id)
    with _local_lock:
        s = _local_slots.get(uid)
        if s:
            s.discard(slot_id)
            if not s:
                _local_slots.pop(uid, None)


def redis_slot_count(user_id: int) -> int:
    r = _redis()
    if r is None:
        return _local_count(user_id)
    try:
        return int(r.scard(_redis_key(user_id)) or 0)
    except Exception:
        return _local_count(user_id)


def _add_slot(user_id: int, slot_id: str) -> None:
    r = _redis()
    if r is None:
        _local_add(user_id, slot_id)
        return
    try:
        key = _redis_key(user_id)
        r.sadd(key, slot_id)
        r.expire(key, _SLOT_TTL_S)
        _local_add(user_id, slot_id)  # keep process view in sync for tests
    except Exception as e:
        logger.warning("concurrency redis add failed: %s", e)
        _local_add(user_id, slot_id)


def release_slot(user_id: int | None, slot_id: str | None) -> None:
    """Release a previously acquired slot. Safe to call twice / with missing ids."""
    if user_id is None or not slot_id:
        return
    r = _redis()
    if r is not None:
        try:
            r.srem(_redis_key(int(user_id)), slot_id)
        except Exception as e:
            logger.warning("concurrency redis release failed: %s", e)
    _local_discard(int(user_id), slot_id)


def release_slot_sync(user_id: int | None, slot_id: str | None) -> None:
    release_slot(user_id, slot_id)


async def count_active_db(db, user_id: int) -> int:
    from sqlalchemy import func, select
    from app.models.task import Task

    q = await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == int(user_id),
            Task.status.in_(ACTIVE_STATUSES),
        )
    )
    return int(q.scalar() or 0)


async def count_queue_ahead(db) -> int:
    """Global queued jobs ahead of a new submit (honest ETA input, not SLA)."""
    from sqlalchemy import func, select
    from app.models.task import Task

    q = await db.execute(
        select(func.count()).select_from(Task).where(Task.status == "queued")
    )
    return int(q.scalar() or 0)


def used_slots(user_id: int, db_active: int) -> int:
    """Conservative used count: max(redis/local, db) so we never under-count."""
    return max(redis_slot_count(user_id), int(db_active or 0))


@dataclass
class ConcurrencySnapshot:
    used: int
    limit: int
    role: str
    remaining: int
    upgrade_plan: str | None
    upgrade_hint: str


async def snapshot(db, user_id: int, role: str | None) -> ConcurrencySnapshot:
    role_n = (role or "guest").lower()
    limit = concurrency_limit(role_n)
    db_active = await count_active_db(db, user_id)
    used = used_slots(user_id, db_active)
    plan, hint = upgrade_hint_for(role_n)
    return ConcurrencySnapshot(
        used=used,
        limit=limit,
        role=role_n,
        remaining=max(0, limit - used),
        upgrade_plan=plan,
        upgrade_hint=hint,
    )


async def acquire_slot(
    db,
    *,
    user_id: int,
    slot_id: str,
    role: str | None,
) -> ConcurrencySnapshot:
    """Reserve one concurrent slot. Raises ConcurrencyLimitError when full."""
    snap = await snapshot(db, user_id, role)
    if snap.used >= snap.limit:
        plan, hint = upgrade_hint_for(role)
        raise ConcurrencyLimitError(
            used=snap.used,
            limit=snap.limit,
            role=snap.role,
            retry_after=30,
            upgrade_plan=plan,
            upgrade_hint=hint,
        )
    _add_slot(user_id, slot_id)
    snap.used += 1
    snap.remaining = max(0, snap.limit - snap.used)
    return snap


def plan_shot_concurrency(role: str | None, env_conc: int) -> int:
    """Director in-job video parallelism: min(env, plan cap), at least 1.

    Starter 4 / Personal 6 / Creator 10 / Max 40 are user-level job caps;
    in-job shot fan-out must not exceed that plan's ceiling either.
    """
    try:
        env_n = max(1, min(8, int(env_conc)))
    except (TypeError, ValueError):
        env_n = 2
    return max(1, min(env_n, concurrency_limit(role)))


def concurrency_limit_for_user_id_sync(user_id: int | None) -> int:
    """Best-effort sync role lookup for Celery workers (director shot cap)."""
    if not user_id:
        return concurrency_limit("guest")
    try:
        from sqlalchemy import create_engine, text
        from app.tasks.task_db import get_db_url_sync

        engine = create_engine(get_db_url_sync())
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT role FROM users WHERE id = :id"),
                {"id": int(user_id)},
            ).first()
        role = (row[0] if row else "guest") or "guest"
        return concurrency_limit(role)
    except Exception as e:
        logger.warning("concurrency role lookup failed user=%s: %s", user_id, e)
        return concurrency_limit("guest")


# Test helper — never call from request paths.
def _reset_local_slots() -> None:
    with _local_lock:
        _local_slots.clear()
