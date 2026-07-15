""""
Generation API — submit generation requests with smart routing.
"""
import uuid
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.models.task import Task
from app.services.credits import deduct_credits, resolve_team_id
from app.tasks.image_tasks import generate_image_task
from app.tasks.video_tasks import generate_video_task
from app.tasks.pipeline_tasks import run_pipeline
from app.router import router as prompt_router
from app.prompt_enhancer import enhancer as prompt_enhancer
from app.rate_limiter import rate_limit
from app.auth import resolve_user_id

router = APIRouter()
logger = logging.getLogger(__name__)


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000, description="描述你想要的画面的提示词")
    media_type: str = Field(default="auto", description="生成类型: image | video | auto")
    model: str = Field(default="auto", description="指定模型或 'auto' 自动选择")
    quality: str = Field(default="balanced", description="质量偏好: fast | balanced | high")
    resolution: str = Field(default="1080x1080", description="输出分辨率")
    duration: Optional[int] = Field(default=5, ge=1, le=60, description="视频时长(秒)")
    count: int = Field(default=1, ge=1, le=4, description="生成数量")
    style: Optional[str] = Field(default=None, description="风格偏好")
    template: Optional[str] = Field(default=None, description="可选模板名称")
    webhook_url: Optional[str] = Field(default=None, description="回调地址")
    enhance_prompt: Optional[bool] = Field(default=True, description="是否自动增强提示词")
    image_url: Optional[str] = Field(default=None, description="参考图片URL（用于图转视频）")
    seed: Optional[int] = Field(default=None, ge=0, le=2147483647, description="随机种子（复现同一结果；留空则随机）")


class GenerateResponse(BaseModel):
    task_id: str
    status: str
    estimated_model: str
    fallback_model: Optional[str] = None
    enhanced_prompt: Optional[str] = None
    estimated_time_seconds: int
    estimated_cost_credits: int
    poll_url: str
    routing_info: Optional[dict] = None
    model_scores: Optional[list[dict]] = None


class RouterAnalysisResponse(BaseModel):
    """Endpoint to analyze a prompt without submitting a task."""
    analysis: dict
    recommended_model: dict
    all_scores: list[dict]


