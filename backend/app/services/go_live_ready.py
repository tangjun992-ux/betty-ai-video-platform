"""Unified go-live readiness — Stripe + Storage/CDN + live smoke KPI."""
from __future__ import annotations

import time

from app.config import settings


def live_smoke_kpi(*, last_smoke: dict | None = None) -> dict:
    """Honest live outframe KPI (WORLD_CLASS_BENCHMARK 80+ gates)."""
    from app.services.model_smoke import get_last_smoke

    report = last_smoke if last_smoke is not None else get_last_smoke()
    targets = {"video_outframe_min": 2, "image_outframe_min": 1}
    if not report:
        return {
            "available": False,
            "kpi_met": False,
            "video_outframe_ok": 0,
            "image_outframe_ok": 0,
            "targets": targets,
            "mode": None,
            "ts": None,
            "note": "尚未运行 live smoke（需 MODEL_SMOKE_LIVE* 显式开启）",
        }

    details = report.get("details") or []

    def _path(d: dict) -> str:
        ev = d.get("evidence") if isinstance(d.get("evidence"), dict) else {}
        return str((ev or {}).get("path") or d.get("path") or d.get("media_type") or "")

    video_ok = sum(1 for d in details if d.get("ok") and "video" in _path(d))
    image_ok = sum(1 for d in details if d.get("ok") and "image" in _path(d))
    mode = report.get("mode") or ""
    if mode == "live_kpi_combined":
        image_ok = max(image_ok, int((report.get("image_sample") or {}).get("outframe_ok") or 0))
        video_ok = max(video_ok, int((report.get("video_sample") or {}).get("outframe_ok") or 0))
    outframe = int(report.get("outframe_ok") or 0)
    if video_ok == 0 and "video" in mode:
        video_ok = outframe
    if image_ok == 0 and "image" in mode:
        image_ok = outframe
    if video_ok == 0 and image_ok == 0 and outframe > 0:
        # Legacy combined report — count as partial credit on video axis only.
        video_ok = outframe

    kpi_met = video_ok >= targets["video_outframe_min"] and image_ok >= targets["image_outframe_min"]
    return {
        "available": True,
        "kpi_met": kpi_met,
        "video_outframe_ok": video_ok,
        "image_outframe_ok": image_ok,
        "targets": targets,
        "mode": mode,
        "ts": report.get("ts"),
        "failed": list(report.get("failed") or [])[:8],
        "note": "KPI 达标" if kpi_met else f"需 video≥{targets['video_outframe_min']} image≥{targets['image_outframe_min']}",
    }


def go_live_readiness(*, last_smoke: dict | None = None) -> dict:
    """Aggregate staging checklist for revenue + media delivery + live KPI."""
    from app.services.stripe_ready import stripe_staging_readiness
    from app.services.storage_ready import storage_staging_readiness
    from app.services.oidc_ready import oidc_status, oidc_staging_readiness

    stripe = stripe_staging_readiness()
    storage = storage_staging_readiness()
    live = live_smoke_kpi(last_smoke=last_smoke)
    oidc = oidc_status(discover=False).public_dict()
    oidc_staging = oidc_staging_readiness(discover=False)

    blockers: list[str] = []
    blockers.extend(stripe.get("blockers") or [])
    blockers.extend(storage.get("blockers") or [])
    if oidc_staging.get("required_in_production") and not oidc_staging.get("staging_ready"):
        blockers.extend(oidc_staging.get("blockers") or [])
    if settings.is_production and not oidc.get("production_ok"):
        blockers.extend(oidc.get("blockers") or [])
    if live.get("available") and not live.get("kpi_met"):
        blockers.append(live.get("note") or "live smoke KPI not met")

    revenue_ready = bool(stripe.get("staging_ready"))
    media_ready = bool(storage.get("staging_ready"))
    live_ready = live.get("kpi_met") if live.get("available") else None

    go_live_ok = revenue_ready and media_ready
    if settings.is_production:
        go_live_ok = go_live_ok and oidc_staging.get("staging_ready", True)
        if live.get("available"):
            go_live_ok = go_live_ok and bool(live.get("kpi_met"))

    return {
        "go_live_ok": go_live_ok,
        "revenue_ready": revenue_ready,
        "media_ready": media_ready,
        "live_kpi_ready": live_ready,
        "sso_ready": bool(oidc_staging.get("staging_ready")),
        "stripe": stripe,
        "storage": storage,
        "live_kpi": live,
        "oidc": oidc_staging,
        "blockers": blockers,
        "env": settings.ENV,
    }


