"""
Stripe production readiness helpers.
"""
from __future__ import annotations

import os
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

# Minimum monthly prices that unlock real subscription Checkout mode.
_SUBSCRIPTION_MONTHLY_ENVS = (
    "STRIPE_PRICE_STARTER_MONTHLY",
    "STRIPE_PRICE_PERSONAL_MONTHLY",
    "STRIPE_PRICE_CREATOR_MONTHLY",
    "STRIPE_PRICE_MAX_MONTHLY",
    "STRIPE_PRICE_PRO_MONTHLY",  # legacy alias of Max
)


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
