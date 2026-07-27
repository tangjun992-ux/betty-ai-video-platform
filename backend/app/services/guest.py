"""Per-browser guest accounts — isolated anonymous users instead of shared user_id=0."""
from __future__ import annotations

import logging
import secrets

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.models.billing import UserBalance
from app.models.user import User

logger = logging.getLogger(__name__)

GUEST_CREDITS = 5
GUEST_DAILY = 3
LEGACY_POOL_USERNAME = "legacy_pool"


async def get_or_create_legacy_pool_user(db: AsyncSession) -> int:
    """Dedicated system user that owns pre-migration shared guest rows (user_id=0)."""
    result = await db.execute(select(User).where(User.username == LEGACY_POOL_USERNAME))
    user = result.scalar_one_or_none()
    if user:
        return user.id

    user = User(
        username=LEGACY_POOL_USERNAME,
        email=f"{LEGACY_POOL_USERNAME}@betty.local",
        hashed_password=get_password_hash(secrets.token_hex(32)),
        display_name="历史共享数据",
        role="system",
    )
    db.add(user)
    await db.flush()
    db.add(UserBalance(user_id=user.id, credits=0, daily_credits=0, daily_credits_max=0))
    await db.flush()
    return user.id


async def migrate_legacy_guest_pool(db: AsyncSession) -> int:
    """Reassign orphaned user_id=0 rows so new per-browser guests stay isolated."""
    from app.models.asset import Asset
    from app.models.director_session import DirectorSession
    from app.models.payment_order import PaymentOrder
    from app.models.project import Project
    from app.models.task import Task
    from app.models.timeline_project import TimelineProject

    pool_id = await get_or_create_legacy_pool_user(db)
    moved = 0
    tables = [
        (Task, Task.user_id),
        (Asset, Asset.user_id),
        (Project, Project.user_id),
        (TimelineProject, TimelineProject.user_id),
        (PaymentOrder, PaymentOrder.user_id),
        (DirectorSession, DirectorSession.user_id),
    ]
    for model, col in tables:
        r = await db.execute(
            update(model).where((col == 0) | (col.is_(None))).values(user_id=pool_id)
        )
        moved += r.rowcount or 0
    if moved:
        await db.commit()
        logger.info("migrated %s legacy guest rows to user_id=%s", moved, pool_id)
    return moved


async def _ensure_guest_balance(db: AsyncSession, user_id: int) -> None:
    """Create the guest's starter balance once, tolerating concurrent creators."""
    existing = await db.execute(
        select(UserBalance).where(UserBalance.user_id == user_id)
    )
    if existing.scalar_one_or_none():
        return
    db.add(UserBalance(
        user_id=user_id,
        credits=GUEST_CREDITS,
        daily_credits=GUEST_DAILY,
        daily_credits_max=GUEST_DAILY,
    ))
    try:
        await db.flush()
    except IntegrityError:
        # A parallel request for the same new guest already inserted the balance.
        await db.rollback()


async def get_or_create_guest_user(db: AsyncSession, guest_token: str) -> int:
    """Map a stable client token (X-Guest-Id) to a dedicated User row.

    Concurrency-safe: the first page load fires several parallel API calls with
    the same guest id; each runs in its own session and would otherwise race to
    INSERT the same user/balance (UNIQUE violation → 500). We commit on create
    and, on conflict, roll back and re-select the winner's row.
    """
    token = (guest_token or "").strip()
    if len(token) < 8:
        token = secrets.token_hex(16)
    username = f"guest_{token[:20]}"
    email = f"{username}@betty.local"

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user:
        await _ensure_guest_balance(db, user.id)
        return user.id

    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(secrets.token_hex(32)),
        display_name="访客",
        role="guest",
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        # Lost the race: another request created this guest. Re-select it.
        await db.rollback()
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one()
        await _ensure_guest_balance(db, user.id)
        return user.id

    await _ensure_guest_balance(db, user.id)
    return user.id
