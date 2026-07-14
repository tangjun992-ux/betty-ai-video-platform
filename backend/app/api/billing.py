"""
Billing API — credits lifecycle (对标 Yapper 的订阅/积分).

Checkout is Stripe-ready: when settings.STRIPE_API_KEY is configured it creates a
real Stripe Checkout Session; otherwise it runs in dev-grant mode, crediting the
account immediately and recording a PURCHASE transaction. The whole app shares
the guest account (user_id=0), matching how generation deducts credits.
"""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.billing import UserBalance, Transaction, TransactionType
from app.models.payment_order import PaymentOrder
from app.api.pricing import PLANS
from app.rate_limiter import rate_limit
from app.auth import resolve_user_id
from app.services.receipt_email import send_receipt_email

logger = logging.getLogger(__name__)
router = APIRouter()

GUEST_USER_ID = 0


def _emit_receipt(order: PaymentOrder, to_email: Optional[str] = None) -> None:
    """Fire-and-forget receipt email stub after a successful grant."""
    try:
        send_receipt_email(
            to_email=to_email,
            order_no=order.order_no,
            label=order.label or "",
            credits=int(order.credits or 0),
            amount_usd=float(order.amount_usd or 0),
            provider=order.provider or "",
        )
    except Exception as e:
        logger.warning("send_receipt_email failed: %s", e)


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


class PayCreateRequest(CheckoutRequest):
    method: str = Field("wechat", description="wechat | alipay")


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
async def billing_summary(db: AsyncSession = Depends(get_db), user_id: int = Depends(resolve_user_id)):
    bal = await _get_balance(db, user_id)
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
async def transactions(limit: int = 50, db: AsyncSession = Depends(get_db),
                       user_id: int = Depends(resolve_user_id)):
    res = await db.execute(
        select(Transaction).where(Transaction.user_id == user_id)
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
        "payment_id": t.payment_id,
        "created_at": t.created_at.isoformat() if t.created_at else "",
    } for t in rows]}


@router.get("/usage", summary="用量报表（按用户聚合）")
async def usage(days: int = 30, db: AsyncSession = Depends(get_db),
                user_id: int = Depends(resolve_user_id)):
    """Per-user usage report: spend total, by-model, by-type, daily series —
    computed from the user's consumption transactions + completed tasks."""
    from datetime import timedelta
    from app.models.task import Task
    since = (datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 365)))).replace(tzinfo=None)

    def _naive(dt):
        return dt.replace(tzinfo=None) if (dt and dt.tzinfo) else dt

    # Consumption transactions (credits spent)
    res = await db.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.CONSUMPTION.value,
        ).order_by(desc(Transaction.created_at)).limit(2000)
    )
    txns = [t for t in res.scalars().all() if (t.created_at and _naive(t.created_at) >= since)]
    total_spent = sum(-t.amount for t in txns)

    by_model: dict = {}
    daily: dict = {}
    for t in txns:
        m = t.model_used or "unknown"
        by_model[m] = by_model.get(m, 0) + (-t.amount)
        day = t.created_at.strftime("%Y-%m-%d") if t.created_at else "?"
        daily[day] = daily.get(day, 0) + (-t.amount)

    # By media type from tasks
    tres = await db.execute(
        select(Task).where(Task.user_id == user_id, Task.status == "completed").limit(2000)
    )
    by_type: dict = {}
    task_count = 0
    for t in tres.scalars().all():
        if t.created_at and _naive(t.created_at) < since:
            continue
        task_count += 1
        by_type[t.media_type or "image"] = by_type.get(t.media_type or "image", 0) + 1

    return {
        "period_days": days,
        "total_spent": total_spent,
        "task_count": task_count,
        "by_model": sorted([{"model": k, "credits": v} for k, v in by_model.items()], key=lambda x: -x["credits"]),
        "by_type": [{"type": k, "count": v} for k, v in by_type.items()],
        "daily": [{"day": k, "credits": v} for k, v in sorted(daily.items())],
    }