def staging_go_live_report(*, last_smoke: dict | None = None) -> dict:
    """Full staging acceptance report with next-step guidance for ops/CI."""
    from app.services.model_smoke import get_last_smoke
    from app.services.ops_alerts import ops_alerts_status

    smoke = last_smoke if last_smoke is not None else get_last_smoke()
    gl = go_live_readiness(last_smoke=smoke)
    next_steps: list[str] = []

    if not gl.get("revenue_ready"):
        next_steps.append("配置 Stripe：STRIPE_API_KEY、STRIPE_WEBHOOK_SECRET、Price IDs、SUCCESS/CANCEL URL")
        wh = (gl.get("stripe") or {}).get("webhook_config") or {}
        if wh.get("blockers"):
            next_steps.append(f"Stripe Webhook：{'; '.join(wh['blockers'][:2])}")
        sig = (gl.get("stripe") or {}).get("webhook_signature_self_test") or {}
        if wh.get("setup_ok") and not sig.get("self_test_ok"):
            next_steps.append(f"Stripe Webhook 签名校验自测失败：{sig.get('error') or 'unknown'}")
    if not gl.get("media_ready"):
        next_steps.append("配置 CDN/S3：STORAGE_TYPE=s3、AWS_*、MEDIA_CDN_BASE_URL")
    if gl.get("oidc", {}).get("required_in_production") and not gl.get("sso_ready"):
        next_steps.append("配置 OIDC：OIDC_ISSUER、CLIENT_ID、CLIENT_SECRET、REDIRECT_URI")
    elif gl.get("oidc", {}).get("configured") and not (gl.get("oidc") or {}).get("discovery_probe"):
        next_steps.append("在 Admin Ops 点击「OIDC Discovery 探测」验证 IdP /.well-known")
    live = gl.get("live_kpi") or {}
    if not live.get("available"):
        next_steps.append("在 Admin Ops 触发 Live KPI 抽样，或设置 MODEL_SMOKE_LIVE* 后运行 scripts/staging_go_live_check.py --live")
    elif not live.get("kpi_met"):
        next_steps.append(f"Live KPI 未达标：{live.get('note')}")

    ops = ops_alerts_status()
    if not ops.get("webhook_failure_alerts"):
        next_steps.append("可选：配置 OPS_ALERT_WEBHOOK_URL 接收 Webhook 失败告警")

    dims = {
        "revenue": bool(gl.get("revenue_ready")),
        "media": bool(gl.get("media_ready")),
        "sso": bool(gl.get("sso_ready")),
        "live_kpi": live.get("kpi_met") if live.get("available") else None,
    }
    ok_count = sum(1 for v in dims.values() if v is True)
    pending = sum(1 for v in dims.values() if v is False)

    return {
        **gl,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "dimensions": dims,
            "dimensions_ok": ok_count,
            "dimensions_pending": pending,
            "dimensions_unknown": sum(1 for v in dims.values() if v is None),
            "blocker_count": len(gl.get("blockers") or []),
        },
        "next_steps": next_steps,
        "ops_alerts": ops,
        "last_smoke_ts": (smoke or {}).get("ts"),
        "commands": {
            "staging_check": "python scripts/staging_go_live_check.py",
            "staging_strict": "python scripts/staging_go_live_check.py --strict --require-webhook",
            "staging_live": "python scripts/staging_go_live_check.py --live",
            "stripe_bootstrap": "python scripts/bootstrap_stripe_prices.py --validate",
            "live_kpi_admin": "POST /admin/model-health/smoke/live-kpi",
            "webhook_deliver_test": "POST /billing/stripe-webhook-deliver-test",
            "staging_runbook": "python scripts/staging_runbook.py",
            "staging_env_audit": "python scripts/staging_env_audit.py",
            "staging_checkout_smoke": "POST /billing/staging-checkout-smoke",
            "stripe_cli_listen": "stripe listen --forward-to localhost:8000/api/v1/billing/stripe/webhook",
        },
    }


