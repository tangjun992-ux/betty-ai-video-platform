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
                "modes": ["vision", "heuristic", "metadata"],
                "note": (
                    "对标 Yapper Prompt Extractor + URL-to-Viral。"
                    "有 LLM Key 走 vision，否则诚实 heuristic。"
                    "YouTube/TikTok 官方 oEmbed（标题+封面）；Instagram/X 尽力而为。"
                    "结构模板来自投放规格，不是原片逐帧反推。"
                ),
                "social_page_urls": {
                    "youtube": True,
                    "tiktok": "oembed",
                    "instagram": "best_effort",
                    "x": "best_effort",
                    "douyin": False,
                    "xiaohongshu": False,
                },
            },
            "url_to_viral": {
                "available": True,
                "path": "/create/extract",
                "api": ["/generate/extract-prompt", "/generate/viral-spec"],
                "mode": "oembed_plus_placement_beats",
                "note": (
                    "官方 oEmbed 元数据 + 投放规格分镜（钩子/展开/收束）。"
                    "不是原片下载，不是逐帧结构反推。IG 仍需上传或直链。"
                ),
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
            "photo_packs": {
                "available": True,
                "path": ["/create/product", "/create/headshots", "/create/photo-packs"],
                "api": ["/generate/packs", "/generate/pack", "/generate/pack/quote"],
                "mode": "batch_sku",
                "note": "Product/Headshots/Packs 为 N 个独立图像任务；仅已验证 active 模型；整批预检积分。",
            },
            "voice_changer": {
                "available": True,
                "mode": "tts_narration",
                "path": ["/create/motion", "/create/audio"],
                "note": "Motion 可选 TTS 旁白 + Generate Audio。不是实时变声 / RVC / ElevenLabs Voice Changer。",
            },
            "max_slider": {
                "available": True,
                "path": "/pricing",
                "api": "/pricing/plans",
                "note": "Max credits 滑块写入 checkout.credits；未注入 Stripe Key 无法收款。",
            },
            "team_seats": {
                "available": True,
                "path": "/teams",
                "api": "/billing/credit-packs",
                "note": "席位 SKU seat_monthly / seat_pack_3；购买走 checkout kind=team_seats。",
            },
            "mcp_api": {
                "available": True,
                "path": "/mcp",
                "connector": "/api/v1/mcp/connector",
                "rest": ["/public/generate", "/public/quote", "/public/models", "/public/credits", "/public/tasks/{id}", "/public/assets"],
                "auth": "api_key",
                "oauth": False,
                "note": (
                    "对标 Yapper MCP/API 分发面：托管 JSON-RPC + REST。"
                    "鉴权是 sk_betty_ API Key，不是账号 OAuth。"
                    "货架以 active 数为准，不宣称 54+ / Seedance 2.5 / Sora / Veo。"
                ),
            },
            "director_minimal": {
                "available": True,
                "note": "PlanRequest.minimal / 快速成片：enhance→1图→1视，跳过配音字幕合成。",
            },
            "live_smoke": {
                "image_sample": "scripts/smoke_live_image_sample.py",
                "video_sample": "scripts/smoke_live_video_sample.py",
                "lipsync_weekly": "app.tasks.health_tasks.smoke_live_lipsync_weekly",
                "gates": [
                    "MODEL_SMOKE_LIVE",
                    "MODEL_SMOKE_LIVE_VIDEO",
                    "MODEL_SMOKE_LIVE_*_WEEKLY",
                    "LIPSYNC_FIXTURE_LIVE_WEEKLY",
                ],
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
        "lipsync_fixture": _public_lipsync_fixture(),
    }


def _public_lipsync_fixture() -> dict | None:
    from pathlib import Path
    import json

    path = Path(__file__).resolve().parents[2] / "fixtures" / "lipsync" / "last_run.json"
    if not path.is_file():
        return {"available": False, "note": "无折叠 last_run；设置 LIPSYNC_FIXTURE_LIVE_WEEKLY=1 启用周检"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "available": True,
            "ok": bool(data.get("ok")),
            "ts": data.get("ts") or data.get("completed_at"),
            "model": data.get("model"),
            "weekly_gate": "LIPSYNC_FIXTURE_LIVE_WEEKLY=1",
        }
    except Exception:
        return {"available": False}


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
