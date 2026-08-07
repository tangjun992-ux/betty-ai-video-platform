"""
Video generation Celery tasks with automatic fallback.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone

from celery_app import app
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.media_store import persist_results
from app.services.model_health import model_health, validate_generation_results

logger = logging.getLogger(__name__)


from app.tasks.task_db import update_task as _update_task, get_db_url_sync as _get_db_url_sync


def _load_adapters():
    from app.adapters.registry import get_adapter, _load_all_adapters
    _load_all_adapters()
    return get_adapter


def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _broadcast_progress(task_id: str, progress: int, stage: str, message: str = "", preview_url: str = ""):
    """Send real-time progress update via WebSocket (non-blocking, fire-and-forget)."""
    try:
        from app.api.websocket import broadcast_task_progress

        async def _send():
            payload = {
                "type": "progress",
                "progress": progress,
                "current_stage": stage,
                "message": message or stage,
            }
            if preview_url:
                payload["preview_url"] = preview_url
            await broadcast_task_progress(task_id, payload)

        _run_async(_send())
    except Exception:
        pass


@app.task(
    bind=True,
    name="app.tasks.video_tasks.generate_video",
    queue="video_q",
    max_retries=2,
    acks_late=True,
)
def generate_video_task(
    self, db_task_id: str, model: str, prompt: str, params: dict
) -> dict:
    """Video generation with automatic fallback."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if backend_dir not in os.getcwd():
        os.chdir(backend_dir)

    self.update_state(state="PROGRESS", meta={"current_stage": "routing", "progress": 5})
    _update_task(
        db_task_id, status="generating", selected_model=model,
        progress=5, current_stage="routing",
        started_at=datetime.now(timezone.utc),
    )
    _broadcast_progress(db_task_id, 5, "routing", "正在分析视频提示词...")

    image_url = params.get("image_url")
    ref_images = [u for u in (params.get("reference_images") or []) if u]
    if image_url and image_url not in ref_images:
        ref_images = [image_url] + ref_images
    ref_videos = [u for u in (params.get("reference_videos") or []) if u][:3]
    ref_audios = [u for u in (params.get("reference_audios") or []) if u][:3]
    omni = bool(params.get("omni")) or bool(ref_videos or ref_audios or len(ref_images) > 1)
    if image_url or ref_images or ref_videos or ref_audios:
        self.update_state(state="PROGRESS", meta={"current_stage": "loading_reference", "progress": 15})
        _update_task(db_task_id, progress=15, current_stage="loading_reference")
        msg = "正在加载 Omni 多模态参考..." if omni else "正在加载参考图片..."
        _broadcast_progress(db_task_id, 15, "loading_reference", msg)

    # Omni productization: prefer Seedance when multimodal refs present
    if omni and "seedance" not in (model or "").lower():
        logger.info("Omni refs present — routing %s → seedance-2.0", model)
        model = "seedance-2.0"
        _update_task(db_task_id, selected_model=model, current_stage="omni_route")

    self.update_state(state="PROGRESS", meta={"current_stage": "generating", "progress": 30})
    _update_task(db_task_id, progress=30, current_stage="generating")
    _broadcast_progress(db_task_id, 30, "generating", "Seedance Omni 生成中..." if omni else "视频模型已启动，开始生成...")

    # Demo mode: render locally when no provider key is configured.
    from app.adapters.demo_provider import demo_mode_active, DemoAdapter
    from app.gateway import gateway_enabled
    if demo_mode_active():
        adapter = DemoAdapter(model_label=model)
        use_gateway = False
    elif gateway_enabled():
        use_gateway = True
        adapter = None
    else:
        use_gateway = False
        get_adapter = _load_adapters()
        adapter = get_adapter(model)
        if not adapter:
            from app.fallback_handler import get_fallback
            fallback_id = get_fallback(model)
            if fallback_id:
                adapter = get_adapter(fallback_id)
                model = fallback_id
                _update_task(db_task_id, selected_model=model, current_stage="fallback_used")

        if not adapter:
            return _mark_failed(db_task_id, f"No adapter for model or fallback: {model}")

    duration = params.get("duration", 5)
    resolution = params.get("resolution", "1080p")

    self.update_state(state="PROGRESS", meta={"current_stage": "generating", "progress": 50})
    _update_task(db_task_id, progress=50)
    _broadcast_progress(db_task_id, 50, "generating", "视频渲染中，请耐心等待...")

    started = time.monotonic()
    try:
        if use_gateway:
            from app.gateway import gateway
            from app.tasks.gateway_context import gateway_call_kwargs
            gw = _run_async(gateway.generate_video(
                model=model,
                prompt=prompt,
                image_url=image_url or (ref_images[0] if ref_images else None),
                duration=duration,
                resolution=resolution,
                reference_images=ref_images,
                reference_videos=ref_videos,
                reference_audios=ref_audios,
                omni=omni,
                generate_audio=bool(params.get("generate_audio")),
                **gateway_call_kwargs(db_task_id),
            ))
            result = gw.result
            if gw.fallback_used:
                _update_task(db_task_id, current_stage="gateway_fallback", selected_model=model)
        else:
            result = _run_async(
                adapter.generate_video(
                    prompt=prompt,
                    model_id=model,
                    image_url=image_url or (ref_images[0] if ref_images else None),
                    duration=duration,
                    resolution=resolution,
                    reference_images=ref_images,
                    reference_videos=ref_videos,
                    reference_audios=ref_audios,
                    omni=omni,
                    generate_audio=bool(params.get("generate_audio")),
                )
            )
        quality_ok, quality_error = validate_generation_results(result, "video")
        if not quality_ok:
            raise RuntimeError(quality_error)

        self.update_state(state="PROGRESS", meta={"current_stage": "uploading", "progress": 85})
        _update_task(db_task_id, progress=85, current_stage="uploading")
        _broadcast_progress(db_task_id, 85, "uploading", "正在上传视频结果...")

        rd = result.to_dict() if hasattr(result, "to_dict") else result
        error = rd.get("error")
        if error:
            return _handle_retryable(
                self, db_task_id, model, error, prompt,
                {
                    "image_url": image_url, "duration": duration, "resolution": resolution,
                    "reference_images": ref_images, "reference_videos": ref_videos,
                    "reference_audios": ref_audios, "omni": omni,
                    "generate_audio": bool(params.get("generate_audio")),
                },
            )

        from app.services.demo_tag import demo_mode_active, tag_result
        output = [tag_result({
            "type": "video", "url": rd.get("media_url", ""),
            "thumbnail": rd.get("thumbnail_url", ""),
            "model": rd.get("model", model),
            "resolution": rd.get("resolution", resolution),
            "duration": rd.get("duration", duration),
            "cost": rd.get("cost", 0),
        }, demo=demo_mode_active() or rd.get("demo"))]
        cost = rd.get("cost", 0)

        output = persist_results(output)
        chained = _maybe_chain_lipsync(
            db_task_id, params,
            prompt,
            output[0].get("url", "") if output else "",
        )
        stage = "lipsync_queued" if chained else "completed"
        _update_task(
            db_task_id, status="completed", progress=100, current_stage=stage,
            completed_at=datetime.now(timezone.utc),
            results=json.dumps(output), actual_cost=cost,
        )
        model_health.record_success(model, int((time.monotonic() - started) * 1000))
        msg = "唇形同步已排队…" if chained else "视频生成完成！"
        _broadcast_progress(db_task_id, 100, stage, msg)
        result = {"status": "completed", "results": output, "cost": cost}
        if chained:
            result["lipsync_task_id"] = chained
        return result

    except RuntimeError as e:
        from app.fallback_handler import is_retryable_error
        model_health.record_failure(model, str(e), retryable=is_retryable_error(str(e)))
        return _handle_retryable(
            self, db_task_id, model, str(e), prompt,
            {
                "image_url": image_url, "duration": duration, "resolution": resolution,
                "reference_images": ref_images, "reference_videos": ref_videos,
                "reference_audios": ref_audios, "omni": omni,
                "generate_audio": bool(params.get("generate_audio")),
            },
        )
    except Exception as e:
        from app.fallback_handler import is_retryable_error
        model_health.record_failure(model, str(e), retryable=is_retryable_error(str(e)))
        return _mark_failed(db_task_id, str(e))


