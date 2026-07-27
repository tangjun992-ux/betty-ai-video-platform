"""
Available models info API — KIE.ai unified models.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter()


class ModelCapability(BaseModel):
    media_types: list[str]
    max_resolution: str
    max_duration_s: int
    avg_latency_s: int
    styles: list[str]
    cost_per_image_credits: int
    cost_per_5s_video_credits: int


class ModelInfo(BaseModel):
    id: str
    provider: str
    display_name: str
    description: str
    capabilities: ModelCapability
    cost_tier: str  # low | medium | high
    status: str     # active | beta | lab | maintenance | deprecated


MODELS = [
    # ─── Image models (15) via KIE.ai ───
    ModelInfo(
        id="gpt-image-2", provider="KIE.ai → OpenAI", display_name="GPT Image 2",
        description="4K 近乎完美的文字渲染，产品图/海报首选",
        capabilities=ModelCapability(media_types=["image"], max_resolution="4K", max_duration_s=0, avg_latency_s=15, styles=["photorealistic", "product", "poster", "portrait"], cost_per_image_credits=5, cost_per_5s_video_credits=0),
        cost_tier="high", status="active",
    ),
    ModelInfo(
        id="nano-banana", provider="KIE.ai → Google", display_name="Nano Banana 2",
        description="写实人物强、速度快、性价比高",
        capabilities=ModelCapability(media_types=["image"], max_resolution="2K", max_duration_s=0, avg_latency_s=8, styles=["realistic", "portrait", "landscape", "anime"], cost_per_image_credits=2, cost_per_5s_video_credits=0),
        cost_tier="low", status="active",
    ),
    ModelInfo(
        id="nano-banana-pro", provider="KIE.ai → Google", display_name="Nano Banana 2 Pro",
        description="Google 旗舰，超高保真与一致性 (已真实验证)",
        capabilities=ModelCapability(media_types=["image"], max_resolution="4K", max_duration_s=0, avg_latency_s=12, styles=["photorealistic", "cinematic", "portrait"], cost_per_image_credits=4, cost_per_5s_video_credits=0),
        cost_tier="high", status="active",
    ),
    ModelInfo(
        id="flux-1.1-pro", provider="KIE.ai → Black Forest", display_name="FLUX 1.1 Pro",
        description="顶级美学与构图，创意视觉标杆",
        capabilities=ModelCapability(media_types=["image"], max_resolution="4K", max_duration_s=0, avg_latency_s=10, styles=["artistic", "cinematic", "fantasy", "concept"], cost_per_image_credits=4, cost_per_5s_video_credits=0),
        cost_tier="high", status="lab",
    ),
    ModelInfo(
        id="flux-1-dev", provider="KIE.ai → Black Forest", display_name="FLUX.1 Dev",
        description="开源旗舰，可控性强",
        capabilities=ModelCapability(media_types=["image"], max_resolution="2K", max_duration_s=0, avg_latency_s=8, styles=["realistic", "artistic", "anime"], cost_per_image_credits=3, cost_per_5s_video_credits=0),
        cost_tier="medium", status="lab",
    ),
    ModelInfo(
        id="flux-kontext", provider="KIE.ai → Black Forest", display_name="FLUX Kontext",
        description="指令式图像编辑，局部精修",
        capabilities=ModelCapability(media_types=["image"], max_resolution="2K", max_duration_s=0, avg_latency_s=9, styles=["edit", "inpaint", "style-transfer"], cost_per_image_credits=3, cost_per_5s_video_credits=0),
        cost_tier="medium", status="lab",
    ),
    ModelInfo(
        id="imagen-4", provider="KIE.ai → Google", display_name="Imagen 4",
        description="Google 摄影级写实与光影（网关已映射验证）",
        capabilities=ModelCapability(media_types=["image"], max_resolution="4K", max_duration_s=0, avg_latency_s=11, styles=["photorealistic", "landscape", "food", "product"], cost_per_image_credits=4, cost_per_5s_video_credits=0),
        cost_tier="high", status="active",
    ),
    ModelInfo(
        id="ideogram-v3", provider="KIE.ai → Ideogram", display_name="Ideogram V3",
        description="最强文字排版与 Logo 设计",
        capabilities=ModelCapability(media_types=["image"], max_resolution="2K", max_duration_s=0, avg_latency_s=10, styles=["typography", "logo", "poster", "design"], cost_per_image_credits=3, cost_per_5s_video_credits=0),
        cost_tier="medium", status="lab",
    ),
    ModelInfo(
        id="recraft-v3", provider="KIE.ai → Recraft", display_name="Recraft V3",
        description="矢量/品牌设计与图标系统",
        capabilities=ModelCapability(media_types=["image"], max_resolution="2K", max_duration_s=0, avg_latency_s=9, styles=["vector", "icon", "brand", "illustration"], cost_per_image_credits=3, cost_per_5s_video_credits=0),
        cost_tier="medium", status="lab",
    ),
    ModelInfo(
        id="seedream-3", provider="KIE.ai → ByteDance", display_name="Seedream 3.0",
        description="中文语义理解强，国风/电商",
        capabilities=ModelCapability(media_types=["image"], max_resolution="2K", max_duration_s=0, avg_latency_s=8, styles=["chinese", "ecommerce", "portrait", "anime"], cost_per_image_credits=2, cost_per_5s_video_credits=0),
        cost_tier="low", status="lab",
    ),
    ModelInfo(
        id="qwen-image", provider="KIE.ai → Alibaba", display_name="Qwen-Image",
        description="中英文字渲染与复杂场景",
        capabilities=ModelCapability(media_types=["image"], max_resolution="2K", max_duration_s=0, avg_latency_s=9, styles=["chinese", "poster", "scene"], cost_per_image_credits=2, cost_per_5s_video_credits=0),
        cost_tier="low", status="lab",
    ),
    ModelInfo(
        id="hidream-i1", provider="KIE.ai → HiDream", display_name="HiDream I1",
        description="高细节写实与质感",
        capabilities=ModelCapability(media_types=["image"], max_resolution="2K", max_duration_s=0, avg_latency_s=10, styles=["realistic", "detail", "portrait"], cost_per_image_credits=3, cost_per_5s_video_credits=0),
        cost_tier="medium", status="lab",
    ),
    ModelInfo(
        id="sdxl", provider="KIE.ai → Stability", display_name="Stable Diffusion XL",
        description="经典开源，生态丰富",
        capabilities=ModelCapability(media_types=["image"], max_resolution="1080p", max_duration_s=0, avg_latency_s=6, styles=["realistic", "anime", "artistic"], cost_per_image_credits=1, cost_per_5s_video_credits=0),
        cost_tier="low", status="lab",
    ),
    ModelInfo(
        id="midjourney-v7", provider="KIE.ai → Midjourney", display_name="Midjourney V7",
        description="艺术美学天花板",
        capabilities=ModelCapability(media_types=["image"], max_resolution="2K", max_duration_s=0, avg_latency_s=30, styles=["artistic", "cinematic", "fantasy"], cost_per_image_credits=5, cost_per_5s_video_credits=0),
        cost_tier="high", status="lab",
    ),
    ModelInfo(
        id="grok-image", provider="KIE.ai → xAI", display_name="Grok Image",
        description="实时风格与梗图生成",
        capabilities=ModelCapability(media_types=["image"], max_resolution="2K", max_duration_s=0, avg_latency_s=10, styles=["meme", "realistic", "creative"], cost_per_image_credits=3, cost_per_5s_video_credits=0),
        cost_tier="medium", status="lab",
    ),

    # ─── Video models (22) via KIE.ai ───
    ModelInfo(
        id="seedance-2.0", provider="KIE.ai → ByteDance", display_name="Seedance 2.0",
        description="电影级画质，多镜头/唇形同步",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=15, avg_latency_s=90, styles=["cinematic", "realistic", "dynamic"], cost_per_image_credits=0, cost_per_5s_video_credits=4),
        cost_tier="medium", status="active",
    ),
    ModelInfo(
        id="seedance-2.0-fast", provider="KIE.ai → ByteDance", display_name="Seedance 2.0 Fast",
        description="图生视频流畅，社媒短视频",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=10, avg_latency_s=30, styles=["realistic", "anime", "sci-fi"], cost_per_image_credits=0, cost_per_5s_video_credits=3),
        cost_tier="low", status="active",
    ),
    ModelInfo(
        id="veo-3.1", provider="KIE.ai → Google", display_name="Veo 3.1",
        description="Google 旗舰，原生带声/物理真实",
        capabilities=ModelCapability(media_types=["video"], max_resolution="4K", max_duration_s=60, avg_latency_s=150, styles=["cinematic", "realistic", "nature"], cost_per_image_credits=0, cost_per_5s_video_credits=12),
        cost_tier="high", status="beta",
    ),
    ModelInfo(
        id="veo-3.1-fast", provider="KIE.ai → Google", display_name="Veo 3.1 Fast",
        description="Veo 快速档，质价比优",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=30, avg_latency_s=70, styles=["cinematic", "realistic"], cost_per_image_credits=0, cost_per_5s_video_credits=8),
        cost_tier="high", status="beta",
    ),
    ModelInfo(
        id="veo-3", provider="KIE.ai → Google", display_name="Veo 3",
        description="上一代旗舰，稳定可靠",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=30, avg_latency_s=80, styles=["cinematic", "realistic"], cost_per_image_credits=0, cost_per_5s_video_credits=7),
        cost_tier="high", status="beta",
    ),
    ModelInfo(
        id="sora-2", provider="KIE.ai → OpenAI", display_name="Sora 2",
        description="物理一致性与长镜头叙事",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=60, avg_latency_s=160, styles=["cinematic", "narrative", "realistic"], cost_per_image_credits=0, cost_per_5s_video_credits=12),
        cost_tier="high", status="lab",
    ),
    ModelInfo(
        id="sora-2-pro", provider="KIE.ai → OpenAI", display_name="Sora 2 Pro",
        description="Sora 专业档，最高保真",
        capabilities=ModelCapability(media_types=["video"], max_resolution="4K", max_duration_s=60, avg_latency_s=200, styles=["cinematic", "narrative"], cost_per_image_credits=0, cost_per_5s_video_credits=16),
        cost_tier="high", status="lab",
    ),
    ModelInfo(
        id="kling-2.5-turbo", provider="KIE.ai → Kuaishou", display_name="Kling 2.5 Turbo",
        description="快手旗舰，运动连贯/性价比高（网关 ID 已识别）",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=10, avg_latency_s=60, styles=["cinematic", "dynamic", "realistic"], cost_per_image_credits=0, cost_per_5s_video_credits=7),
        cost_tier="medium", status="active",
    ),
    ModelInfo(
        id="kling-2.1-master", provider="KIE.ai → Kuaishou", display_name="Kling 2.1 Master",
        description="大师版，复杂运镜（网关 ID 已识别）",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=10, avg_latency_s=90, styles=["cinematic", "dynamic"], cost_per_image_credits=0, cost_per_5s_video_credits=9),
        cost_tier="high", status="active",
    ),
    ModelInfo(
        id="kling-2.1-pro", provider="KIE.ai → Kuaishou", display_name="Kling 2.1 Pro",
        description="专业图生视频（网关 ID 已识别）",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=10, avg_latency_s=70, styles=["realistic", "product"], cost_per_image_credits=0, cost_per_5s_video_credits=7),
        cost_tier="medium", status="active",
    ),
    ModelInfo(
        id="kling-1.6", provider="KIE.ai → Kuaishou", display_name="Kling 1.6",
        description="经典稳定档",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=10, avg_latency_s=60, styles=["realistic", "dynamic"], cost_per_image_credits=0, cost_per_5s_video_credits=5),
        cost_tier="medium", status="beta",
    ),
    ModelInfo(
        id="wan-2.5", provider="KIE.ai → Alibaba", display_name="WAN 2.5",
        description="阿里旗舰，开源生态强",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=10, avg_latency_s=70, styles=["realistic", "anime", "dynamic"], cost_per_image_credits=0, cost_per_5s_video_credits=6),
        cost_tier="medium", status="beta",
    ),
    ModelInfo(
        id="wan-2.2", provider="KIE.ai → Alibaba", display_name="WAN 2.2",
        description="高质开源视频",
        capabilities=ModelCapability(media_types=["video"], max_resolution="720p", max_duration_s=8, avg_latency_s=55, styles=["realistic", "anime"], cost_per_image_credits=0, cost_per_5s_video_credits=4),
        cost_tier="low", status="beta",
    ),
    ModelInfo(
        id="hailuo-2.3", provider="KIE.ai → MiniMax", display_name="Hailuo 2.3",
        description="海螺，运动幅度大/表演力强",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=10, avg_latency_s=75, styles=["dynamic", "cinematic", "character"], cost_per_image_credits=0, cost_per_5s_video_credits=7),
        cost_tier="medium", status="beta",
    ),
    ModelInfo(
        id="hailuo-02", provider="KIE.ai → MiniMax", display_name="Hailuo 02",
        description="海螺经典，稳定流畅",
        capabilities=ModelCapability(media_types=["video"], max_resolution="720p", max_duration_s=6, avg_latency_s=50, styles=["realistic", "dynamic"], cost_per_image_credits=0, cost_per_5s_video_credits=5),
        cost_tier="low", status="beta",
    ),
    ModelInfo(
        id="grok-video", provider="KIE.ai → xAI", display_name="Grok Video",
        description="实时创意短视频",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=10, avg_latency_s=60, styles=["creative", "meme", "dynamic"], cost_per_image_credits=0, cost_per_5s_video_credits=6),
        cost_tier="medium", status="lab",
    ),
    ModelInfo(
        id="runway-gen4", provider="KIE.ai → Runway", display_name="Runway Gen-4",
        description="好莱坞级一致性与控制",
        capabilities=ModelCapability(media_types=["video"], max_resolution="4K", max_duration_s=10, avg_latency_s=90, styles=["cinematic", "vfx", "narrative"], cost_per_image_credits=0, cost_per_5s_video_credits=10),
        cost_tier="high", status="lab",
    ),
    ModelInfo(
        id="runway-gen3", provider="KIE.ai → Runway", display_name="Runway Gen-3 Alpha",
        description="成熟创作工作流",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=10, avg_latency_s=70, styles=["cinematic", "vfx"], cost_per_image_credits=0, cost_per_5s_video_credits=8),
        cost_tier="high", status="lab",
    ),
    ModelInfo(
        id="luma-ray-2", provider="KIE.ai → Luma", display_name="Luma Ray 2",
        description="自然运动与物理",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=10, avg_latency_s=80, styles=["realistic", "nature", "dynamic"], cost_per_image_credits=0, cost_per_5s_video_credits=8),
        cost_tier="high", status="lab",
    ),
    ModelInfo(
        id="pika-2.2", provider="KIE.ai → Pika", display_name="Pika 2.2",
        description="创意特效与转场",
        capabilities=ModelCapability(media_types=["video"], max_resolution="1080p", max_duration_s=10, avg_latency_s=55, styles=["creative", "vfx", "anime"], cost_per_image_credits=0, cost_per_5s_video_credits=6),
        cost_tier="medium", status="lab",
    ),
    ModelInfo(
        id="hunyuan-video", provider="KIE.ai → Tencent", display_name="Hunyuan Video",
        description="腾讯开源，中文场景强",
        capabilities=ModelCapability(media_types=["video"], max_resolution="720p", max_duration_s=8, avg_latency_s=65, styles=["chinese", "realistic", "cinematic"], cost_per_image_credits=0, cost_per_5s_video_credits=5),
        cost_tier="medium", status="lab",
    ),
    ModelInfo(
        id="ltx-video", provider="KIE.ai → Lightricks", display_name="LTX Video",
        description="极速生成，本地友好",
        capabilities=ModelCapability(media_types=["video"], max_resolution="720p", max_duration_s=10, avg_latency_s=25, styles=["realistic", "fast", "dynamic"], cost_per_image_credits=0, cost_per_5s_video_credits=3),
        cost_tier="low", status="lab",
    ),
]


# ─── Model governance: single source of truth for what is production-ready ───
# "active" == verified working on the live gateway. Everything else is a lab
# model that must never be surfaced by default nor silently used in production.

def verified_model_ids() -> set[str]:
    from app.services.model_health import model_health
    return {
        m.id for m in MODELS
        if m.status == "active" and model_health.is_routable(m.id)
    }


def is_verified(model_id: str) -> bool:
    from app.services.model_health import model_health
    return any(m.id == model_id and m.status == "active" for m in MODELS) and model_health.is_routable(model_id)


def default_verified_model(media_type: str) -> str | None:
    """Cheapest-first verified model for a media type (safe production fallback)."""
    order = {"low": 0, "medium": 1, "high": 2}
    candidates = [
        m for m in MODELS
        if m.status == "active" and media_type in m.capabilities.media_types
    ]
    candidates.sort(key=lambda m: order.get(m.cost_tier, 9))
    return candidates[0].id if candidates else None


def _serialize(m: ModelInfo) -> dict:
    d = m.model_dump()
    # Explicit, non-derivable-by-clients trust signal.
    d["verified"] = m.status == "active"
    return d


@router.get("/", summary="获取可用模型列表")
async def list_models(
    status: str | None = None,
    include_beta: bool = False,
    include_lab: bool = False,
):
    """List models with production-safe defaults.

    - `status=active` → verified/production-ready only
    - `status=beta` → mapped-but-unverified labs
    - `status=lab` → gateway guess SKUs (likely 422) — opt-in only
    - default: verified only; `include_beta` may add beta (never in production primary);
      `include_lab` required to surface guess SKUs at all.
    """
    from app.services.model_health import model_health

    active = [
        _serialize(m) for m in MODELS
        if m.status == "active" and model_health.is_routable(m.id)
    ]
    quarantined_ids = [
        m.id for m in MODELS
        if m.status == "active" and not model_health.is_routable(m.id)
    ]
    beta = [_serialize(m) for m in MODELS if m.status == "beta"]
    lab = [_serialize(m) for m in MODELS if m.status == "lab"]
    # Legacy: treat unknown non-active as beta for back-compat counts
    other = [_serialize(m) for m in MODELS if m.status not in ("active", "beta", "lab")]

    if status == "active":
        return {"models": active, "active": active, "beta": [], "lab": [],
                "active_count": len(active), "beta_count": 0, "lab_count": 0}
    if status == "beta":
        return {"models": beta, "active": [], "beta": beta, "lab": [],
                "active_count": 0, "beta_count": len(beta), "lab_count": 0}
    if status == "lab":
        return {"models": lab, "active": [], "beta": [], "lab": lab,
                "active_count": 0, "beta_count": 0, "lab_count": len(lab)}

    from app.config import settings
    primary = list(active)
    if include_beta and not settings.is_production:
        primary.extend(beta)
        primary.extend(other)
    if include_lab and not settings.is_production:
        primary.extend(lab)
    return {
        "models": primary,
        "active": active,
        "beta": beta + other,
        "lab": lab,
        "quarantined": quarantined_ids,
        "active_count": len(active),
        "beta_count": len(beta) + len(other),
        "lab_count": len(lab),
    }


@router.get("/health", summary="模型健康 registry 快照")
@router.get("/health/live", summary="模型实时健康与熔断状态")
async def live_model_health():
    """Runtime feedback used by automatic routing (success, latency, circuit)."""
    from app.services.model_health import model_health
    rows = [model_health.snapshot(m.id).public_dict() for m in MODELS]
    rows.sort(key=lambda r: (r["circuit_open"], -r["score"], r["model_id"]))
    return {
        "models": rows,
        "circuits_open": sum(1 for r in rows if r["circuit_open"]),
        "count": len(rows),
        "last_smoke": _models_last_smoke(),
    }


def _models_last_smoke() -> dict | None:
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
    }


@router.get("/{model_id}", summary="获取指定模型详情")
async def get_model(model_id: str):
    for m in MODELS:
        if m.id == model_id:
            return m
    raise HTTPException(status_code=404, detail=f"Model {model_id} not found")


# ─── Pricing & Credits (inline to avoid cache issues) ───

from pydantic import BaseModel as PydanticBase
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.auth import resolve_user_id
from app.models.billing import UserBalance, Transaction, TransactionType

PLANS_DATA = [
    {"id":"starter","name":"入门版","monthly_price":9.99,"yearly_price":7.99,"credits":1000,
     "features":[{"name":"Seedance 2.0 全模态视频","included":False},{"name":"已验证图片模型","included":True},{"name":"已验证视频模型","included":False},{"name":"高级唇形同步","included":True},{"name":"高级图片编辑器","included":True},{"name":"视频 & 图片放大","included":True},{"name":"运动迁移（best-effort）","included":False},{"name":"商用授权许可","included":False},{"name":"团队协作","included":False},{"name":"优先支持","included":False}]},
    {"id":"personal","name":"个人版","monthly_price":24.99,"yearly_price":19.99,"credits":3000,
     "features":[{"name":"Seedance 2.0 全模态视频","included":True},{"name":"已验证图片模型","included":True},{"name":"已验证视频模型","included":True},{"name":"高级唇形同步","included":True},{"name":"高级图片编辑器","included":True},{"name":"视频 & 图片放大","included":True},{"name":"运动迁移（best-effort）","included":True},{"name":"商用授权许可","included":False},{"name":"团队协作","included":False},{"name":"优先支持","included":False}]},
    {"id":"creator","name":"创作者版","monthly_price":49.99,"yearly_price":39.99,"credits":7000,"highlighted":True,"badge":"最受欢迎",
     "features":[{"name":"Seedance 2.0 全模态视频","included":True},{"name":"已验证图片模型","included":True},{"name":"已验证视频模型","included":True},{"name":"高级唇形同步","included":True},{"name":"高级图片编辑器","included":True},{"name":"视频 & 图片放大","included":True},{"name":"运动迁移（best-effort）","included":True},{"name":"商用授权许可","included":True},{"name":"团队协作","included":True},{"name":"优先支持","included":True}]},
    {"id":"pro","name":"专业版","monthly_price":99.99,"yearly_price":79.99,"credits":15000,
     "features":[{"name":"Seedance 2.0 全模态视频","included":True},{"name":"全部可用模型","included":True},{"name":"按用量计费","included":True},{"name":"高级唇形同步","included":True},{"name":"高级图片编辑器","included":True},{"name":"视频 & 图片放大","included":True},{"name":"运动迁移（best-effort）","included":True},{"name":"商用授权许可","included":True},{"name":"团队协作","included":True},{"name":"优先支持","included":True}]},
]

@router.get("/pricing/plans", summary="获取定价方案")
async def get_pricing_plans(cycle: str = "monthly"):
    key = "yearly_price" if cycle == "yearly" else "monthly_price"
    result = []
    for p in PLANS_DATA:
        result.append({
            "id": p["id"], "name": p["name"],
            "price": p[key], "credits_per_month": p["credits"],
            "cycle": cycle, "features": p["features"],
            "highlighted": p.get("highlighted", False),
            "badge": p.get("badge"),
        })
    return {"plans": result, "cycle": cycle}


@router.get("/pricing/user", summary="获取用户余额")
async def get_user_balance(user_id: int = Depends(resolve_user_id), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select as sa_select
    from app.models.user import User
    r = await db.execute(sa_select(UserBalance).where(UserBalance.user_id == user_id))
    balance = r.scalar_one_or_none()
    u = await db.execute(sa_select(User).where(User.id == user_id))
    user = u.scalar_one_or_none()
    if not balance:
        return {"user_id": user_id, "credits": 0, "total_spent": 0, "total_tasks": 0, "role": "free"}
    return {
        "user_id": user_id,
        "credits": balance.credits + balance.daily_credits,
        "purchased_credits": balance.credits,
        "daily_credits": balance.daily_credits,
        "daily_credits_max": balance.daily_credits_max,
        "total_spent": balance.total_spent,
        "total_tasks": balance.total_tasks,
        "total_purchased": balance.total_purchased,
        "role": user.role if user else "free",
    }


@router.post("/pricing/subscribe", summary="订阅方案")
async def subscribe(plan_id: str, user_id: int = Depends(resolve_user_id), db: AsyncSession = Depends(get_db)):
    from app.config import settings
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not found")
    from sqlalchemy import select as sa_select
    plan = next((p for p in PLANS_DATA if p["id"] == plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found")
    r = await db.execute(sa_select(UserBalance).where(UserBalance.user_id == user_id))
    balance = r.scalar_one_or_none()
    if not balance:
        balance = UserBalance(user_id=user_id, credits=0)
        db.add(balance)
    balance.credits += plan["credits"]
    balance.total_purchased += plan["credits"]
    await db.flush()
    return {"success": True, "plan": plan["name"], "credits_added": plan["credits"],
            "new_balance": balance.credits + balance.daily_credits}


@router.get("/pricing/costs", summary="KIE 费用统计")
async def get_kie_costs(days: int = 30):
    """KIE API cost tracking: total, by-model, by-type, daily breakdown."""
    import sqlite3, os, traceback
    from datetime import datetime, timedelta, timezone

    try:
        db_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
        db_path = db_url
        for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
            if db_path.startswith(prefix):
                db_path = db_path[len(prefix):]
                break
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", db_path)

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        cur.execute(
            "SELECT COUNT(*), COALESCE(SUM(estimated_cost),0), COALESCE(SUM(actual_cost),0) "
            "FROM tasks WHERE created_at >= ?", (cutoff,))
        total_tasks, total_est, total_act = cur.fetchone()

        cur.execute(
            "SELECT COALESCE(selected_model,'?'), COUNT(*), "
            "COALESCE(AVG(actual_cost),0), COALESCE(SUM(actual_cost),0) "
            "FROM tasks WHERE created_at >= ? AND status='completed' "
            "GROUP BY selected_model ORDER BY SUM(actual_cost) DESC", (cutoff,))
        by_model = [{"model": r[0], "count": r[1], "avg_cost": round(r[2], 2),
                      "total_cost": round(r[3], 2)} for r in cur.fetchall()]

        cur.execute(
            "SELECT COALESCE(media_type,'?'), COUNT(*), COALESCE(SUM(actual_cost),0) "
            "FROM tasks WHERE created_at >= ? AND status='completed' "
            "GROUP BY media_type", (cutoff,))
        by_type = [{"type": r[0], "count": r[1], "total_cost": round(r[2], 2)}
                   for r in cur.fetchall()]

        cur.execute(
            "SELECT DATE(created_at), COUNT(*), COALESCE(SUM(actual_cost),0), "
            "SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) "
            "FROM tasks WHERE created_at >= ? "
            "GROUP BY DATE(created_at) ORDER BY DATE(created_at) DESC", (cutoff,))
        daily = [{"day": r[0], "count": r[1], "total_cost": round(r[2], 2),
                  "succeeded": r[3], "failed": r[4]} for r in cur.fetchall()]

        cur.execute(
            "SELECT task_id, media_type, selected_model, estimated_cost, actual_cost, "
            "status, created_at FROM tasks WHERE created_at >= ? "
            "ORDER BY created_at DESC LIMIT 50", (cutoff,))
        recent = [{"task_id": r[0], "type": r[1], "model": r[2],
                   "estimated_cost": r[3], "actual_cost": r[4],
                   "status": r[5], "created_at": r[6]} for r in cur.fetchall()]

        conn.close()
        return {
            "period_days": days,
            "summary": {"total_tasks": total_tasks,
                         "total_estimated_cost": round(total_est, 2),
                         "total_actual_cost": round(total_act, 2)},
            "by_model": by_model, "by_type": by_type,
            "daily": daily, "recent": recent,
        }
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}