@router.post(
    "/",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="提交生成请求",
    description="根据提示词智能选择模型并生成图像或视频",
    dependencies=[Depends(rate_limit("generate", rpm=10, rph=100))],
)
async def submit_generation(
    req: GenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    task_id = str(uuid.uuid4())
    team_id = resolve_team_id(request)
    # Deterministic seed: reuse the caller's (reproduce) or roll a fresh one so
    # every generation is reproducible and variations can be requested later.
    import random as _random
    seed = req.seed if req.seed is not None else _random.randint(1, 2_147_483_647)

    # Stage 1: Smart prompt analysis
    analysis = prompt_router.analyze(
        prompt=req.prompt,
        media_type_hint=req.media_type,
        quality_hint=req.quality,
    )

    # Stage 1b: Prompt enhancement (optional)
    enhanced_prompt = req.prompt
    if req.enhance_prompt:
        enhancement = prompt_enhancer.enhance(
            prompt=req.prompt,
            media_type=analysis.media_type.value,
            style=req.style or "auto",
            quality=req.quality,
        )
        enhanced_prompt = enhancement.enhanced

    # Stage 1c: Content safety pre-check (fast keyword filter)
    from app.services.moderation import check_prompt, moderation_reject
    mod = check_prompt(f"{req.prompt}\n{enhanced_prompt}")
    if not mod.allowed:
        raise moderation_reject(mod)

    # Stage 2: Smart model selection via router
    model_selection = prompt_router.select_model(
        analysis=analysis,
        user_model=req.model,
    )
    estimated_model = model_selection.model_id
    fallback_model = getattr(model_selection, "is_fallback_model", None)

    # Get all model scores for UI display
    all_scores = prompt_router.get_all_model_scores(analysis)

    # Determine effective media type
    effective_media = analysis.media_type.value
    if effective_media == "auto":
        effective_media = "image" if "video" not in estimated_model else "video"

    estimated_time, estimated_cost = _estimate_time_and_cost(
        effective_media, estimated_model, req.duration or 5
    )

    # Build routing info for response
    routing_info = {
        "detected_media_type": analysis.media_type.value,
        "detected_quality": analysis.quality.value,
        "detected_styles": analysis.styles,
        "complexity": analysis.complexity,
        "mood": analysis.mood,
        "model_selection_score": model_selection.score,
        "selection_reasons": model_selection.reasons,
        "prompt_was_enhanced": enhanced_prompt != req.prompt,
    }

    # Create Task record
    task = Task(
        task_id=task_id,
        user_id=user_id,
        prompt=enhanced_prompt,  # use enhanced prompt
        media_type=effective_media,
        quality=req.quality,
        requested_model=req.model,
        selected_model=estimated_model,
        fallback_model=fallback_model,
        parameters={
            "resolution": req.resolution,
            "duration": req.duration,
            "count": req.count,
            "style": req.style,
            "seed": seed,
            "original_prompt": req.prompt if enhanced_prompt != req.prompt else None,
            "routing_info": json.dumps(routing_info),
        },
        estimated_cost=estimated_cost,
        status="queued",
        webhook_url=req.webhook_url,
    )
    db.add(task)
    await db.flush()

    # Check and deduct credits (personal or team pool via X-Team-Id)
    credits_ok = await deduct_credits(
        db=db, user_id=user_id, cost=estimated_cost,
        task_id=task_id, model=estimated_model, team_id=team_id,
    )
    if not credits_ok:
        task.status = "failed"
        task.error_message = "积分不足，请充值后重试"
        await db.flush()
        return GenerateResponse(
            task_id=task_id,
            status="failed",
            estimated_model=estimated_model,
            estimated_time_seconds=0,
            estimated_cost_credits=estimated_cost,
            poll_url=f"/api/v1/tasks/{task_id}",
            routing_info=routing_info,
        )
    task.status = "queued"

    # Prepare Celery task params
    celery_params = {
        "resolution": req.resolution,
        "duration": req.duration or 5,
        "count": req.count,
        "style": req.style,
        "seed": seed,
    }
    if req.image_url:
        celery_params["image_url"] = req.image_url

    # Dispatch appropriate Celery task
    if req.template:
        celery_task = run_pipeline.delay(db_task_id=task_id, pipeline_config=[])
    elif effective_media == "image" or req.media_type == "image":
        celery_task = generate_image_task.delay(
            db_task_id=task_id, model=estimated_model,
            prompt=enhanced_prompt, params=celery_params,
        )
    else:
        celery_task = generate_video_task.delay(
            db_task_id=task_id, model=estimated_model,
            prompt=enhanced_prompt, params=celery_params,
        )

    task.celery_task_id = celery_task.id
    task.status = "queued"
    task.estimated_completion = datetime.now(timezone.utc) + timedelta(seconds=estimated_time)
    await db.flush()

    return GenerateResponse(
        task_id=task_id,
        status="queued",
        estimated_model=estimated_model,
        fallback_model=fallback_model,
        enhanced_prompt=enhanced_prompt if enhanced_prompt != req.prompt else None,
        estimated_time_seconds=estimated_time,
        estimated_cost_credits=estimated_cost,
        poll_url=f"/api/v1/tasks/{task_id}",
        routing_info=routing_info,
        model_scores=[{"model": s.model_id, "score": s.score, "reasons": s.reasons}
                      for s in all_scores],
    )


class SpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="要配音的文本/脚本")
    voice: str = Field(default="Rachel", description="音色")


@router.post("/speech", summary="AI 配音 (TTS)",
             dependencies=[Depends(rate_limit("speech", rpm=20, rph=150))])