def _maybe_chain_lipsync(db_task_id: str, params: dict, prompt: str, video_url: str) -> str | None:
    """Queue Kling lipsync after video when post_lipsync=true (Omni integrated flow)."""
    if not params.get("post_lipsync"):
        return None
    portrait = (params.get("image_url") or "").strip()
    if not portrait and params.get("reference_images"):
        refs = params.get("reference_images") or []
        if refs:
            portrait = str(refs[0]).strip()
    if not portrait:
        logger.warning("post_lipsync skipped: no portrait image for task %s", db_task_id)
        return None
    text = (params.get("lipsync_text") or prompt or "").strip()[:2000]
    if not text:
        return None
    try:
        import uuid
        from celery_app import app as celery_app
        from app.tasks.task_db import get_task_gateway_context, get_db_url_sync
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from app.models.task import Task

        ctx = get_task_gateway_context(db_task_id)
        user_id = ctx.get("user_id")
        if not user_id:
            return None
        lipsync_id = str(uuid.uuid4())
        voice_id = params.get("lipsync_voice_id") or "zh-CN-XiaoxiaoNeural"
        engine = create_engine(get_db_url_sync())
        with Session(engine) as session:
            session.add(Task(
                task_id=lipsync_id,
                user_id=int(user_id),
                prompt=text,
                media_type="video",
                quality="balanced",
                requested_model="lipsync-demo",
                selected_model="kling/ai-avatar-pro",
                parameters={
                    "image_url": portrait,
                    "text": text,
                    "voice_id": voice_id,
                    "tier": "demo",
                    "parent_task_id": db_task_id,
                    "parent_video_url": video_url,
                },
                estimated_cost=4.0,
                status="queued",
                current_stage="post_lipsync_chain",
            ))
            session.commit()
        celery_app.send_task(
            "app.tasks.lipsync_tasks.process_lipsync",
            args=[lipsync_id, portrait, None, text, voice_id, "kling/ai-avatar-pro"],
            queue="video_q",
        )
        _update_task(db_task_id, current_stage="lipsync_queued")
        logger.info("post_lipsync chained %s → %s", db_task_id, lipsync_id)
        return lipsync_id
    except Exception as e:
        logger.warning("post_lipsync chain failed for %s: %s", db_task_id, e)
        return None