def staging_acceptance_scorecard(*, last_smoke: dict | None = None, strict: bool = False) -> dict:
    """Compact staging acceptance view for ops dashboards and CI gates."""
    report = staging_go_live_report(last_smoke=last_smoke)
    stripe = report.get("stripe") or {}
    wh = stripe.get("webhook_config") or {}
    sig = stripe.get("webhook_signature_self_test") or {}
    live = report.get("live_kpi") or {}
    oidc = report.get("oidc") or {}

    def _status(ok: bool | None) -> str:
        if ok is True:
            return "pass"
        if ok is False:
            return "fail"
        return "skip"

    checks = [
        {"id": "revenue", "label": "Stripe 收款就绪", "status": _status(report.get("revenue_ready")), "required": True},
        {"id": "webhook_config", "label": "Webhook Dashboard 配置", "status": _status(wh.get("setup_ok")), "required": True},
        {"id": "webhook_signature", "label": "Webhook whsec 签名校验", "status": _status(sig.get("self_test_ok")), "required": True},
        {"id": "media", "label": "CDN/S3 媒体分发", "status": _status(report.get("media_ready")), "required": True},
        {
            "id": "sso",
            "label": "OIDC/SSO",
            "status": _status(report.get("sso_ready")) if oidc.get("required_in_production") or oidc.get("configured") else "skip",
            "required": bool(oidc.get("required_in_production")),
        },
        {
            "id": "live_kpi",
            "label": "Live KPI 出片",
            "status": _status(live.get("kpi_met")) if live.get("available") else "skip",
            "required": strict and bool(live.get("available")),
        },
    ]
    required_checks = [c for c in checks if c.get("required")]
    required_pass = sum(1 for c in required_checks if c["status"] == "pass")
    scored = [c for c in checks if c["status"] in ("pass", "fail")]
    score_pct = round(100 * sum(1 for c in scored if c["status"] == "pass") / len(scored)) if scored else 0

    acceptance_ok = all(c["status"] == "pass" for c in required_checks)

    return {
        "acceptance_ok": acceptance_ok,
        "strict": strict,
        "score_pct": score_pct,
        "checks": checks,
        "checks_pass": sum(1 for c in checks if c["status"] == "pass"),
        "checks_fail": sum(1 for c in checks if c["status"] == "fail"),
        "checks_skip": sum(1 for c in checks if c["status"] == "skip"),
        "required_pass": required_pass,
        "required_total": len(required_checks),
        "go_live_ok": report.get("go_live_ok"),
        "revenue_ready": report.get("revenue_ready"),
        "media_ready": report.get("media_ready"),
        "live_kpi_ready": report.get("live_kpi_ready"),
        "blockers": report.get("blockers") or [],
        "next_steps": report.get("next_steps") or [],
        "generated_at": report.get("generated_at"),
        "stripe": {
            "webhook_config": wh,
            "webhook_signature_self_test": sig,
            "staging_ready": stripe.get("staging_ready"),
        },
        "env": report.get("env"),
    }


