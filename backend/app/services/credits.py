"""
Credit accounting shared by the generation APIs.
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Transaction, TransactionType, UserBalance

logger = logging.getLogger(__name__)

TRIAL_CREDITS = 50
TRIAL_DAILY_CREDITS = 10


async def check_and_deduct_credits(
    db: AsyncSession,
    user_id: int,
    cost: int,
    task_id: str,
    model: str,
    description: str | None = None,
) -> bool:
    """Check and deduct credits from a user balance. Returns True if successful."""
    if cost <= 0:
        return True

    result = await db.execute(select(UserBalance).where(UserBalance.user_id == user_id))
    balance = result.scalar_one_or_none()

    # Allow first-time users (no balance record) — they start with free trial
    if balance is None:
        balance = UserBalance(
            user_id=user_id, credits=TRIAL_CREDITS, daily_credits=TRIAL_DAILY_CREDITS
        )
        db.add(balance)
        await db.flush()

    total_available = balance.credits + balance.daily_credits
    if total_available < cost:
        return False

    # Deduct from daily credits first, then purchased
    remaining = cost
    credits_before = total_available

    if balance.daily_credits > 0:
        deduct_daily = min(balance.daily_credits, remaining)
        balance.daily_credits -= deduct_daily
        remaining -= deduct_daily

    if remaining > 0:
        balance.credits -= remaining

    balance.total_spent += cost
    balance.total_tasks += 1
    credits_after = balance.credits + balance.daily_credits

    txn = Transaction(
        user_id=user_id,
        task_id=task_id,
        type=TransactionType.CONSUMPTION.value,
        amount=-cost,
        balance_before=credits_before,
        balance_after=credits_after,
        model_used=model,
        description=description or f"Generation task {task_id[:8]}...",
    )
    db.add(txn)
    await db.flush()

    logger.info(
        f"Credits deducted: user={user_id} cost={cost} model={model} "
        f"balance={credits_before}→{credits_after}"
    )
    return True