def _handle_retryable(self, db_task_id, model, error, prompt, params: dict):
    from app.fallback_handler import get_fallback, is_retryable_error
    from app.gateway import gateway_enabled

    if not is_retryable_error(error):
        return _mark_failed(db_task_id, error)

    fallback_id = get_fallback(model)
    if not fallback_id:
        return _mark_failed(db_task_id, f"{error} (no fallback)")

    logger.info("Fallback from %s to %s: %s", model, fallback_id, error)
    _update_task(db_task_id, selected_model=fallback_id, current_stage="fallback_used")

    image_url = params.get("image_url")
    ref_images = params.get("reference_images") or []
    duration = params.get("duration", 5)
    resolution = params.get("resolution", "1080p")

    started = time.monotonic()
    try:
        if gateway_enabled():
            from app.gateway import gateway
            from app.tasks.gateway_context import gateway_call_kwargs
            gw = _run_async(gateway.generate_video(
                model=fallback_id,
                prompt=prompt,
                image_url=image_url or (ref_images[0] if ref_images else None),
                duration=duration,
                resolution=resolution,
                reference_images=ref_images,
                reference_videos=params.get("reference_videos") or [],
                reference_audios=params.get("reference_audios") or [],
                omni=bool(params.get("omni")),
                generate_audio=bool(params.get("generate_audio")),
                **gateway_call_kwargs(db_task_id),
            ))
            result = gw.result
        else:
            get_adapter = _load_adapters()
            fb = get_adapter(fallback_id)
            if not fb:
                return _mark_failed(db_task_id, f"Fallback not found: {fallback_id}")
            result = _run_async(
                fb.generate_video(
                    prompt=prompt, model_id=fallback_id, image_url=image_url,
                    duration=duration, resolution=resolution,
                )
            )

        rd = result.to_dict() if hasattr(result, "to_dict") else result
        quality_ok, quality_error = validate_generation_results(result, "video")
        if not quality_ok:
            raise RuntimeError(quality_error)
        if rd.get("error"):
            return _mark_failed(db_task_id, f"Fallback also failed: {rd['error']}")

        output = [{
            "type": "video", "url": rd.get("media_url", ""),
            "thumbnail": rd.get("thumbnail_url", ""),
            "model": fallback_id,
            "resolution": rd.get("resolution", resolution),
            "duration": rd.get("duration", duration),
            "cost": rd.get("cost", 0),
        }]
        cost = rd.get("cost", 0)
        output = persist_results(output)
        _update_task(
            db_task_id, status="completed", progress=100, current_stage="completed_fallback",
            completed_at=datetime.now(timezone.utc),
            results=json.dumps(output), actual_cost=cost,
        )
        model_health.record_success(fallback_id, int((time.monotonic() - started) * 1000))
        return {"status": "completed_fallback", "results": output, "cost": cost}
    except Exception as fe:
        from app.fallback_handler import is_retryable_error
        model_health.record_failure(fallback_id, str(fe), retryable=is_retryable_error(str(fe)))
        return _mark_failed(db_task_id, f"Fallback also failed: {fe}. Original: {error}")


def _translate_error(error_msg: str) -> str:
    """Translate raw API errors to user-friendly Chinese messages."""
    err_lower = error_msg.lower()
    if any(w in err_lower for w in ("guardrails", "nudity", "sexuality", "erotic", "inappropriate", "content policy", "safety system")):
        return "内容不合规：您的提示词包含不当内容，已被 AI 安全系统拦截。请修改后重试。"
    if "violates" in err_lower:
        return "内容不合规：提示词违反了内容安全策略。请使用合规的描述重新尝试。"
    if "timeout" in err_lower or "timed out" in err_lower:
        return "生成超时：AI 模型响应时间过长，请稍后重试或简化提示词。"
    if "rate" in err_lower and ("limit" in err_lower or "exceeded" in err_lower):
        return "请求过于频繁：请稍等片刻后再试。"
    return error_msg


def _mark_failed(db_task_id: str, error_msg: str) -> dict:
    friendly_msg = _translate_error(error_msg)
    logger.error(f"Task {db_task_id} failed: {error_msg}")
    _update_task(
        db_task_id, status="failed", progress=0, current_stage="failed",
        error_message=friendly_msg, completed_at=datetime.now(timezone.utc),
    )
    return {"status": "failed", "error": friendly_msg}
