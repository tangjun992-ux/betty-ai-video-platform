"""
Shared credit deduction — personal balance or team shared pool.

APIs pass an optional ``team_id`` (via ``X-Team-Id`` header) to spend from the
team pool when the actor is an active member.

Failed / cancelled tasks refund via ``refund_task_credits`` (async) or
``refund_task_credits_sync`` (Celery hooks) — both are idempotent per task_id.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Request
from sqlalchemy import create_engine, select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.billing import UserBalance, Transaction, TransactionType
from app.models.team import Team, TeamMember
from app.models.team_balance import TeamBalance

logger = logging.getLogger(__name__)

# Creator/Pro subscriptions auto-fund the owner's primary team pool.
TEAM_SUBSCRIPTION_PLANS = frozenset({"creator", "pro"})


def resolve_team_id(request: Request | None) -> Optional[str]:
    """Read X-Team-Id from the incoming request (empty → None)."""
    if request is None:
        return None
    return (request.headers.get("x-team-id") or "").strip() or None


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


async def available_personal_credits(balance: UserBalance) -> int:
    return (
        int(balance.credits or 0)
        + int(getattr(balance, "daily_credits", 0) or 0)
        + int(getattr(balance, "plan_credits", 0) or 0)
    )


def apply_plan_credit_rollover(balance: UserBalance, monthly: int) -> int:
    """Grant monthly plan credits with ≤2× allotment rollover cap (Yapper FAQ).

    Unused plan_credits carry into the next cycle, capped so
    plan_credits ≤ 2 * monthly after the grant. Purchased ``credits`` are untouched.
    """
    if monthly <= 0:
        return int(getattr(balance, "plan_credits", 0) or 0)
    current = int(getattr(balance, "plan_credits", 0) or 0)
    # Carry at most one month of unused allotment → total ≤ 2× after grant.
    carry = min(current, monthly)
    balance.plan_credits = carry + monthly
    balance.plan_monthly_allotment = monthly
    return balance.plan_credits


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
        total_available = balance.credits + getattr(balance, "daily_credits", 0)
        if total_available < cost:
            return False
        remaining = cost
        credits_before = total_available
        daily = getattr(balance, "daily_credits", 0) or 0
        if daily > 0:
            deduct_daily = min(daily, remaining)
            balance.daily_credits = daily - deduct_daily
            remaining -= deduct_daily
        if remaining > 0:
            balance.credits -= remaining
        credits_after = balance.credits + getattr(balance, "daily_credits", 0)
    else:
        balance = await _ensure_user_balance(db, user_id)
        total_available = await available_personal_credits(balance)
        if total_available < cost:
            return False
        remaining = cost
        credits_before = total_available

        daily = getattr(balance, "daily_credits", 0) or 0
        if daily > 0:
            deduct_daily = min(daily, remaining)
            balance.daily_credits = daily - deduct_daily
            remaining -= deduct_daily

        plan = int(getattr(balance, "plan_credits", 0) or 0)
        if remaining > 0 and plan > 0:
            take = min(plan, remaining)
            balance.plan_credits = plan - take
            remaining -= take

        if remaining > 0:
            balance.credits -= remaining

        credits_after = await available_personal_credits(balance)

    balance.total_spent = (balance.total_spent or 0) + cost
    balance.total_tasks = (balance.total_tasks or 0) + 1

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


async def grant_subscription_to_team_pool(
    db: AsyncSession,
    user_id: int,
    plan_id: str,
    credits: int,
    *,
    order_no: str = "",
) -> int:
    """Auto-recharge team shared pool when a Creator/Pro subscription is granted."""
    if credits <= 0 or plan_id not in TEAM_SUBSCRIPTION_PLANS:
        return 0

    res = await db.execute(
        select(Team).where(Team.owner_user_id == user_id).order_by(Team.created_at.asc())
    )
    team = res.scalars().first()
    if not team:
        logger.info("subscription team pool skip: user=%s has no owned team", user_id)
        return 0

    balance = await _ensure_team_balance(db, team.team_id)
    before = balance.credits
    balance.credits += credits
    balance.total_purchased = (balance.total_purchased or 0) + credits

    db.add(Transaction(
        user_id=user_id,
        type=TransactionType.BONUS.value,
        amount=credits,
        balance_before=before,
        balance_after=balance.credits,
        payment_id=order_no or None,
        description=f"订阅 {plan_id} 自动充值团队池（+{credits}）",
        team_id=team.team_id,
    ))
    await db.flush()
    logger.info(
        "subscription team pool funded: user=%s team=%s +%d credits",
        user_id, team.team_id[:8], credits,
    )
    return credits


def _db_url_sync() -> str:
    db_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    if db_url.startswith("sqlite+aiosqlite"):
        return db_url.replace("sqlite+aiosqlite", "sqlite")
    if db_url.startswith("postgresql+asyncpg"):
        return db_url.replace("postgresql+asyncpg", "postgresql")
    return db_url


def _mark_task_refunded_sync(session: Session, task_id: str, amount: int, reason: str) -> None:
    row = session.execute(
        text("SELECT parameters FROM tasks WHERE task_id = :tid"),
        {"tid": task_id},
    ).first()
    if not row:
        return
    raw = row[0]
    params: dict[str, Any] = {}
    if isinstance(raw, dict):
        params = dict(raw)
    elif isinstance(raw, str) and raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                params = parsed
        except Exception:
            params = {}
    params["credits_refunded"] = True
    params["refund_amount"] = amount
    params["refund_reason"] = reason
    params["refund_at"] = datetime.now(timezone.utc).isoformat()
    session.execute(
        text("UPDATE tasks SET parameters = :p WHERE task_id = :tid"),
        {"p": json.dumps(params, ensure_ascii=False), "tid": task_id},
    )


def refund_task_credits_sync(task_id: str, *, reason: str = "task_failed") -> dict[str, Any]:
    """Idempotent refund of the latest CONSUMPTION for ``task_id`` (Celery-safe).

    Restores credits to the original personal or team pool. Safe to call multiple
    times — subsequent calls return ``already_refunded``.
    """
    if not task_id:
        return {"refunded": False, "reason": "missing_task_id"}

    engine = create_engine(_db_url_sync())
    with Session(engine) as session:
        existing = session.execute(
            text(
                "SELECT id FROM transactions WHERE task_id = :tid AND type = :typ LIMIT 1"
            ),
            {"tid": task_id, "typ": TransactionType.REFUND.value},
        ).first()
        if existing:
            return {"refunded": False, "reason": "already_refunded", "task_id": task_id}

        cons = session.execute(
            text(
                "SELECT id, user_id, team_id, amount, model_used FROM transactions "
                "WHERE task_id = :tid AND type = :typ ORDER BY id DESC LIMIT 1"
            ),
            {"tid": task_id, "typ": TransactionType.CONSUMPTION.value},
        ).mappings().first()
        if not cons:
            return {"refunded": False, "reason": "no_consumption", "task_id": task_id}

        amount = abs(int(cons["amount"] or 0))
        if amount <= 0:
            return {"refunded": False, "reason": "zero_amount", "task_id": task_id}

        user_id = int(cons["user_id"])
        team_id = cons["team_id"] or None
        model_used = cons["model_used"]

        if team_id:
            bal = session.execute(
                text("SELECT credits, daily_credits, total_spent FROM team_balance WHERE team_id = :tid"),
                {"tid": team_id},
            ).mappings().first()
            if not bal:
                return {"refunded": False, "reason": "team_balance_missing", "task_id": task_id}
            before = int(bal["credits"] or 0) + int(bal["daily_credits"] or 0)
            session.execute(
                text(
                    "UPDATE team_balance SET credits = credits + :amt, "
                    "total_spent = CASE WHEN total_spent >= :amt THEN total_spent - :amt ELSE 0 END "
                    "WHERE team_id = :tid"
                ),
                {"amt": amount, "tid": team_id},
            )
            after = before + amount
        else:
            bal = session.execute(
                text(
                    "SELECT credits, daily_credits, plan_credits, total_spent "
                    "FROM user_balance WHERE user_id = :uid"
                ),
                {"uid": user_id},
            ).mappings().first()
            if not bal:
                return {"refunded": False, "reason": "user_balance_missing", "task_id": task_id}
            before = (
                int(bal["credits"] or 0)
                + int(bal["daily_credits"] or 0)
                + int(bal["plan_credits"] or 0)
            )
            session.execute(
                text(
                    "UPDATE user_balance SET credits = credits + :amt, "
                    "total_spent = CASE WHEN total_spent >= :amt THEN total_spent - :amt ELSE 0 END "
                    "WHERE user_id = :uid"
                ),
                {"amt": amount, "uid": user_id},
            )
            after = before + amount

        session.execute(
            text(
                "INSERT INTO transactions "
                "(user_id, task_id, team_id, type, amount, balance_before, balance_after, "
                "description, model_used, created_at, updated_at) "
                "VALUES (:uid, :tid, :team, :typ, :amt, :before, :after, :desc, :model, :now, :now)"
            ),
            {
                "uid": user_id,
                "tid": task_id,
                "team": team_id,
                "typ": TransactionType.REFUND.value,
                "amt": amount,
                "before": before,
                "after": after,
                "desc": f"任务失败退款 ({reason}) {task_id[:8]}",
                "model": model_used,
                "now": datetime.now(timezone.utc).replace(tzinfo=None),
            },
        )
        try:
            _mark_task_refunded_sync(session, task_id, amount, reason)
        except Exception as e:
            logger.warning("mark task refunded failed task=%s: %s", task_id, e)
        session.commit()
        logger.info(
            "Credits refunded: task=%s amount=%d reason=%s scope=%s",
            task_id[:8], amount, reason, f"team={team_id}" if team_id else f"user={user_id}",
        )
        return {
            "refunded": True,
            "task_id": task_id,
            "amount": amount,
            "reason": reason,
            "team_id": team_id,
            "user_id": user_id,
        }


async def refund_task_credits(
    db: AsyncSession,
    task_id: str,
    *,
    reason: str = "task_failed",
) -> dict[str, Any]:
    """Async idempotent refund using the request DB session."""
    if not task_id:
        return {"refunded": False, "reason": "missing_task_id"}

    existing = await db.execute(
        select(Transaction).where(
            Transaction.task_id == task_id,
            Transaction.type == TransactionType.REFUND.value,
        ).limit(1)
    )
    if existing.scalar_one_or_none():
        return {"refunded": False, "reason": "already_refunded", "task_id": task_id}

    cons_res = await db.execute(
        select(Transaction).where(
            Transaction.task_id == task_id,
            Transaction.type == TransactionType.CONSUMPTION.value,
        ).order_by(Transaction.id.desc()).limit(1)
    )
    cons = cons_res.scalar_one_or_none()
    if not cons:
        return {"refunded": False, "reason": "no_consumption", "task_id": task_id}

    amount = abs(int(cons.amount or 0))
    if amount <= 0:
        return {"refunded": False, "reason": "zero_amount", "task_id": task_id}

    user_id = int(cons.user_id)
    team_id = cons.team_id or None

    if team_id:
        balance = await _ensure_team_balance(db, team_id)
        before = int(balance.credits or 0) + int(getattr(balance, "daily_credits", 0) or 0)
        balance.credits = int(balance.credits or 0) + amount
        balance.total_spent = max(0, int(balance.total_spent or 0) - amount)
        after = int(balance.credits or 0) + int(getattr(balance, "daily_credits", 0) or 0)
    else:
        balance = await _ensure_user_balance(db, user_id)
        before = await available_personal_credits(balance)
        balance.credits = int(balance.credits or 0) + amount
        balance.total_spent = max(0, int(balance.total_spent or 0) - amount)
        after = await available_personal_credits(balance)

    db.add(Transaction(
        user_id=user_id,
        task_id=task_id,
        team_id=team_id,
        type=TransactionType.REFUND.value,
        amount=amount,
        balance_before=before,
        balance_after=after,
        model_used=cons.model_used,
        description=f"任务失败退款 ({reason}) {task_id[:8]}",
    ))

    # Best-effort: stamp task.parameters when Task row exists
    try:
        from app.models.task import Task
        tres = await db.execute(select(Task).where(Task.task_id == task_id))
        task = tres.scalar_one_or_none()
        if task is not None:
            params = dict(task.parameters) if isinstance(task.parameters, dict) else {}
            if isinstance(task.parameters, str) and task.parameters:
                try:
                    parsed = json.loads(task.parameters)
                    if isinstance(parsed, dict):
                        params = parsed
                except Exception:
                    pass
            params["credits_refunded"] = True
            params["refund_amount"] = amount
            params["refund_reason"] = reason
            params["refund_at"] = datetime.now(timezone.utc).isoformat()
            task.parameters = params
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(task, "parameters")
    except Exception as e:
        logger.warning("async mark task refunded failed task=%s: %s", task_id, e)

    await db.flush()
    logger.info("Credits refunded (async): task=%s amount=%d reason=%s", task_id[:8], amount, reason)
    return {
        "refunded": True,
        "task_id": task_id,
        "amount": amount,
        "reason": reason,
        "team_id": team_id,
        "user_id": user_id,
    }
