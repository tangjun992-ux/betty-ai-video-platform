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