def staging_runbook(*, last_smoke: dict | None = None, host: str = "localhost:8000") -> dict:
    """Ordered staging go-live runbook with step status and copy-paste commands."""
    from app.services.stripe_ready import (
        stripe_bootstrap_status,
        stripe_cli_webhook_guide,
        stripe_staging_readiness,
        stripe_webhook_signature_self_test,
    )
    from app.services.storage_ready import storage_staging_readiness
    from app.services.oidc_ready import oidc_staging_readiness

    scorecard = staging_acceptance_scorecard(last_smoke=last_smoke, strict=False)
    from app.services.staging_env import staging_env_audit

    env_audit = staging_env_audit()
    stripe = stripe_staging_readiness()
    storage = storage_staging_readiness()
    bootstrap = stripe_bootstrap_status()
    cli = stripe_cli_webhook_guide(host=host)
    sig = stripe_webhook_signature_self_test()
    oidc = oidc_staging_readiness(discover=False)
    live = scorecard.get("live_kpi_ready")

    def step_status(ok: bool | None, *, optional: bool = False) -> str:
        if ok is True:
            return "done"
        if ok is False:
            return "pending"
        return "skipped" if optional else "pending"

    steps = [
        {
            "id": "stripe_bootstrap",
            "title": "Stripe Price Bootstrap",
            "status": step_status(bootstrap.get("subscription_prices_ready")),
            "commands": [
                "python scripts/bootstrap_stripe_prices.py --dry-run --json-only",
                "STRIPE_API_KEY=sk_test_... python scripts/bootstrap_stripe_prices.py --write-env .env",
                "python scripts/bootstrap_stripe_prices.py --validate --json-only",
            ],
            "env_keys": list(bootstrap.get("price_envs", {}).keys())[:4] + ["STRIPE_API_KEY"],
        },
        {
            "id": "stripe_env",
            "title": "Stripe 收款环境变量",
            "status": step_status(stripe.get("staging_ready")),
            "commands": [
                "export STRIPE_API_KEY=sk_test_...",
                "export STRIPE_WEBHOOK_SECRET=whsec_...",
                "export STRIPE_SUCCESS_URL=http://localhost:3000/billing/success",
                "export STRIPE_CANCEL_URL=http://localhost:3000/pricing",
            ],
            "env_keys": ["STRIPE_API_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_SUCCESS_URL", "STRIPE_CANCEL_URL"],
        },
        {
            "id": "stripe_cli_webhook",
            "title": "Stripe CLI 本地 Webhook 转发",
            "status": step_status(sig.get("self_test_ok") if stripe.get("webhook_config", {}).get("setup_ok") else False, optional=True),
            "commands": [cli["listen_command"], cli["whsec_hint"]],
            "env_keys": ["STRIPE_WEBHOOK_SECRET"],
            "notes": cli.get("local_dev_steps") or [],
        },
        {
            "id": "webhook_verify",
            "title": "Webhook 签名 + 投递自测",
            "status": step_status(sig.get("self_test_ok")),
            "commands": [
                "curl http://localhost:8000/api/v1/billing/stripe-webhook-self-test",
                "curl -X POST http://localhost:8000/api/v1/billing/stripe-webhook-deliver-test",
            ],
            "env_keys": ["STRIPE_WEBHOOK_SECRET"],
        },
        {
            "id": "cdn_storage",
            "title": "CDN / S3 媒体分发",
            "status": step_status(storage.get("staging_ready"), optional=not storage.get("blockers")),
            "commands": [
                "export STORAGE_TYPE=s3",
                "export AWS_ACCESS_KEY_ID=... AWS_S3_BUCKET=...",
                "export MEDIA_CDN_BASE_URL=https://cdn.example.com",
            ],
            "env_keys": ["STORAGE_TYPE", "AWS_S3_BUCKET", "MEDIA_CDN_BASE_URL"],
        },
        {
            "id": "oidc_sso",
            "title": "OIDC / SSO（企业可选）",
            "status": step_status(oidc.get("staging_ready") if oidc.get("configured") or oidc.get("required_in_production") else None, optional=not oidc.get("required_in_production")),
            "commands": [
                "export OIDC_ISSUER=https://idp.example.com",
                "curl http://localhost:8000/api/v1/auth/oidc/discovery-check",
            ],
            "env_keys": ["OIDC_ISSUER", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET", "OIDC_REDIRECT_URI"],
        },
        {
            "id": "live_kpi",
            "title": "Live KPI 出片抽样",
            "status": step_status(live if live is not None else None, optional=True),
            "commands": [
                "export MODEL_SMOKE_LIVE=1  # 或 MODEL_SMOKE_LIVE_VIDEO=1",
                "python scripts/staging_go_live_check.py --live",
                "POST /admin/model-health/smoke/live-kpi",
            ],
            "env_keys": ["MODEL_SMOKE_LIVE", "MODEL_SMOKE_LIVE_VIDEO"],
        },
        {
            "id": "checkout_smoke",
            "title": "收款链路自测（checkout → webhook → 积分）",
            "status": "pending",
            "commands": [
                "curl -X POST http://localhost:8000/api/v1/billing/staging-checkout-smoke -H 'X-Guest-Id: staging-smoke'",
            ],
            "env_keys": [],
        },
        {
            "id": "final_acceptance",
            "title": "最终验收",
            "status": step_status(scorecard.get("acceptance_ok")),
            "commands": [
                "python scripts/staging_go_live_check.py --strict --require-webhook",
                "python scripts/staging_go_live_check.py --json-only",
                "curl http://localhost:8000/api/v1/system/staging-acceptance?strict=true",
            ],
            "env_keys": [],
        },
    ]
    done = sum(1 for s in steps if s["status"] == "done")
    pending = sum(1 for s in steps if s["status"] == "pending")

    return {
        "generated_at": scorecard.get("generated_at"),
        "env": scorecard.get("env"),
        "acceptance_ok": scorecard.get("acceptance_ok"),
        "score_pct": scorecard.get("score_pct"),
        "steps_done": done,
        "steps_pending": pending,
        "steps_total": len(steps),
        "steps": steps,
        "stripe_cli": cli,
        "env_audit": env_audit,
        "blockers": scorecard.get("blockers") or [],
        "next_steps": scorecard.get("next_steps") or [],
    }