async def generate_speech(req: SpeechRequest):
    """Text-to-speech voiceover (对标 yapper Generate Audio). Real ElevenLabs via
    KIE when a key is configured; a short local tone otherwise."""
    from app.services.moderation import check_prompt, moderation_reject
    mod = check_prompt(req.text)
    if not mod.allowed:
        raise moderation_reject(mod)
    from app.adapters.demo_provider import demo_mode_active
    if demo_mode_active():
        from app.adapters.demo_provider import render_demo_speech
        import asyncio as _a
        url = await _a.to_thread(render_demo_speech, req.text)
        return {"url": url, "media_type": "audio", "model": "demo-tts", "demo": True}
    from app.adapters.kie_adapter import KieAdapter
    from app.services.media_store import persist_results
    res = await KieAdapter().generate_speech(req.text, voice=req.voice)
    out = {"type": "audio", "url": res.media_url, "media_url": res.media_url, "model": res.model}
    import asyncio as _a
    out = (await _a.to_thread(persist_results, [out]))[0]
    return {"url": out.get("url"), "source_url": out.get("source_url", res.media_url),
            "media_type": "audio", "model": res.model, "cost": res.cost, "demo": False}


@router.post("/edit", summary="AI 图像工具 (编辑/超分/抠图/扩图)",
             dependencies=[Depends(rate_limit("edit", rpm=15, rph=120))])
async def edit_image_tool(
    operation: str = Form(..., description="edit | upscale | bg-remove | extend"),
    image_file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    factor: str = Form("2"),
    ratio: str = Form("16:9"),
):
    """Unified image-tool endpoint (对标 yapper 编辑/放大/去背景/扩图).
    Uploads the source to a public URL then runs the real KIE model."""
    import asyncio as _a
    op = (operation or "").strip().lower()
    if op not in ("edit", "upscale", "bg-remove", "extend"):
        raise HTTPException(status_code=400, detail=f"未知操作: {operation}")
    if prompt:
        from app.services.moderation import check_prompt
        _m = check_prompt(prompt)
        if not _m.allowed:
            raise HTTPException(status_code=400, detail=_m.reason)
    if not image_file and not image_url:
        raise HTTPException(status_code=400, detail="请提供图片 (image_file 或 image_url)")
    if op in ("edit",) and not (prompt and prompt.strip()):
        raise HTTPException(status_code=400, detail="编辑操作需要 prompt 指令")

    # Resolve source bytes
    from app.adapters.demo_provider import demo_mode_active, _local_media_path
    if image_file:
        data = await image_file.read()
        ctype = image_file.content_type or "image/png"
    else:
        p = _local_media_path(image_url)
        if p:
            with open(p, "rb") as f:
                data = f.read()
            ctype = "image/png"
        else:
            import httpx
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.get(image_url)
                r.raise_for_status()
                data = r.content
                ctype = r.headers.get("content-type", "image/png")

    if demo_mode_active():
        from app.adapters.demo_provider import run_demo_image_tool
        url = await _a.to_thread(run_demo_image_tool, op, data, factor, ratio)
        return {"url": url, "media_type": "image", "model": f"demo-{op}", "demo": True}

    from app.adapters.kie_adapter import KieAdapter
    from app.services.media_store import persist_results
    adapter = KieAdapter()
    pub = await adapter.upload_public_url(data, filename="src.png", content_type=ctype)

    async def _run():
        if op == "upscale":
            return await adapter.upscale_image(image_url=pub, factor=factor)
        if op == "bg-remove":
            return await adapter.remove_background(image_url=pub)
        if op == "extend":
            return await adapter.extend_image(image_url=pub, target_ratio=ratio, prompt=prompt or "")
        return await adapter.edit_image(image_urls=[pub], prompt=prompt,
                                        image_size=ratio if ratio else "auto")

    # KIE image tools are intermittently flaky ("internal error") — retry.
    res = None
    last_err = None
    for attempt in range(3):
        try:
            res = await _run()
            break
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            logger.warning("[edit] %s attempt %d failed: %s", op, attempt + 1, e)
            if "internal error" in msg or "try again" in msg:
                await _a.sleep(4)
                continue
            raise HTTPException(status_code=502, detail=f"{op} 处理失败: {e}")
    if res is None:
        raise HTTPException(status_code=502, detail=f"{op} 处理失败: {last_err}")
    out = {"type": "image", "url": res.media_url, "media_url": res.media_url, "model": res.model}
    out = (await _a.to_thread(persist_results, [out]))[0]
    return {"url": out.get("url"), "source_url": out.get("source_url", res.media_url),
            "media_type": "image", "model": res.model, "operation": op, "cost": res.cost}


class EnhanceRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000)
    media_type: str = Field(default="auto")
    style: Optional[str] = Field(default=None)


