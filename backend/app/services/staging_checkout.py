"""Staging checkout smoke — checkout → webhook → credits verification."""
from __future__ import annotations

import json
import uuid

import httpx
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings


async def run_staging_checkout_smoke(db: AsyncSession, user_id: int) -> dict:
    """Verify revenue path: dev-grant or Stripe pending order + signed webhook."""
    from app.api.billing import CREDIT_PACKS, _get_balance, available_personal_credits
    from app.models.payment_order import PaymentOrder

    pack = next((p for p in CREDIT_PACKS if p["id"] == "pack_mini"), None)
    if not pack:
        return {"ok": False, "error": "pack_mini not configured"}

    bal = await _get_balance(db, user_id)
    credits_before = await available_personal_credits(bal)

    if settings.STRIPE_API_KEY:
        return await _stripe_checkout_webhook_smoke(db, user_id, pack, credits_before)

    return await _dev_grant_smoke(db, user_id, pack, credits_before)


async def _dev_grant_smoke(db: AsyncSession, user_id: int, pack: dict, credits_before: int) -> dict:
    from app.api.billing import CheckoutRequest, TransactionType, _get_balance, _resolve_purchase, available_personal_credits
    from app.models.billing import Transaction

    if settings.is_production:
        return {"ok": False, "mode": "dev_grant", "error": "dev-grant blocked in production"}

    req = CheckoutRequest(kind="pack", id="pack_mini", cycle="monthly", quantity=1)
    credits, price_usd, label, _extra = _resolve_purchase(req)
    order_no = "DEV" + uuid.uuid4().hex[:20]
    bal = await _get_balance(db, user_id)
    before = await available_personal_credits(bal)
    bal.credits += credits
    bal.total_purchased += credits
    after = await available_personal_credits(bal)
    txn = Transaction(
        user_id=user_id,
        type=TransactionType.PURCHASE.value,
        amount=credits,
        balance_before=before,
        balance_after=after,
        amount_usd=price_usd,
        payment_method="dev-grant",
        payment_id=order_no,
        description=f"staging smoke {label}",
    )
    db.add(txn)
    await db.commit()

    bal2 = await _get_balance(db, user_id)
    credits_after = await available_personal_credits(bal2)
    ok = credits_after > credits_before
    return {
        "ok": ok,
        "mode": "dev_grant",
        "order_no": order_no,
        "credits_before": credits_before,
        "credits_after": credits_after,
        "credits_delta": credits_after - credits_before,
        "pack_id": "pack_mini",
    }


async def _stripe_checkout_webhook_smoke(
    db: AsyncSession,
    user_id: int,
    pack: dict,
    credits_before: int,
) -> dict:
    from app.models.payment_order import PaymentOrder
    from app.services.stripe_ready import stripe_webhook_sign_payload

    secret = (settings.STRIPE_WEBHOOK_SECRET or "").strip()
    if not secret:
        return {"ok": False, "mode": "stripe_webhook", "error": "STRIPE_WEBHOOK_SECRET missing"}

    order_no = "ST" + uuid.uuid4().hex[:22]
    order = PaymentOrder(
        order_no=order_no,
        user_id=user_id,
        provider="stripe",
        kind="pack",
        item_id="pack_mini",
        cycle="monthly",
        credits=int(pack["credits"]),
        amount_usd=float(pack["price_usd"]),
        amount_cny=round(float(pack["price_usd"]) * settings.USD_TO_CNY, 2),
        label=pack["name"],
        status="pending",
    )
    db.add(order)
    await db.commit()

    body = json.dumps({
        "id": "evt_staging_checkout_smoke",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"order_no": order_no},
                "customer_details": {"email": "staging-smoke@test.example"},
            },
        },
    })
    sig = stripe_webhook_sign_payload(body, secret)

    from app.main import app

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        wh = await client.post(
            "/api/v1/billing/stripe/webhook",
            content=body.encode("utf-8"),
            headers={"Content-Type": "application/json", "Stripe-Signature": sig},
        )

    if wh.status_code != 200:
        return {
            "ok": False,
            "mode": "stripe_webhook",
            "order_no": order_no,
            "error": f"webhook HTTP {wh.status_code}",
            "webhook_response": wh.text[:200],
        }

    wh_body = wh.json()
    from app.api.billing import _get_balance, available_personal_credits

    credits_after = int(wh_body.get("balance") or 0)
    if credits_after <= credits_before:
        await db.commit()
        db.expire_all()
        bal = await _get_balance(db, user_id)
        credits_after = await available_personal_credits(bal)
    ok = credits_after > credits_before and wh_body.get("status") == "paid"
    return {
        "ok": ok,
        "mode": "stripe_webhook",
        "order_no": order_no,
        "credits_before": credits_before,
        "credits_after": credits_after,
        "credits_delta": credits_after - credits_before,
        "webhook_response": wh_body,
        "pack_id": "pack_mini",
    }
