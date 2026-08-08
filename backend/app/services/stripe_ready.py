"""
Stripe production readiness helpers.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass

from app.config import settings


PLAN_PRICE_ENVS = (
    "STRIPE_PRICE_STARTER_MONTHLY",
    "STRIPE_PRICE_STARTER_YEARLY",
    "STRIPE_PRICE_PERSONAL_MONTHLY",
    "STRIPE_PRICE_PERSONAL_YEARLY",
    "STRIPE_PRICE_CREATOR_MONTHLY",
    "STRIPE_PRICE_CREATOR_YEARLY",
    "STRIPE_PRICE_PRO_MONTHLY",
    "STRIPE_PRICE_PRO_YEARLY",
    "STRIPE_PRICE_MAX_MONTHLY",
    "STRIPE_PRICE_MAX_YEARLY",
)

# All env keys emitted by scripts/bootstrap_stripe_prices.py (incl. team seat).
BOOTSTRAP_PRICE_ENVS = PLAN_PRICE_ENVS + ("STRIPE_PRICE_TEAM_SEAT_MONTHLY",)

# Minimum monthly prices that unlock real subscription Checkout mode.
_SUBSCRIPTION_MONTHLY_ENVS = (
    "STRIPE_PRICE_STARTER_MONTHLY",
    "STRIPE_PRICE_PERSONAL_MONTHLY",
    "STRIPE_PRICE_CREATOR_MONTHLY",
    "STRIPE_PRICE_MAX_MONTHLY",
    "STRIPE_PRICE_PRO_MONTHLY",  # legacy alias of Max
)

REQUIRED_STRIPE_WEBHOOK_EVENTS = (
    "checkout.session.completed",
    "invoice.paid",
)

STRIPE_WEBHOOK_PATH = "/api/v1/billing/stripe/webhook"

# Stripe-Signature tolerance (seconds) — matches stripe-python default.
STRIPE_WEBHOOK_TOLERANCE_SEC = 300


def stripe_webhook_sign_payload(payload: bytes | str, secret: str, *, timestamp: int | None = None) -> str:
    """Build a Stripe-Signature header for test/staging self-checks."""
    ts = int(timestamp if timestamp is not None else time.time())
    body = payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else payload
    signed = f"{ts}.{body}"
    digest = hmac.new(secret.encode("utf-8"), signed.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def stripe_webhook_verify_payload(
    payload: bytes,
    signature_header: str,
    secret: str,
    *,
    tolerance: int = STRIPE_WEBHOOK_TOLERANCE_SEC,
) -> dict:
    """Verify Stripe-Signature and return parsed event dict (pure Python, no stripe SDK)."""
    if not secret:
        raise ValueError("webhook secret missing")
    if not signature_header:
        raise ValueError("Missing Stripe-Signature header")
    parts = [p.strip() for p in signature_header.split(",")]
    timestamp: int | None = None
    signatures: list[str] = []
    for part in parts:
        if part.startswith("t="):
            timestamp = int(part[2:])
        elif part.startswith("v1="):
            signatures.append(part[3:])
    if timestamp is None or not signatures:
        raise ValueError("invalid Stripe-Signature header")
    if tolerance > 0 and abs(time.time() - timestamp) > tolerance:
        raise ValueError("timestamp outside tolerance")
    body = payload.decode("utf-8")
    expected = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.{body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise ValueError("signature mismatch")
    event = json.loads(body)
    if not isinstance(event, dict):
        raise ValueError("webhook payload must be JSON object")
    return event


def parse_stripe_webhook_event(payload: bytes, signature_header: str, secret: str) -> dict:
    """Verify Stripe-Signature and return parsed event (pure Python, no stripe SDK required)."""
    return stripe_webhook_verify_payload(payload, signature_header, secret)


def stripe_webhook_signature_self_test() -> dict:
    """Round-trip sign/verify using configured whsec (no Stripe API calls)."""
    secret = (settings.STRIPE_WEBHOOK_SECRET or os.getenv("STRIPE_WEBHOOK_SECRET", "") or "").strip()
    if not secret:
        return {
            "configured": False,
            "self_test_ok": False,
            "error": "STRIPE_WEBHOOK_SECRET missing",
        }
    if not secret.startswith("whsec_"):
        return {
            "configured": True,
            "self_test_ok": False,
            "error": "STRIPE_WEBHOOK_SECRET should start with whsec_",
        }
    sample = json.dumps({
        "id": "evt_self_test",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"order_no": "SELF_TEST"}}},
    })
    try:
        sig = stripe_webhook_sign_payload(sample, secret)
        parsed = stripe_webhook_verify_payload(sample.encode("utf-8"), sig, secret)
        ok = parsed.get("type") == "checkout.session.completed"
        return {
            "configured": True,
            "self_test_ok": ok,
            "sample_event_type": parsed.get("type"),
            "error": None if ok else "unexpected parsed event type",
        }
    except Exception as ex:
        return {
            "configured": True,
            "self_test_ok": False,
            "error": str(ex)[:200],
        }


def stripe_webhook_ping_payload(*, event_type: str = "account.updated") -> tuple[str, str] | tuple[None, None]:
    """Build signed ping payload + Stripe-Signature header (ignored event type)."""
    secret = (settings.STRIPE_WEBHOOK_SECRET or os.getenv("STRIPE_WEBHOOK_SECRET", "") or "").strip()
    if not secret:
        return None, None
    payload = json.dumps({
        "id": "evt_deliver_ping",
        "object": "event",
        "type": event_type,
        "data": {"object": {}},
    })
    return payload, stripe_webhook_sign_payload(payload, secret)


async def stripe_webhook_delivery_test(*, app=None) -> dict:
    """Deliver signed ping event through the webhook route (ASGI in-process)."""
    import httpx
    from httpx import ASGITransport

    payload, sig = stripe_webhook_ping_payload()
    if not payload or not sig:
        return {"delivery_ok": False, "error": "STRIPE_WEBHOOK_SECRET missing"}
    if app is None:
        from app.main import app as default_app
        app = default_app
    path = "/api/v1/billing/stripe/webhook"
    try:
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                path,
                content=payload.encode("utf-8"),
                headers={"Content-Type": "application/json", "Stripe-Signature": sig},
            )
        body: dict | str
        try:
            body = r.json()
        except Exception:
            body = r.text[:300]
        ok = r.status_code == 200 and isinstance(body, dict) and body.get("received") is True
        return {
            "delivery_ok": ok,
            "status_code": r.status_code,
            "endpoint": path,
            "event_type": "account.updated",
            "response": body,
            "error": None if ok else f"HTTP {r.status_code}",
        }
    except Exception as ex:
        return {
            "delivery_ok": False,
            "endpoint": path,
            "error": str(ex)[:200],
        }


@dataclass
class StripeStatus:
    api_key_configured: bool
    webhook_secret_configured: bool
    plan_price_ids: dict[str, bool]
    seat_price_configured: bool
    subscription_ready: bool
    production_ok: bool
    blockers: list[str]

    def public_dict(self) -> dict:
        return {
            "api_key_configured": self.api_key_configured,
            "webhook_secret_configured": self.webhook_secret_configured,
            "plan_price_ids": self.plan_price_ids,
            "seat_price_configured": self.seat_price_configured,
            "subscription_ready": self.subscription_ready,
            "production_ok": self.production_ok,
            "blockers": self.blockers,
        }


def _env_price(name: str) -> str:
    return (getattr(settings, name, None) or os.getenv(name, "") or "").strip()


def stripe_status() -> StripeStatus:
    api = bool(settings.STRIPE_API_KEY)
    wh = bool(settings.STRIPE_WEBHOOK_SECRET or os.getenv("STRIPE_WEBHOOK_SECRET", ""))
    plan_ids = {name: bool(_env_price(name)) for name in PLAN_PRICE_ENVS}
    seat = bool(_env_price("STRIPE_PRICE_TEAM_SEAT_MONTHLY"))
    # At least one monthly plan price enables real subscription checkout.
    sub_ready = api and any(plan_ids[k] for k in _SUBSCRIPTION_MONTHLY_ENVS)
    blockers: list[str] = []
    if settings.is_production:
        if not api:
            blockers.append("STRIPE_API_KEY missing")
        if not wh:
            blockers.append("STRIPE_WEBHOOK_SECRET missing")
        if not sub_ready:
            blockers.append(
                "configure at least one of STRIPE_PRICE_{STARTER,PERSONAL,CREATOR,MAX|PRO}_MONTHLY "
                "for subscription Checkout"
            )
    return StripeStatus(
        api_key_configured=api,
        webhook_secret_configured=wh,
        plan_price_ids=plan_ids,
        seat_price_configured=seat,
        subscription_ready=sub_ready,
        production_ok=not blockers,
        blockers=blockers,
    )


def assert_stripe_production_ready() -> None:
    """Raise RuntimeError in production when Stripe cannot take payments."""
    st = stripe_status()
    if settings.is_production and not st.production_ok:
        raise RuntimeError("Stripe production blockers: " + "; ".join(st.blockers))


def stripe_bootstrap_status() -> dict:
    """Report bootstrap Price env coverage (scripts/bootstrap_stripe_prices.py)."""
    price_envs = {name: bool(_env_price(name)) for name in BOOTSTRAP_PRICE_ENVS}
    configured = sum(1 for v in price_envs.values() if v)
    monthly_ok = any(price_envs[k] for k in _SUBSCRIPTION_MONTHLY_ENVS)
    return {
        "price_envs": price_envs,
        "price_envs_configured": configured,
        "price_envs_total": len(BOOTSTRAP_PRICE_ENVS),
        "subscription_prices_ready": monthly_ok,
        "bootstrap_complete": monthly_ok and price_envs.get("STRIPE_PRICE_TEAM_SEAT_MONTHLY", False),
        "script": "scripts/bootstrap_stripe_prices.py",
        "validate_cmd": "python scripts/bootstrap_stripe_prices.py --validate",
        "dry_run_cmd": "python scripts/bootstrap_stripe_prices.py --dry-run",
    }


def validate_stripe_bootstrap() -> dict:
    """One-shot validation for CI/ops — no Stripe API calls."""
    st = stripe_status()
    bs = stripe_bootstrap_status()
    blockers: list[str] = []
    if not st.api_key_configured:
        blockers.append("STRIPE_API_KEY missing (optional in dev dry-run)")
    if not bs["subscription_prices_ready"]:
        blockers.append(
            "configure at least one STRIPE_PRICE_*_MONTHLY via bootstrap_stripe_prices.py"
        )
    ok = bs["subscription_prices_ready"]
    if settings.is_production:
        ok = st.production_ok and bs["bootstrap_complete"]
        if not st.webhook_secret_configured:
            blockers.append("STRIPE_WEBHOOK_SECRET missing")
        if not bs["bootstrap_complete"]:
            blockers.append("run bootstrap_stripe_prices.py for all plan + seat Price IDs")
    else:
        # Dev/test: structural validation passes without live Price env injection.
        ok = True
    return {
        "ok": ok,
        "bootstrap": bs,
        "stripe": st.public_dict(),
        "blockers": blockers,
    }


def stripe_checkout_readiness() -> dict:
    """Report whether /billing/checkout uses Stripe or dev-grant."""
    st = stripe_status()
    if st.api_key_configured and st.subscription_ready:
        return {
            "mode": "stripe",
            "dev_grant": False,
            "checkout_ready": True,
            "note": "Stripe Checkout 已启用（订阅/一次性）",
        }
    if settings.is_production:
        return {
            "mode": "blocked",
            "dev_grant": False,
            "checkout_ready": False,
            "note": "生产环境需配置 STRIPE_API_KEY 与 Price IDs",
            "blockers": st.blockers,
        }
    return {
        "mode": "dev_grant",
        "dev_grant": True,
        "checkout_ready": True,
        "note": "开发模式：/billing/checkout 直发积分（无 Stripe key）",
    }


def stripe_webhook_staging_check() -> dict:
    """Validate Stripe Dashboard webhook setup expectations (no Stripe API calls)."""
    secret = (settings.STRIPE_WEBHOOK_SECRET or os.getenv("STRIPE_WEBHOOK_SECRET", "") or "").strip()
    api = (settings.STRIPE_API_KEY or os.getenv("STRIPE_API_KEY", "") or "").strip()
    configured = bool(secret)
    format_ok = secret.startswith("whsec_") if configured else False
    test_key = api.startswith("sk_test_") if api else False
    live_key = api.startswith("sk_live_") if api else False
    setup_ok = configured and format_ok
    blockers: list[str] = []
    if not configured:
        blockers.append("STRIPE_WEBHOOK_SECRET missing")
    elif not format_ok:
        blockers.append("STRIPE_WEBHOOK_SECRET should start with whsec_")
    return {
        "endpoint_path": STRIPE_WEBHOOK_PATH,
        "required_events": list(REQUIRED_STRIPE_WEBHOOK_EVENTS),
        "webhook_secret_configured": configured,
        "webhook_secret_format_ok": format_ok,
        "test_mode_api_key": test_key,
        "live_mode_api_key": live_key,
        "setup_ok": setup_ok,
        "blockers": blockers,
        "dashboard_steps": [
            "Stripe Dashboard → Developers → Webhooks → Add endpoint",
            f"URL: https://<your-domain>{STRIPE_WEBHOOK_PATH}",
            f"Events: {', '.join(REQUIRED_STRIPE_WEBHOOK_EVENTS)}",
            "Copy signing secret → STRIPE_WEBHOOK_SECRET",
        ],
    }


def stripe_staging_readiness() -> dict:
    """Actionable checklist for Stripe test-mode / staging go-live."""
    st = stripe_status()
    bs = stripe_bootstrap_status()
    ck = stripe_checkout_readiness()
    success_url = (getattr(settings, "STRIPE_SUCCESS_URL", None) or os.getenv("STRIPE_SUCCESS_URL", "") or "").strip()
    cancel_url = (getattr(settings, "STRIPE_CANCEL_URL", None) or os.getenv("STRIPE_CANCEL_URL", "") or "").strip()
    checklist = [
        {"id": "api_key", "label": "STRIPE_API_KEY", "ok": st.api_key_configured, "required": True},
        {"id": "webhook_secret", "label": "STRIPE_WEBHOOK_SECRET", "ok": st.webhook_secret_configured, "required": True},
        {
            "id": "subscription_prices",
            "label": "至少一个 STRIPE_PRICE_*_MONTHLY",
            "ok": bs["subscription_prices_ready"],
            "required": True,
        },
        {"id": "success_url", "label": "STRIPE_SUCCESS_URL → /billing/success", "ok": bool(success_url), "required": True},
        {"id": "cancel_url", "label": "STRIPE_CANCEL_URL", "ok": bool(cancel_url), "required": True},
        {
            "id": "checkout_stripe_mode",
            "label": "Checkout mode=stripe",
            "ok": ck.get("mode") == "stripe",
            "required": False,
        },
    ]
    blockers = [c["label"] for c in checklist if c.get("required") and not c["ok"]]
    wh = stripe_webhook_staging_check()
    blockers.extend(wh.get("blockers") or [])
    sig_test = stripe_webhook_signature_self_test()
    if wh.get("setup_ok") and not sig_test.get("self_test_ok"):
        blockers.append("Stripe webhook signature self-test failed")
    staging_ready = (
        st.api_key_configured
        and st.webhook_secret_configured
        and bs["subscription_prices_ready"]
        and bool(success_url)
        and bool(cancel_url)
        and wh.get("setup_ok", False)
        and sig_test.get("self_test_ok", False)
    )
    return {
        "staging_ready": staging_ready,
        "checklist": checklist,
        "checkout": ck,
        "bootstrap": bs,
        "blockers": blockers,
        "webhook_config": wh,
        "webhook_signature_self_test": sig_test,
        "webhook_events": list(REQUIRED_STRIPE_WEBHOOK_EVENTS),
        "webhook_endpoint": STRIPE_WEBHOOK_PATH,
        "success_page_path": "/billing/success?session_id={CHECKOUT_SESSION_ID}",
        "sync_fallback": "POST /billing/stripe/sync?session_id=…",
    }
