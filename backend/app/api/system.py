"""System capabilities — demo vs real mode for honest UI disclosure."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/capabilities", summary="平台能力（demo / 真实生成）")
async def capabilities():
    from app.adapters.demo_provider import any_provider_configured, demo_mode_active
    from app.api.director import _dry_run_default
    from app.services.model_catalog import catalog_integrity

    configured = any_provider_configured()
    demo = demo_mode_active()
    catalog = catalog_integrity()
    return {
        "demo_mode": demo,
        "providers_configured": configured,
        "real_generation_available": configured and not _dry_run_default(),
        "director_dry_run_default": _dry_run_default(),
        "verified_model_count": catalog["active_count"],
        "catalog_total": catalog["total"],
        "label": "真实生成可用" if (configured and not _dry_run_default()) else "预览模式（未配置模型 Key）",
        # Honest motion disclosure: dedicated path exists but provider may treat
        # videoUrl as best-effort (not Kling Motion Control / Runway Act-One grade).
        "features": {
            "motion_transfer": {
                "available": configured and not demo,
                "mode": "best_effort",
                "note": "专用 motion 通道已启用（imageUrl+videoUrl）；上游可能降级为图生视频+动作提示，非原生 Motion Control SKU。",
            },
            "task_webhooks": {
                "available": True,
                "note": "任务完成/失败时 POST webhook_url，HMAC 签名头 X-Betty-Signature。",
            },
            "share_permalink": {
                "available": True,
                "path": "/explore/{task_id}",
            },
        },
    }


@router.get("/slo", summary="核心能力 SLO 快照")
async def slo_snapshot():
    """Ops-facing SLOs for lipsync / motion / generation health."""
    from app.api.models_info import MODELS
    from app.services.model_health import model_health
    from app.services.model_catalog import catalog_integrity
    from app.adapters.demo_provider import demo_mode_active

    active = [m for m in MODELS if m.status == "active"]
    rows = []
    for m in active:
        snap = model_health.snapshot(m.id)
        rows.append({
            "model_id": m.id,
            "media": m.capabilities.media_types,
            "success_rate": snap.success_rate,
            "avg_latency_ms": snap.avg_latency_ms,
            "circuit_open": snap.circuit_open,
            "quarantined": model_health.is_quarantined(m.id),
            "score": snap.score,
        })
    return {
        "demo_mode": demo_mode_active(),
        "catalog": catalog_integrity(),
        "targets": {
            "generation_success_rate": 0.95,
            "lipsync_p95_latency_s": 90,
            "motion_p95_latency_s": 120,
        },
        "models": rows,
    }


@router.get("/catalog", summary="模型目录诚信报告")
async def catalog_report():
    from app.services.model_catalog import catalog_integrity
    return catalog_integrity()


@router.get("/readiness", summary="生产就绪检查（Stripe/CDN/SSO）")
async def readiness():
    from app.services.stripe_ready import stripe_status
    from app.services.storage_ready import storage_status
    from app.api.oidc import oidc_status
    from app.config import settings

    stripe = stripe_status().public_dict()
    storage = storage_status().public_dict()
    sso = oidc_status()
    ok = True
    if settings.is_production:
        ok = stripe["production_ok"] and storage["production_ok"]
    return {
        "ok": ok,
        "env": settings.ENV,
        "stripe": stripe,
        "storage": storage,
        "sso": sso,
    }
