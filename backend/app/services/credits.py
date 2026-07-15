"""
Shared credit deduction — personal balance or team shared pool.

Generation APIs pass an optional ``team_id`` (via ``X-Team-Id`` header) to spend
from the team pool when the actor is an active member.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import UserBalance, Transaction, TransactionType
from app.models.team import TeamMember
from app.models.team_balance import TeamBalance

logger = logging.getLogger(__name__)


async def _ensure_user_balance(db: AsyncSession, user_id: int) -> UserBalance:
    result = await db.execute(select(UserBalance).where(UserBalance.user_id == user_id))
    balance = result.scalar_one_or_none()
    if balance is None:
        balance = UserBalance(user_id=user_id, credits=50, daily_credits=10)
        db.add(balance)
        await db.flush()
    return balance


async def _ensure_team_balance(db: AsyncSession, team_id: str) -> TeamBalance:
    result = await db.execute(select(TeamBalance).where(TeamBalance.team_id == team_id))
    balance = result.scalar_one_or_none()
    if balance is None:
        balance = TeamBalance(team_id=team_id, credits=0, daily_credits=0, daily_credits_max=0)
        db.add(balance)
        await db.flush()
    return balance


async def is_active_team_member(db: AsyncSession, team_id: str, user_id: int) -> bool:
    res = await db.execute(
        select(TeamMember).where(
            and_(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
                TeamMember.status == "active",
            )
        )
    )
    return res.scalar_one_or_none() is not None


async def deduct_credits(
    db: AsyncSession,
    user_id: int,
    cost: int,
    task_id: str,
    model: str,
    *,
    team_id: Optional[str] = None,
    description: Optional[str] = None,
) -> bool:
    """Deduct credits from team pool (if team_id + membership) else personal balance."""
    if cost <= 0:
        return True

    if team_id:
        if not await is_active_team_member(db, team_id, user_id):
            return False
        balance = await _ensure_team_balance(db, team_id)
    else:
        balance = await _ensure_user_balance(db, user_id)

    total_available = balance.credits + getattr(balance, "daily_credits", 0)
    if total_available < cost:
        return False

    remaining = cost
    credits_before = balance.credits + getattr(balance, "daily_credits", 0)

    daily = getattr(balance, "daily_credits", 0) or 0
    if daily > 0:
        deduct_daily = min(daily, remaining)
        balance.daily_credits = daily - deduct_daily
        remaining -= deduct_daily

    if remaining > 0:
        balance.credits -= remaining

    balance.total_spent = (balance.total_spent or 0) + cost
    balance.total_tasks = (balance.total_tasks or 0) + 1
    credits_after = balance.credits + getattr(balance, "daily_credits", 0)

    desc = description or f"Generation task {task_id[:8]}..."
    txn = Transaction(
        user_id=user_id,
        task_id=task_id,
        type=TransactionType.CONSUMPTION.value,
        amount=-cost,
        balance_before=credits_before,
        balance_after=credits_after,
        model_used=model,
        description=desc,
        team_id=team_id,
    )
    db.add(txn)
    await db.flush()

    scope = f"team={team_id}" if team_id else f"user={user_id}"
    logger.info("Credits deducted: %s cost=%d balance=%d→%d", scope, cost, credits_before, credits_after)
    return True


async def transfer_to_team(
    db: AsyncSession, user_id: int, team_id: str, amount: int,
) -> int:
    """Move purchased credits from personal balance into the team shared pool."""
    if amount <= 0:
        raise ValueError("amount must be positive")
    if not await is_active_team_member(db, team_id, user_id):
        raise PermissionError("not a team member")

    personal = await _ensure_user_balance(db, user_id)
    if personal.credits < amount:
        raise ValueError("insufficient personal credits")

    team_bal = await _ensure_team_balance(db, team_id)
    before_personal = personal.credits + personal.daily_credits
    personal.credits -= amount
    after_personal = personal.credits + personal.daily_credits

    before_team = team_bal.credits
    team_bal.credits += amount
    team_bal.total_purchased = (team_bal.total_purchased or 0) + amount

    db.add(Transaction(
        user_id=user_id,
        type=TransactionType.CONSUMPTION.value,
        amount=-amount,
        balance_before=before_personal,
        balance_after=after_personal,
        description=f"转入团队池 {team_id[:8]}…",
        team_id=team_id,
    ))
    db.add(Transaction(
        user_id=user_id,
        type=TransactionType.BONUS.value,
        amount=amount,
        balance_before=before_team,
        balance_after=team_bal.credits,
        description=f"团队共享池充值 +{amount}",
        team_id=team_id,
    ))
    await db.flush()
    return team_bal.credits