@router.post("/refund/{order_no}", summary="申请退款（返还积分并记流水）")
async def refund(order_no: str, db: AsyncSession = Depends(get_db),
                 user_id: int = Depends(resolve_user_id)):
    """Refund a purchase order: reverse the granted credits (down to 0) and
    record a REFUND transaction. Idempotent (rejects if already refunded)."""
    res = await db.execute(select(PaymentOrder).where(
        PaymentOrder.order_no == order_no, PaymentOrder.user_id == user_id))
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != "paid" or not order.granted:
        raise HTTPException(status_code=400, detail="该订单不可退款（未支付或未发放）")
    prior = await db.execute(select(Transaction).where(
        Transaction.payment_id == order_no, Transaction.type == TransactionType.REFUND.value))
    if prior.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该订单已退款")

    bal = await _get_balance(db, user_id)
    before = bal.credits + bal.daily_credits
    reversible = min(order.credits, bal.credits)  # can't claw back already-spent credits
    bal.credits -= reversible
    after = bal.credits + bal.daily_credits
    db.add(Transaction(
        user_id=user_id, type=TransactionType.REFUND.value, amount=-reversible,
        balance_before=before, balance_after=after, amount_usd=order.amount_usd,
        payment_method=order.provider, payment_id=order_no,
        description=f"退款：{order.label}（-{reversible} 积分，退回 ${order.amount_usd}）",
    ))
    await db.commit()
    return {"order_no": order_no, "refunded_credits": reversible, "refunded_usd": order.amount_usd,
            "new_balance": after, "message": "退款成功，款项将原路退回"}


@router.get("/receipt/{order_no}", summary="购买收据")
async def receipt(order_no: str, db: AsyncSession = Depends(get_db),
                  user_id: int = Depends(resolve_user_id)):
    res = await db.execute(select(PaymentOrder).where(
        PaymentOrder.order_no == order_no, PaymentOrder.user_id == user_id))
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {
        "order_no": order.order_no,
        "label": order.label,
        "kind": order.kind,
        "credits": order.credits,
        "amount_usd": order.amount_usd,
        "amount_cny": order.amount_cny,
        "provider": order.provider,
        "status": order.status,
        "created_at": order.created_at.isoformat() if order.created_at else "",
        "merchant": "betty AI",
    }


@router.post("/checkout", summary="结算（Stripe-ready，无 key 时 dev 直发）",
             dependencies=[Depends(rate_limit("checkout", rpm=10, rph=60))])
async def checkout(req: CheckoutRequest, db: AsyncSession = Depends(get_db),
                   user_id: int = Depends(resolve_user_id)):
    credits, price_usd, label = _resolve_purchase(req)

    # Stripe-ready branch (activated when a key is configured).
    if settings.STRIPE_API_KEY:
        try:
            import stripe  # optional dependency
            stripe.api_key = settings.STRIPE_API_KEY
            order_no = "ST" + uuid.uuid4().hex[:22]
            order = PaymentOrder(
                order_no=order_no, user_id=user_id, provider="stripe",
                kind=req.kind, item_id=req.id, cycle=req.cycle, credits=credits,
                amount_usd=price_usd, amount_cny=round(price_usd * settings.USD_TO_CNY, 2),
                label=label, status="pending",
            )
            db.add(order)
            await db.commit()
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
                metadata={
                    "kind": req.kind, "id": req.id, "credits": str(credits),
                    "order_no": order_no, "user_id": str(user_id),
                },
            )
            return {"mode": "stripe", "checkout_url": session.url, "credits": credits, "order_no": order_no}
        except Exception as e:
            logger.error("stripe checkout failed: %s", e)
            raise HTTPException(status_code=502, detail=f"支付网关错误: {e}")

    # Dev-grant mode — only allowed outside production (local/staging demos).
    if settings.is_production:
        raise HTTPException(
            status_code=503,
            detail="生产环境未配置 Stripe 支付网关，请联系管理员或配置 STRIPE_API_KEY",
        )

    # Dev-grant mode — credit immediately + record a real transaction.
    bal = await _get_balance(db, user_id)
    before = bal.credits + bal.daily_credits
    bal.credits += credits
    bal.total_purchased += credits
    after = bal.credits + bal.daily_credits
    order_no = "DEV" + uuid.uuid4().hex[:20]
    txn = Transaction(
        user_id=user_id,
        type=TransactionType.PURCHASE.value,
        amount=credits,
        balance_before=before,
        balance_after=after,
        amount_usd=price_usd,
        payment_method="dev-grant",
        payment_id=order_no,
        description=f"购买 {label}（+{credits} 积分）",
    )
    db.add(txn)
    await db.commit()
    logger.info("dev-grant checkout: +%d credits (%s), balance %d→%d", credits, label, before, after)
    try:
        send_receipt_email(
            order_no=order_no, label=label, credits=credits,
            amount_usd=price_usd, provider="dev-grant",
        )
    except Exception as e:
        logger.warning("dev-grant receipt email stub failed: %s", e)
    return {"mode": "dev", "success": True, "credits_added": credits,
            "new_balance": after, "label": label, "order_no": order_no}


