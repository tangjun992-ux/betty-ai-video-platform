"""System capabilities — demo vs real mode for honest UI disclosure."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/capabilities", summary="平台能力（demo / 真实生成）")
async def capabilities():
    from app.adapters.demo_provider import any_provider_configured, demo_mode_active
    from app.api.director import _dry_run_default

    configured = any_provider_configured()
    demo = demo_mode_active()
    return {
        "demo_mode": demo,
        "providers_configured": configured,
        "real_generation_available": configured and not _dry_run_default(),
        "director_dry_run_default": _dry_run_default(),
        "label": "真实生成可用" if (configured and not _dry_run_default()) else "预览模式（未配置模型 Key）",
    }
