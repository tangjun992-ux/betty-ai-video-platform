"""Per-browser guest accounts — isolated anonymous users instead of shared user_id=0."""
from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.models.billing import UserBalance
from app.models.user import User

GUEST_CREDITS = 5
GUEST_DAILY = 3


async def get_or_create_guest_user(db: AsyncSession, guest_token: str) -> int:
    """Map a stable client token (X-Guest-Id) to a dedicated User row."""
    token = (guest_token or "").strip()
    if len(token) < 8:
        token = secrets.token_hex(16)
    username = f"guest_{token[:20]}"
    email = f"{username}@betty.local"

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user:
        return user.id

    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(secrets.token_hex(32)),
        display_name="访客",
        role="guest",
    )
    db.add(user)
    await db.flush()

    balance = UserBalance(
        user_id=user.id,
        credits=GUEST_CREDITS,
        daily_credits=GUEST_DAILY,
        daily_credits_max=GUEST_DAILY,
    )
    db.add(balance)
    await db.flush()
    return user.id