class EnhanceResponse(BaseModel):
    original: str
    enhanced: str
    additions: list[str] = []
    changed: bool = False


@router.post("/enhance", response_model=EnhanceResponse, summary="AI 优化提示词")
async def enhance_prompt_endpoint(req: EnhanceRequest):
    """Expand a casual prompt into a richer, professional one (for 'Ask AI to improve')."""
    from app.services.moderation import check_prompt, moderation_reject
    mod = check_prompt(req.prompt)
    if not mod.allowed:
        raise moderation_reject(mod)
    result = prompt_enhancer.enhance(
        prompt=req.prompt,
        media_type=req.media_type or "auto",
        style=req.style or "auto",
        quality="high",  # always enhance regardless of speed preference
    )
    return EnhanceResponse(
        original=result.original,
        enhanced=result.enhanced,
        additions=getattr(result, "additions", []) or [],
        changed=result.enhanced.strip() != result.original.strip(),
    )


@router.post("/analyze", response_model=RouterAnalysisResponse, summary="分析提示词的模型推荐")
async def analyze_prompt(req: GenerateRequest):
    """Analyze a prompt without submitting a task — returns model recommendations."""
    analysis = prompt_router.analyze(req.prompt, req.media_type, req.quality)
    selection = prompt_router.select_model(analysis, req.model)
    all_scores = prompt_router.get_all_model_scores(analysis)

    return RouterAnalysisResponse(
        analysis={
            "media_type": analysis.media_type.value,
            "quality": analysis.quality.value,
            "styles": analysis.styles,
            "complexity": analysis.complexity,
            "mood": analysis.mood,
            "key_subjects": analysis.key_subjects,
            "language": analysis.language,
        },
        recommended_model={
            "model_id": selection.model_id,
            "score": selection.score,
            "reasons": selection.reasons,
        },
        all_scores=[{"model": s.model_id, "score": s.score, "reasons": s.reasons} for s in all_scores],
    )


def _check_content_safety(prompt: str) -> str | None:
    """Fast keyword-based content safety check. Returns error message or None."""
    prompt_lower = prompt.lower()
    blocked = [
        "nude", "naked", "nsfw", "porn", "xxx", "sex",
        "erotic", "explicit", "hentai", "doujin",
    ]
    for word in blocked:
        if word in prompt_lower:
            return "内容不合规：提示词包含敏感词汇，请修改后重试。"
    return None


def _estimate_time_and_cost(media_type: str, model: str, duration: int) -> tuple[int, int]:
    CREDIT_MAP = {
        # Image models
        "gpt-image-2": 5,
        "seedream-v4": 3,
        "flux-pro": 4,
        "nano-banana": 2,
        # Video models
        "kling-v2.5-pro": 6,
        "kling-v2.1-standard": 4,
        "seedance-2.0-fast": 3,
        "seedance-2.0": 4,
        "wan-2.6": 3,
        "veo-3": 8,
        # Legacy mappings
        "openai/gpt-5.4-image": 5,
        "openai/dall-e-3": 5,
        "bytedance/seedart": 3,
        "bytedance/seedance-2-fast": 3,
        "kling/video-v3-pro": 6,
        "kling/video-v2": 4,
    }
    TIME_MAP = {
        # Image models
        "gpt-image-2": 15,
        "seedream-v4": 10,
        "flux-pro": 12,
        "nano-banana": 8,
        # Video models
        "kling-v2.5-pro": 120,
        "kling-v2.1-standard": 90,
        "seedance-2.0-fast": 30,
        "seedance-2.0": 60,
        "wan-2.6": 60,
        "veo-3": 180,
        # Legacy mappings
        "openai/gpt-5.4-image": 15,
        "openai/dall-e-3": 15,
        "bytedance/seedart": 10,
        "bytedance/seedance-2-fast": 30,
        "kling/video-v3-pro": 120,
        "kling/video-v2": 60,
    }

    credits = CREDIT_MAP.get(model, 5)
    base_time = TIME_MAP.get(model, 30)

    if media_type == "video":
        multiplier = max(1, duration // 5)
        return base_time * multiplier, credits * multiplier
    return base_time, credits
