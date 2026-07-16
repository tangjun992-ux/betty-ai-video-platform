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
from app.services.credits import deduct_credits, refund_task_credits, resolve_team_id
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
    image_url: Optional[str] = Field(default=None, description="首张参考图 URL（兼容字段；等同 reference_images[0]）")
    reference_images: Optional[list[str]] = Field(
        default=None,
        description="多参考图 URL 列表（最多 9 张；图片 i2i≤4，Seedance Omni≤9）",
        max_length=9,
    )
    reference_videos: Optional[list[str]] = Field(
        default=None,
        description="Omni 参考视频 URL（最多 3；Seedance multimodal）",
        max_length=3,
    )
    reference_audios: Optional[list[str]] = Field(
        default=None,
        description="Omni 参考音频 URL（最多 3；Seedance multimodal / 唇形引导）",
        max_length=3,
    )
    omni: Optional[bool] = Field(
        default=None,
        description="强制 Seedance Omni 多模态参考模式（多图/视频/音频）",
    )
    generate_audio: Optional[bool] = Field(
        default=False,
        description="Seedance Omni 是否同时生成音轨",
    )
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


async def execute_generation(
    req: GenerateRequest,
    db: AsyncSession,
    user_id: int,
    team_id: Optional[int] = None,
) -> GenerateResponse:
    """Core generation pipeline shared by web `/generate/` and public Developer API.

    Does not depend on FastAPI `Request` / Depends injection so API-key callers
    can invoke it directly without a synthetic Starlette request.
    """
    task_id = str(uuid.uuid4())
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

    # Normalize multi-ref: reference_images wins; image_url kept as first for compat.
    ref_images: list[str] = []
    if req.reference_images:
        ref_images = [u.strip() for u in req.reference_images if u and str(u).strip()][:9]
    elif req.image_url and str(req.image_url).strip():
        ref_images = [str(req.image_url).strip()]
    # Image i2i stays ≤4; video Omni may use up to 9 (enforced in adapter).
    if effective_media == "image" or req.media_type == "image":
        ref_images = ref_images[:4]
    primary_image = ref_images[0] if ref_images else None
    ref_videos = [u.strip() for u in (req.reference_videos or []) if u and str(u).strip()][:3]
    ref_audios = [u.strip() for u in (req.reference_audios or []) if u and str(u).strip()][:3]
    omni = bool(req.omni) or bool(ref_videos or ref_audios or (len(ref_images) > 1 and effective_media == "video"))

    # Omni prefers Seedance when user left model=auto
    if omni and (req.model or "auto") in ("auto", "", None) and effective_media == "video":
        estimated_model = "seedance-2.0"
        routing_info["omni_routed"] = True
        routing_info["omni_model"] = estimated_model

    params = {
        "resolution": req.resolution,
        "duration": req.duration,
        "count": req.count,
        "style": req.style,
        "seed": seed,
        "original_prompt": req.prompt if enhanced_prompt != req.prompt else None,
        "routing_info": json.dumps(routing_info),
        "omni": omni,
        "generate_audio": bool(req.generate_audio),
    }
    if primary_image:
        params["image_url"] = primary_image
    if ref_images:
        params["reference_images"] = ref_images
    if ref_videos:
        params["reference_videos"] = ref_videos
    if ref_audios:
        params["reference_audios"] = ref_audios

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
        parameters=params,
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
        "omni": omni,
        "generate_audio": bool(req.generate_audio),
    }
    if primary_image:
        celery_params["image_url"] = primary_image
    if ref_images:
        celery_params["reference_images"] = ref_images
    if ref_videos:
        celery_params["reference_videos"] = ref_videos
    if ref_audios:
        celery_params["reference_audios"] = ref_audios

    # Dispatch appropriate Celery task — refund if broker/dispatch fails after deduct.
    try:
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
    except Exception as e:
        logger.error("Generation dispatch failed task=%s: %s", task_id, e)
        task.status = "failed"
        task.error_message = f"任务调度失败: {e}"
        await refund_task_credits(db, task_id, reason="dispatch_failed")
        await db.flush()
        raise HTTPException(status_code=500, detail=f"任务调度失败: {e}")

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
    return await execute_generation(
        req, db, user_id, team_id=resolve_team_id(request),
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


# Credit costs for image tools (upstream KIE burn + margin).
_EDIT_TOOL_COSTS = {
    "edit": 3,
    "upscale": 2,
    "bg-remove": 2,
    "extend": 3,
}


@router.post("/edit", summary="AI 图像工具 (编辑/超分/抠图/扩图)",
             dependencies=[Depends(rate_limit("edit", rpm=15, rph=120))])
async def edit_image_tool(
    request: Request,
    operation: str = Form(..., description="edit | upscale | bg-remove | extend"),
    image_file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    factor: str = Form("2"),
    ratio: str = Form("16:9"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    """Unified image-tool endpoint (对标 yapper 编辑/放大/去背景/扩图).
    Uploads the source to a public URL then runs the real KIE model.
    Authenticated + metered (guest session or JWT via resolve_user_id)."""
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

    tool_cost = _EDIT_TOOL_COSTS[op]
    tool_task_id = str(uuid.uuid4())
    team_id = resolve_team_id(request)
    # Persist a Task so /pricing/costs can align charged credits vs upstream res.cost.
    tool_task = Task(
        task_id=tool_task_id,
        user_id=user_id,
        prompt=(prompt or f"image-tool:{op}")[:5000],
        media_type="image_tool",
        quality="balanced",
        requested_model=f"image-tool-{op}",
        selected_model=f"image-tool-{op}",
        parameters={"operation": op, "charged_credits": tool_cost},
        estimated_cost=float(tool_cost),
        status="queued",
    )
    db.add(tool_task)
    await db.flush()
    if not await deduct_credits(
        db, user_id, tool_cost, tool_task_id, f"image-tool-{op}",
        team_id=team_id, description=f"Image tool {op}",
    ):
        tool_task.status = "failed"
        tool_task.error_message = f"积分不足，需要 {tool_cost} 积分"
        await db.commit()
        raise HTTPException(status_code=402, detail=f"积分不足，需要 {tool_cost} 积分")
    await db.commit()

    try:
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
            upstream = 0.0
            tool_task.status = "completed"
            tool_task.actual_cost = upstream
            tool_task.results = [{"type": "image", "url": url, "model": f"demo-{op}", "demo": True}]
            tool_task.parameters = {
                **(tool_task.parameters if isinstance(tool_task.parameters, dict) else {}),
                "operation": op,
                "charged_credits": tool_cost,
                "upstream_cost": upstream,
                "margin_credits": tool_cost - upstream,
                "demo": True,
            }
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(tool_task, "parameters")
            await db.commit()
            return {"url": url, "media_type": "image", "model": f"demo-{op}", "demo": True,
                    "operation": op, "cost_credits": tool_cost, "cost": upstream,
                    "task_id": tool_task_id, "margin_credits": tool_cost}

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
                raise RuntimeError(f"{op} 处理失败: {e}") from e
        if res is None:
            raise RuntimeError(f"{op} 处理失败: {last_err}")
        out = {"type": "image", "url": res.media_url, "media_url": res.media_url, "model": res.model}
        out = (await _a.to_thread(persist_results, [out]))[0]
        upstream = float(res.cost or 0)
        tool_task.status = "completed"
        tool_task.actual_cost = upstream
        tool_task.selected_model = res.model or f"image-tool-{op}"
        tool_task.results = [out]
        tool_task.parameters = {
            "operation": op,
            "charged_credits": tool_cost,
            "upstream_cost": upstream,
            "margin_credits": round(tool_cost - upstream, 4),
        }
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(tool_task, "parameters")
        await db.commit()
        return {"url": out.get("url"), "source_url": out.get("source_url", res.media_url),
                "media_type": "image", "model": res.model, "operation": op,
                "cost": upstream, "cost_credits": tool_cost,
                "task_id": tool_task_id, "margin_credits": round(tool_cost - upstream, 4)}
    except HTTPException:
        raise
    except Exception as e:
        tool_task.status = "failed"
        tool_task.error_message = str(e)[:500]
        await refund_task_credits(db, tool_task_id, reason="image_tool_failed")
        await db.commit()
        raise HTTPException(status_code=502, detail=str(e))


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


@router.post(
    "/extract-prompt",
    summary="Prompt Extractor（从图片/视频反推提示词）",
    description="对标 Yapper Prompt Extractor：上传或提供媒体 URL，提取可复用生成提示词。",
    dependencies=[Depends(rate_limit("extract", rpm=20, rph=120))],
)
async def extract_prompt(
    request: Request,
    media_file: Optional[UploadFile] = File(None),
    media_url: Optional[str] = Form(None),
    media_kind: Optional[str] = Form(None, description="image | video | auto"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(resolve_user_id),
):
    """Yapper-parity Prompt Extractor.

    Vision LLM when keyed; otherwise honest local heuristic (never pretends vision succeeded).
    Charges 1 credit only when vision mode succeeds.
    """
    from app.services.prompt_extract import extract_prompt_from_media, guess_media_kind
    from app.services.media_store import store_upload

    if not media_file and not (media_url and media_url.strip()):
        raise HTTPException(status_code=400, detail="请提供 media_file 或 media_url")

    filename = ""
    content_type = ""
    resolved_url = (media_url or "").strip()
    # Honesty: TikTok/Instagram/page URLs are not scraped (no URL-to-Viral yet).
    if resolved_url and not media_file:
        from app.services.prompt_extract import is_unsupported_social_page_url
        if is_unsupported_social_page_url(resolved_url):
            raise HTTPException(
                status_code=400,
                detail=(
                    "暂不支持从 TikTok/Instagram/X 等页面链接抓取媒体。"
                    "请上传文件，或粘贴可直链访问的图片/视频 URL（非社媒页面）。"
                    "（对标 Yapper URL-to-Viral 仍为缺口，不假装已解析。）"
                ),
            )
    if media_file is not None:
        raw = await media_file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="空文件")
        if len(raw) > 25 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件过大（≤25MB）")
        filename = media_file.filename or "media.bin"
        content_type = media_file.content_type or ""
        try:
            asset = await store_upload(db, filename, raw, content_type, user_id=user_id)
            resolved_url = asset.url
        except Exception as e:
            # Schema drift / library insert failure — still extract from a local write.
            logger.warning("extract-prompt store_upload fallback: %s", e)
            await db.rollback()
            import os
            from pathlib import Path
            from app.config import settings
            ext = os.path.splitext(filename)[1] or ".bin"
            dest_dir = Path(settings.STORAGE_LOCAL_PATH or "media") / "uploads"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"extract-{uuid.uuid4().hex[:12]}{ext}"
            dest.write_bytes(raw)
            resolved_url = f"/api/v1/media/uploads/{dest.name}"

    kind = (media_kind or "").strip().lower()
    if kind in ("", "auto"):
        kind = guess_media_kind(resolved_url, content_type, filename)
    if kind not in ("image", "video"):
        raise HTTPException(status_code=400, detail="media_kind 须为 image | video | auto")

    result = await extract_prompt_from_media(
        resolved_url,
        media_kind=kind,
        filename=filename,
        content_type=content_type,
        prefer_vision=True,
    )
    charged = 0
    if result.get("mode") == "vision":
        extract_id = f"extract-{uuid.uuid4()}"
        try:
            ok = await deduct_credits(
                db,
                user_id,
                1,
                extract_id,
                "prompt-extract",
                team_id=resolve_team_id(request),
                description="prompt_extract_vision",
            )
            if ok:
                charged = 1
                await db.commit()
            else:
                await db.rollback()
        except Exception as e:
            # Extraction still returns; metering soft-fails in low-credit edge cases
            logger.warning("extract-prompt credit charge skipped: %s", e)
            await db.rollback()

    result["charged_credits"] = charged
    result["create_links"] = {
        "image": "/create/image",
        "video": "/create/video",
        "agent": "/agent",
    }
    return result


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