# ─── QR-based payment (WeChat / Alipay) ──────────────────
async def _grant_order(db: AsyncSession, order: PaymentOrder, *, email: Optional[str] = None) -> int:
    """Idempotently credit a PAID order and record a PURCHASE transaction."""
    if order.granted or order.status != "paid":
        bal = await _get_balance(db, order.user_id or GUEST_USER_ID)
        return bal.credits + bal.daily_credits
    bal = await _get_balance(db, order.user_id or GUEST_USER_ID)
    before = bal.credits + bal.daily_credits
    bal.credits += order.credits
    bal.total_purchased += order.credits
    after = bal.credits + bal.daily_credits
    db.add(Transaction(
        user_id=order.user_id or GUEST_USER_ID,
        type=TransactionType.PURCHASE.value, amount=order.credits,
        balance_before=before, balance_after=after, amount_usd=order.amount_usd,
        payment_method=order.provider, payment_id=order.order_no,
        description=f"{order.label}（+{order.credits} 积分 · {order.provider}）",
    ))
    order.granted = True
    await db.commit()
    logger.info("order %s granted +%d credits (%s)", order.order_no, order.credits, order.provider)
    _emit_receipt(order, to_email=email)
    return after


@router.get("/pay/methods", summary="可用支付方式")
async def pay_methods():
    from app.services import payments
    return {"methods": payments.method_status(), "usd_to_cny": settings.USD_TO_CNY}


@router.post("/pay/create", summary="创建二维码支付订单（微信/支付宝）",
             dependencies=[Depends(rate_limit("pay_create", rpm=10, rph=60))])
async def pay_create(req: PayCreateRequest, db: AsyncSession = Depends(get_db),
                     user_id: int = Depends(resolve_user_id)):
    from app.services import payments
    if req.method not in ("wechat", "alipay"):
        raise HTTPException(status_code=400, detail="method 必须是 wechat 或 alipay")
    credits, price_usd, label = _resolve_purchase(req)
    amount_cny = round(price_usd * settings.USD_TO_CNY, 2)
    order_no = "BT" + uuid.uuid4().hex[:22]
    notify_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/api/v1/billing/pay/notify/{req.method}"

    if req.method == "wechat":
        qr_content, live = payments.create_wechat_native(order_no, amount_cny, f"betty · {label}", notify_url)
    else:
        qr_content, live = payments.create_alipay_precreate(order_no, amount_cny, f"betty · {label}", notify_url)

    provider = req.method if live else "sandbox"
    order = PaymentOrder(
        order_no=order_no, user_id=user_id, provider=provider,
        kind=req.kind, item_id=req.id, cycle=req.cycle, credits=credits,
        amount_usd=price_usd, amount_cny=amount_cny, label=label,
        status="pending", qr_content=qr_content,
    )
    db.add(order)
    await db.commit()
    return {
        "order_no": order_no, "method": req.method, "live": live,
        "qr_content": qr_content, "qr_image": payments.qr_data_url(qr_content),
        "amount_cny": amount_cny, "amount_usd": price_usd, "credits": credits, "label": label,
    }


@router.get("/pay/status/{order_no}", summary="查询支付订单状态")
async def pay_status(order_no: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(PaymentOrder).where(PaymentOrder.order_no == order_no))
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    # For live providers, poll the gateway; sandbox is driven by mock-confirm/notify.
    if order.status == "pending" and order.provider in ("wechat", "alipay"):
        from app.services import payments
        state = payments.query_wechat(order_no) if order.provider == "wechat" else payments.query_alipay(order_no)
        if state == "paid":
            order.status = "paid"
            await db.commit()
    balance = None
    if order.status == "paid":
        balance = await _grant_order(db, order)
    return {"order_no": order_no, "status": order.status, "granted": order.granted,
            "credits": order.credits, "balance": balance}


