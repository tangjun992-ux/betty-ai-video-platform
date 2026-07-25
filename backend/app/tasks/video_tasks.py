"""
Video generation Celery tasks with automatic fallback.
"""
import json
import logging
import time
from datetime import datetime, timezone

from celery_app import app

from app.services.media_store import persist_results
from app.services.model_health import model_health, validate_generation_results

from app.tasks.common import broadcast_progress, chdir_backend_root, load_adapters, run_async, update_task

logger = logging.getLogger(__name__)


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
    chdir_backend_root()

    self.update_state(state="PROGRESS", meta={"current_stage": "routing", "progress": 5})
    update_task(
        db_task_id, status="generating", selected_model=model,
        progress=5, current_stage="routing",
        started_at=datetime.now(timezone.utc),
    )
    broadcast_progress(db_task_id, 5, "routing", "正在分析视频提示词...")

    image_url = params.get("image_url")
    if image_url:
        self.update_state(state="PROGRESS", meta={"current_stage": "loading_reference", "progress": 15})
        update_task(db_task_id, progress=15, current_stage="loading_reference")
        broadcast_progress(db_task_id, 15, "loading_reference", "正在加载参考图片...")

    self.update_state(state="PROGRESS", meta={"current_stage": "generating", "progress": 30})
    update_task(db_task_id, progress=30, current_stage="generating")
    broadcast_progress(db_task_id, 30, "generating", "视频模型已启动，开始生成...")

    # Demo mode: render locally when no provider key is configured.
    from app.adapters.demo_provider import demo_mode_active, DemoAdapter
    if demo_mode_active():
        adapter = DemoAdapter(model_label=model)
    else:
        get_adapter = load_adapters()
        adapter = get_adapter(model)
        if not adapter:
            from app.fallback_handler import get_fallback
            fallback_id = get_fallback(model)
            if fallback_id:
                adapter = get_adapter(fallback_id)
                model = fallback_id
                update_task(db_task_id, selected_model=model, current_stage="fallback_used")

        if not adapter:
            return _mark_failed(db_task_id, f"No adapter for model or fallback: {model}")

    duration = params.get("duration", 5)
    resolution = params.get("resolution", "1080p")

    self.update_state(state="PROGRESS", meta={"current_stage": "generating", "progress": 50})
    update_task(db_task_id, progress=50)
    broadcast_progress(db_task_id, 50, "generating", "视频渲染中，请耐心等待...")

    started = time.monotonic()
    try:
        result = run_async(
            adapter.generate_video(
                prompt=prompt, model_id=model, image_url=image_url,
                duration=duration, resolution=resolution,
            )
        )
        quality_ok, quality_error = validate_generation_results(result, "video")
        if not quality_ok:
            raise RuntimeError(quality_error)

        self.update_state(state="PROGRESS", meta={"current_stage": "uploading", "progress": 85})
        update_task(db_task_id, progress=85, current_stage="uploading")
        broadcast_progress(db_task_id, 85, "uploading", "正在上传视频结果...")

        rd = result.to_dict() if hasattr(result, "to_dict") else result
        error = rd.get("error")
        if error:
            return _handle_retryable(self, db_task_id, model, error, prompt, image_url, duration, resolution)

        output = [{
            "type": "video", "url": rd.get("media_url", ""),
            "thumbnail": rd.get("thumbnail_url", ""),
            "model": rd.get("model", model),
            "resolution": rd.get("resolution", resolution),
            "duration": rd.get("duration", duration),
            "cost": rd.get("cost", 0),
        }]
        cost = rd.get("cost", 0)

        output = persist_results(output)
        update_task(
            db_task_id, status="completed", progress=100, current_stage="completed",
            completed_at=datetime.now(timezone.utc),
            results=json.dumps(output), actual_cost=cost,
        )
        model_health.record_success(model, int((time.monotonic() - started) * 1000))
        broadcast_progress(db_task_id, 100, "completed", "视频生成完成！")
        return {"status": "completed", "results": output, "cost": cost}

    except RuntimeError as e:
        from app.fallback_handler import is_retryable_error
        model_health.record_failure(model, str(e), retryable=is_retryable_error(str(e)))
        return _handle_retryable(self, db_task_id, model, str(e), prompt, image_url, duration, resolution)
    except Exception as e:
        from app.fallback_handler import is_retryable_error
        model_health.record_failure(model, str(e), retryable=is_retryable_error(str(e)))
        return _mark_failed(db_task_id, str(e))


def _handle_retryable(self, db_task_id, model, error, prompt, image_url, duration, resolution):
    from app.fallback_handler import get_fallback, is_retryable_error

    if not is_retryable_error(error):
        return _mark_failed(db_task_id, error)

    fallback_id = get_fallback(model)
    if not fallback_id:
        return _mark_failed(db_task_id, f"{error} (no fallback)")

    logger.info(f"Fallback from {model} to {fallback_id}: {error}")
    update_task(db_task_id, selected_model=fallback_id, current_stage="fallback_used")

    get_adapter = load_adapters()
    fb = get_adapter(fallback_id)
    if not fb:
        return _mark_failed(db_task_id, f"Fallback not found: {fallback_id}")

    started = time.monotonic()
    try:
        result = run_async(
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
        update_task(
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
    update_task(
        db_task_id, status="failed", progress=0, current_stage="failed",
        error_message=friendly_msg, completed_at=datetime.now(timezone.utc),
    )
    return {"status": "failed", "error": friendly_msg}
