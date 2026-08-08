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
            "stripe_bootstrap": "python scripts/bootstrap_stripe_prices.py --validate",
            "live_kpi_admin": "POST /admin/model-health/smoke/live-kpi",
        },
    }