@router.api_route("/pay/mock-confirm/{order_no}", methods=["GET", "POST"], summary="沙箱：模拟支付成功")
async def pay_mock_confirm(order_no: str, db: AsyncSession = Depends(get_db)):
    """Sandbox-only: simulate the user completing the scan-to-pay. Rejected for
    live provider orders (real payment must come through the gateway notify)."""
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not found")
    res = await db.execute(select(PaymentOrder).where(PaymentOrder.order_no == order_no))
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.provider != "sandbox":
        raise HTTPException(status_code=400, detail="真实支付订单不可模拟，请通过支付网关完成")
    if order.status != "paid":
        order.status = "paid"
        await db.commit()
    balance = await _grant_order(db, order)
    return {"order_no": order_no, "status": "paid", "credits": order.credits, "balance": balance}


@router.post("/pay/notify/{provider}", summary="支付异步回调（微信/支付宝）")
async def pay_notify(provider: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Async payment notification from WeChat/Alipay. In production, live orders
    require signature verification before crediting."""
    from app.services import payments
    order_no = None
    paid = False
    try:
        if provider == "alipay":
            form = dict((await request.form()))
            order_no = form.get("out_trade_no")
            trade_status = form.get("trade_status")
            paid = trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED")
            if settings.is_production and order_no:
                r = await db.execute(select(PaymentOrder).where(PaymentOrder.order_no == order_no))
                order_probe = r.scalar_one_or_none()
                if order_probe and order_probe.provider == "alipay":
                    if not payments.verify_alipay_notify(form):
                        return {"code": "FAIL", "message": "signature verification failed"}
        else:  # wechat v3
            body = await request.json()
            order_no = body.get("out_trade_no")
            paid = body.get("event_type", "").endswith("SUCCESS")
            if settings.is_production and order_no:
                r = await db.execute(select(PaymentOrder).where(PaymentOrder.order_no == order_no))
                order_probe = r.scalar_one_or_none()
                if order_probe and order_probe.provider == "wechat":
                    if not payments.verify_wechat_notify(body, dict(request.headers)):
                        return {"code": "FAIL", "message": "signature verification failed"}
        if not order_no:
            return {"code": "FAIL", "message": "missing out_trade_no"}
        r = await db.execute(select(PaymentOrder).where(PaymentOrder.order_no == order_no))
        order = r.scalar_one_or_none()
        if order and paid:
            order.status = "paid"
            await db.commit()
            await _grant_order(db, order)
        return {"code": "SUCCESS", "message": "OK"}
    except Exception as e:
        logger.error("pay notify(%s) error: %s", provider, e)
        return {"code": "FAIL", "message": str(e)}


@router.post("/stripe/webhook", summary="Stripe Webhook（checkout.session.completed）")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Mark the pending Stripe order paid and grant credits + send receipt stub."""
    import json
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    secret = settings.STRIPE_WEBHOOK_SECRET or os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if settings.is_production and not secret:
        raise HTTPException(status_code=503, detail="Stripe webhook secret not configured")
    if settings.is_production and not sig:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    try:
        if secret and settings.STRIPE_API_KEY:
            import stripe
            stripe.api_key = settings.STRIPE_API_KEY
            event = stripe.Webhook.construct_event(payload, sig, secret)
            etype = event["type"]
            data_obj = event["data"]["object"]
        elif settings.is_production:
            raise HTTPException(status_code=503, detail="Stripe not configured")
        else:
            event = json.loads(payload.decode("utf-8"))
            etype = event.get("type")
            data_obj = (event.get("data") or {}).get("object") or {}
    except Exception as e:
        logger.error("stripe webhook parse failed: %s", e)
        raise HTTPException(status_code=400, detail=f"invalid webhook: {e}")

    if etype != "checkout.session.completed":
        return {"received": True, "ignored": etype}

    meta = data_obj.get("metadata") or {}
    order_no = meta.get("order_no")
    customer_details = data_obj.get("customer_details") or {}
    customer_email = customer_details.get("email") or data_obj.get("customer_email")
    if not order_no:
        logger.warning("stripe webhook missing order_no metadata")
        return {"received": True, "error": "missing order_no"}

    res = await db.execute(select(PaymentOrder).where(PaymentOrder.order_no == order_no))
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != "paid":
        order.status = "paid"
        await db.commit()
    balance = await _grant_order(db, order, email=customer_email)
    return {"received": True, "order_no": order_no, "status": "paid", "balance": balance}
