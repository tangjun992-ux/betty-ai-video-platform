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
        # Native Kling Motion Control via KIE; not Runway Act-One.
        "features": {
            "motion_transfer": {
                "available": configured and not demo,
                "mode": "native",
                "sku": "kling-3.0/motion-control",
                "note": "原生 Kling Motion Control（KIE kling-3.0/motion-control：input_urls+video_urls）；非 Runway Act-One。失败时任务层可回退 Seedance。",
            },
            "task_webhooks": {
                "available": True,
                "note": "任务完成/失败时 POST webhook_url，HMAC 签名头 X-Betty-Signature。",
            },
            "share_permalink": {
                "available": True,
                "path": "/explore/{task_id}",
                "requires_publish": True,
                "note": "须调用 POST /gallery/share/{task_id}/publish 后 permalink 才公开。",
            },
            "failure_refund": {
                "available": True,
                "note": "任务 failed/cancelled 时幂等退还预扣积分；调度失败与图像工具失败同步退款。",
            },
            "live_video_weekly_smoke": {
                "available": True,
                "gated_by": "MODEL_SMOKE_LIVE_VIDEO_WEEKLY=1",
                "note": "周检仅在显式开启时跑付费 live_video；live_skipped 不计 outframe_ok。",
            },
            "multi_reference_i2i": {
                "available": True,
                "max_refs": 4,
                "note": "GenerateRequest.reference_images → Celery edit_image 真 i2i。",
            },
            "seedance_omni": {
                "available": configured and not demo,
                "path": "/create/video",
                "models": ["seedance-2.0", "seedance-2.0-fast"],
                "inputs": [
                    "reference_images", "reference_videos", "reference_audios",
                    "generate_audio", "storyboard_omni",
                ],
                "note": (
                    "Seedance Omni 一体：多图/视频/音频参考 + generate_audio；"
                    "真分镜 storyboard 可共享 Omni refs；"
                    "口型仍走 /lipsync（kling avatar），非 Act-One。"
                ),
            },
            "storyboard": {
                "available": True,
                "path": "/director/storyboard",
                "note": "显式多镜头计划（每镜独立 video step）；可携带 Omni reference_* / generate_audio。",
            },
            "face_swap": {
                "available": configured and not demo,
                "mode": "i2i_edit",
                "sku": "google/nano-banana-edit",
                "path": "/create/face-swap",
                "api": "/face-swap",
                "note": "双图换脸已 live 验证（nano-banana-edit createTask→出图）。i2i 指令合成，非 InsightFace/Roop 像素级换脸。",
            },
            "tool_cost_board": {
                "available": True,
                "path": "/pricing/costs",
                "note": "image_tool 任务记录 charged_credits vs upstream res.cost。",
            },
            "prompt_extractor": {
                "available": True,
                "path": "/generate/extract-prompt",
                "modes": ["vision", "heuristic"],
                "note": "对标 Yapper Prompt Extractor；有 LLM Key 走 vision，否则诚实 heuristic。社媒页：YouTube oEmbed/yt-dlp 封面可解析；TikTok/IG 尽力而为（IP 封锁时诚实失败）。",
                "social_page_urls": {
                    "youtube": True,
                    "tiktok": "best_effort",
                    "instagram": "best_effort",
                    "x": "best_effort",
                    "douyin": False,
                    "xiaohongshu": False,
                },
            },
            "talking_avatar": {
                "available": True,
                "path": "/create/avatar",
                "backend": "/lipsync",
                "note": "Talking Avatar UI 走唇形同步链路（图+音频/文本）。",
            },
            "performance_drive": {
                "available": configured and not demo,
                "mode": "motion_plus_optional_lipsync",
                "path": "/create/performance",
                "api": "/performance",
                "sku": ["kling-3.0/motion-control", "kling/ai-avatar-pro"],
                "note": "Betty Performance Drive：原生 Motion + 可选 Lipsync 口播分轨。不是 Runway Act-One 表演编码器。",
            },
            "director_minimal": {
                "available": True,
                "note": "PlanRequest.minimal / 快速成片：enhance→1图→1视，跳过配音字幕合成。",
            },
            "live_smoke": {
                "image_sample": "scripts/smoke_live_image_sample.py",
                "video_sample": "scripts/smoke_live_video_sample.py",
                "gates": ["MODEL_SMOKE_LIVE", "MODEL_SMOKE_LIVE_VIDEO", "MODEL_SMOKE_LIVE_*_WEEKLY"],
                "note": "outframe_ok 仅计入真出片；mapping 不再污染 Auto 路由成功率。",
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
        "last_smoke": _public_last_smoke(),
    }


def _public_last_smoke() -> dict | None:
    from app.services.model_smoke import get_last_smoke
    report = get_last_smoke()
    if not report:
        return None
    return {
        "ts": report.get("ts"),
        "mode": report.get("mode"),
        "probed": report.get("probed", 0),
        "ok": report.get("ok", 0),
        "outframe_ok": report.get("outframe_ok", 0),
        "outframe_skipped": report.get("outframe_skipped", 0),
        "failed_count": len(report.get("failed") or []),
        "quarantined_count": len(report.get("quarantined") or []),
        "skipped_count": len(report.get("skipped") or []),
        "failed": list(report.get("failed") or [])[:12],
        "skipped": list(report.get("skipped") or [])[:12],
    }


@router.get("/catalog", summary="模型目录诚信报告")
async def catalog_report():
    from app.services.model_catalog import catalog_integrity
    return catalog_integrity()


@router.get("/readiness", summary="生产就绪检查（Stripe/CDN/SSO）")
async def readiness():
    from app.services.stripe_ready import stripe_status
    from app.services.storage_ready import storage_status
    from app.services.oidc_ready import oidc_status
    from app.config import settings

    stripe = stripe_status().public_dict()
    storage = storage_status().public_dict()
    sso = oidc_status(discover=False).public_dict()
    ok = True
    if settings.is_production:
        ok = (
            stripe["production_ok"]
            and storage["production_ok"]
            and sso.get("production_ok", True)
        )
    return {
        "ok": ok,
        "env": settings.ENV,
        "stripe": stripe,
        "storage": storage,
        "sso": sso,
    }
