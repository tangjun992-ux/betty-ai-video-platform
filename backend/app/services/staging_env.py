"""Staging environment variable audit — gaps before go-live."""
from __future__ import annotations

import os

from app.config import settings

ENV_SPECS = (
    {"key": "STRIPE_API_KEY", "group": "stripe", "required": True, "label": "Stripe API key"},
    {"key": "STRIPE_WEBHOOK_SECRET", "group": "stripe", "required": True, "label": "Webhook signing secret"},
    {"key": "STRIPE_PRICE_STARTER_MONTHLY", "group": "stripe", "required": True, "label": "Starter monthly price"},
    {"key": "STRIPE_SUCCESS_URL", "group": "stripe", "required": True, "label": "Checkout success URL"},
    {"key": "STRIPE_CANCEL_URL", "group": "stripe", "required": True, "label": "Checkout cancel URL"},
    {"key": "STORAGE_TYPE", "group": "media", "required": False, "label": "Storage backend"},
    {"key": "AWS_ACCESS_KEY_ID", "group": "media", "required": False, "label": "AWS access key"},
    {"key": "AWS_S3_BUCKET", "group": "media", "required": False, "label": "S3 bucket"},
    {"key": "MEDIA_CDN_BASE_URL", "group": "media", "required": False, "label": "CDN base URL"},
    {"key": "MODEL_SMOKE_LIVE", "group": "live_kpi", "required": False, "label": "Live image smoke"},
    {"key": "MODEL_SMOKE_LIVE_VIDEO", "group": "live_kpi", "required": False, "label": "Live video smoke"},
    {"key": "OIDC_ISSUER", "group": "oidc", "required": False, "label": "OIDC issuer"},
    {"key": "OIDC_CLIENT_ID", "group": "oidc", "required": False, "label": "OIDC client id"},
    {"key": "OIDC_CLIENT_SECRET", "group": "oidc", "required": False, "label": "OIDC client secret"},
    {"key": "OIDC_REDIRECT_URI", "group": "oidc", "required": False, "label": "OIDC redirect URI"},
    {"key": "OPS_ALERT_WEBHOOK_URL", "group": "ops", "required": False, "label": "Ops alert webhook"},
)


def _env_value(key: str) -> str:
    val = getattr(settings, key, None)
    if val is not None and str(val).strip():
        return str(val).strip()
    return (os.getenv(key) or "").strip()


def staging_env_audit() -> dict:
    """Report configured vs missing staging env vars by group."""
    items: list[dict] = []
    groups: dict[str, dict] = {}
    missing_required: list[str] = []

    for spec in ENV_SPECS:
        key = spec["key"]
        configured = bool(_env_value(key))
        item = {
            **spec,
            "configured": configured,
        }
        items.append(item)
        g = spec["group"]
        groups.setdefault(g, {"total": 0, "configured": 0, "missing": []})
        groups[g]["total"] += 1
        if configured:
            groups[g]["configured"] += 1
        else:
            groups[g]["missing"].append(key)
        if spec.get("required") and not configured:
            missing_required.append(key)

    stype = (settings.STORAGE_TYPE or "local").lower()
    if settings.is_production and stype == "s3":
        for k in ("AWS_ACCESS_KEY_ID", "AWS_S3_BUCKET", "MEDIA_CDN_BASE_URL"):
            if not _env_value(k) and k not in missing_required:
                missing_required.append(k)

    return {
        "env": settings.ENV,
        "missing_required": missing_required,
        "items": items,
        "groups": groups,
        "env_file_hint": "cp .env.staging.example .env.staging && fill sk_test_/whsec_/price_ values",
        "demo_export_snippet": (
            "export STRIPE_API_KEY=sk_test_... STRIPE_WEBHOOK_SECRET=whsec_... "
            "STRIPE_PRICE_STARTER_MONTHLY=price_... "
            "STRIPE_SUCCESS_URL=http://localhost:3000/billing/success "
            "STRIPE_CANCEL_URL=http://localhost:3000/pricing"
        ),
        "staging_ready_without_live": not missing_required,
    }
