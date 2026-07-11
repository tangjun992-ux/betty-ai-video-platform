"""
Billing API — credits lifecycle (对标 Yapper 的订阅/积分).

Checkout is Stripe-ready: when settings.STRIPE_API_KEY is configured it creates a
real Stripe Checkout Session; otherwise it runs in dev-grant mode, crediting the
account immediately and recording a PURCHASE transaction. The whole app shares
the guest account (user_id=0), matching how generation deducts credits.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.billing import UserBalance, Transaction, TransactionType
from app.api.pricing import PLANS

logger = logging.getLogger(__name__)
router = APIRouter()

GUEST_USER_ID = 0


# One-time credit packs (对标 credit bundles). price_usd 供展示 & 未来 Stripe。
CREDIT_PACKS = [
    {"id": "pack_mini", "name": "迷你包", "credits": 500, "price_usd": 4.99, "bonus": 0},
    {"id": "pack_basic", "name": "基础包", "credits": 2000, "price_usd": 17.99, "bonus": 200},
    {"id": "pack_pro", "name": "专业包", "credits": 5000, "price_usd": 39.99, "bonus": 800, "highlighted": True},
    {"id": "pack_studio", "name": "工作室包", "credits": 12000, "price_usd": 89.99, "bonus": 3000},
]


class CheckoutRequest(BaseModel):
    kind: str = Field(..., description="plan | pack")
    id: str = Field(..., description="套餐或积分包 id")
    cycle: str = Field("monthly", description="套餐计费周期 monthly|yearly")


async def _get_balance(db: AsyncSession, user_id: int) -> UserBalance:
    res = await db.execute(select(UserBalance).where(UserBalance.user_id == user_id))
    bal = res.scalar_one_or_none()
    if bal is None:
        bal = UserBalance(user_id=user_id, credits=0, daily_credits=10, daily_credits_max=10)
        db.add(bal)
        await db.flush()
    return bal


def _resolve_purchase(req: CheckoutRequest):
    """Return (credits, price_usd, label) for the requested plan/pack."""
    if req.kind == "plan":
        plan = next((p for p in PLANS if p.id == req.id), None)
        if not plan:
            raise HTTPException(status_code=404, detail=f"套餐不存在: {req.id}")
        price = plan.yearly_price if req.cycle == "yearly" else plan.monthly_price
        months = 12 if req.cycle == "yearly" else 1
        return plan.credits_per_month * months, round(price * months, 2), f"{plan.name}·{'年' if req.cycle=='yearly' else '月'}付"
    if req.kind == "pack":
        pack = next((p for p in CREDIT_PACKS if p["id"] == req.id), None)
        if not pack:
            raise HTTPException(status_code=404, detail=f"积分包不存在: {req.id}")
        return pack["credits"] + pack.get("bonus", 0), pack["price_usd"], pack["name"]
    raise HTTPException(status_code=400, detail="kind 必须是 plan 或 pack")


@router.get("/credit-packs", summary="一次性积分包")
async def credit_packs():
    return {"packs": CREDIT_PACKS}


@router.get("/summary", summary="账户余额与消费概览")
async def billing_summary(db: AsyncSession = Depends(get_db)):
    bal = await _get_balance(db, GUEST_USER_ID)
    await db.commit()
    return {
        "credits": bal.credits + bal.daily_credits,
        "purchased_credits": bal.credits,
        "daily_credits": bal.daily_credits,
        "daily_credits_max": bal.daily_credits_max,
        "total_spent": bal.total_spent,
        "total_tasks": bal.total_tasks,
        "total_purchased": bal.total_purchased,
        "stripe_enabled": bool(settings.STRIPE_API_KEY),
    }


@router.get("/transactions", summary="积分流水")
async def transactions(limit: int = 50, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Transaction).where(Transaction.user_id == GUEST_USER_ID)
        .order_by(desc(Transaction.created_at)).limit(min(limit, 200))
    )
    rows = res.scalars().all()
    return {"transactions": [{
        "id": t.id,
        "type": t.type,
        "amount": t.amount,
        "balance_after": t.balance_after,
        "description": t.description,
        "model_used": t.model_used,
        "amount_usd": t.amount_usd,
        "created_at": t.created_at.isoformat() if t.created_at else "",
    } for t in rows]}


@router.post("/checkout", summary="结算（Stripe-ready，无 key 时 dev 直发）")
async def checkout(req: CheckoutRequest, db: AsyncSession = Depends(get_db)):
    credits, price_usd, label = _resolve_purchase(req)

    # Stripe-ready branch (activated when a key is configured).
    if settings.STRIPE_API_KEY:
        try:
            import stripe  # optional dependency
            stripe.api_key = settings.STRIPE_API_KEY
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"betty · {label} ({credits} 积分)"},
                        "unit_amount": int(price_usd * 100),
                    },
                    "quantity": 1,
                }],
                success_url=settings.STRIPE_SUCCESS_URL,
                cancel_url=settings.STRIPE_CANCEL_URL,
                metadata={"kind": req.kind, "id": req.id, "credits": credits},
            )
            return {"mode": "stripe", "checkout_url": session.url, "credits": credits}
        except Exception as e:
            logger.error("stripe checkout failed: %s", e)
            raise HTTPException(status_code=502, detail=f"支付网关错误: {e}")

    # Dev-grant mode — credit immediately + record a real transaction.
    bal = await _get_balance(db, GUEST_USER_ID)
    before = bal.credits + bal.daily_credits
    bal.credits += credits
    bal.total_purchased += credits
    after = bal.credits + bal.daily_credits
    txn = Transaction(
        user_id=GUEST_USER_ID,
        type=TransactionType.PURCHASE.value,
        amount=credits,
        balance_before=before,
        balance_after=after,
        amount_usd=price_usd,
        payment_method="dev-grant",
        description=f"购买 {label}（+{credits} 积分）",
    )
    db.add(txn)
    await db.commit()
    logger.info("dev-grant checkout: +%d credits (%s), balance %d→%d", credits, label, before, after)
    return {"mode": "dev", "success": True, "credits_added": credits,
            "new_balance": after, "label": label}
