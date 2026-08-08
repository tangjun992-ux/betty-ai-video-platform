"""Automated staging runbook execution — runs self-tests in sequence."""
from __future__ import annotations

import time

from sqlalchemy.ext.asyncio import AsyncSession


def _step_result(
    step_id: str,
    title: str,
    *,
    ok: bool,
    executed: bool = True,
    optional: bool = False,
    detail: dict | None = None,
    error: str | None = None,
    started: float | None = None,
) -> dict:
    return {
        "id": step_id,
        "title": title,
        "executed": executed,
        "optional": optional,
        "ok": ok,
        "error": error,
        "detail": detail or {},
        "duration_ms": int((time.monotonic() - started) * 1000) if started else 0,
    }


async def execute_staging_runbook(
    db: AsyncSession,
    *,
    guest_id: str = "runbook-exec-guest",
    strict: bool = False,
) -> dict:
    """Run automatable runbook checks and return consolidated report."""
    from app.config import settings
    from app.services.staging_env import staging_env_audit
    from app.services.stripe_ready import (
        stripe_webhook_delivery_test,
        stripe_webhook_signature_self_test,
        validate_stripe_bootstrap,
    )
    from app.services.oidc_ready import oidc_configured, oidc_discovery_probe
    from app.services.staging_checkout import run_staging_checkout_smoke
    from app.services.go_live_ready import staging_acceptance_scorecard, staging_runbook
    from app.services.guest import get_or_create_guest_user

    results: list[dict] = []

    t0 = time.monotonic()
    audit = staging_env_audit()
    results.append(_step_result(
        "env_audit",
        "环境变量审计",
        ok=audit.get("staging_ready_without_live", False),
        detail={"missing_required": audit.get("missing_required"), "groups": audit.get("groups")},
        started=t0,
    ))

    t0 = time.monotonic()
    bootstrap = validate_stripe_bootstrap()
    results.append(_step_result(
        "stripe_bootstrap",
        "Stripe Bootstrap 校验",
        ok=bool(bootstrap.get("ok")) if settings.STRIPE_API_KEY else True,
        optional=not bool(settings.STRIPE_API_KEY),
        detail={"bootstrap": bootstrap.get("bootstrap"), "blockers": bootstrap.get("blockers", [])},
        started=t0,
    ))

    t0 = time.monotonic()
    sig = stripe_webhook_signature_self_test()
    whsec_ok = bool(sig.get("self_test_ok"))
    whsec_configured = bool(sig.get("configured"))
    results.append(_step_result(
        "webhook_self_test",
        "Webhook whsec 签名校验",
        ok=whsec_ok if whsec_configured else True,
        optional=not whsec_configured,
        executed=whsec_configured,
        detail=sig,
        started=t0,
    ))

    if whsec_configured:
        t0 = time.monotonic()
        deliver = await stripe_webhook_delivery_test()
        results.append(_step_result(
            "webhook_deliver",
            "Webhook HTTP 投递",
            ok=bool(deliver.get("delivery_ok")),
            detail=deliver,
            started=t0,
        ))

    if oidc_configured():
        t0 = time.monotonic()
        probe = oidc_discovery_probe()
        results.append(_step_result(
            "oidc_discovery",
            "OIDC Discovery 探测",
            ok=bool(probe.get("probe_ok")),
            optional=True,
            detail={"probe_ok": probe.get("probe_ok"), "error": probe.get("error")},
            started=t0,
        ))

    t0 = time.monotonic()
    uid = await get_or_create_guest_user(db, guest_id)
    await db.commit()
    checkout = await run_staging_checkout_smoke(db, uid)
    results.append(_step_result(
        "checkout_smoke",
        "收款链路自测",
        ok=bool(checkout.get("ok")),
        detail=checkout,
        started=t0,
    ))

    t0 = time.monotonic()
    acceptance = staging_acceptance_scorecard(strict=strict)
    results.append(_step_result(
        "acceptance",
        "验收记分卡",
        ok=bool(acceptance.get("acceptance_ok")),
        detail={"score_pct": acceptance.get("score_pct"), "checks": acceptance.get("checks")},
        started=t0,
    ))

    required = [r for r in results if r.get("executed") and not r.get("optional")]
    execute_ok = all(r["ok"] for r in required) if required else False
    runbook = staging_runbook()

    return {
        "execute_ok": execute_ok,
        "strict": strict,
        "steps_executed": sum(1 for r in results if r.get("executed")),
        "steps_passed": sum(1 for r in results if r.get("executed") and r.get("ok")),
        "steps_total": len(results),
        "results": results,
        "acceptance": acceptance,
        "runbook_summary": {
            "steps_done": runbook.get("steps_done"),
            "steps_total": runbook.get("steps_total"),
            "score_pct": runbook.get("score_pct"),
        },
        "env": settings.ENV,
    }
