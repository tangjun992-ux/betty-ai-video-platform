"""
Video generation Celery tasks with automatic fallback.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone

from celery_app import app
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.media_store import persist_results

logger = logging.getLogger(__name__)


def _get_db_url_sync():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    if db_url.startswith("sqlite+aiosqlite"):
        db_url = db_url.replace("sqlite+aiosqlite", "sqlite")
    elif db_url.startswith("postgresql+asyncpg"):
        db_url = db_url.replace("postgresql+asyncpg", "postgresql")
    return db_url


def _update_task(db_task_id: str, **kwargs):
    db_url = _get_db_url_sync()
    engine = create_engine(db_url)
    with Session(engine) as session:
        stmt = text("SELECT id FROM tasks WHERE task_id = :tid")
        row = session.execute(stmt, {"tid": db_task_id}).first()
        if not row:
            return None
        task_pk = row[0]
        for field, value in kwargs.items():
            if value is not None:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                session.execute(
                    text(f"UPDATE tasks SET {field} = :val WHERE id = :id"),
                    {"val": value, "id": task_pk},
                )
        session.commit()
        return task_pk


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
    if image_url:
        self.update_state(state="PROGRESS", meta={"current_stage": "loading_reference", "progress": 15})
        _update_task(db_task_id, progress=15, current_stage="loading_reference")
        _broadcast_progress(db_task_id, 15, "loading_reference", "正在加载参考图片...")

    self.update_state(state="PROGRESS", meta={"current_stage": "generating", "progress": 30})
    _update_task(db_task_id, progress=30, current_stage="generating")
    _broadcast_progress(db_task_id, 30, "generating", "视频模型已启动，开始生成...")

    # Demo mode: render locally when no provider key is configured.
    from app.adapters.demo_provider import demo_mode_active, DemoAdapter
    if demo_mode_active():
        adapter = DemoAdapter(model_label=model)
    else:
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

    try:
        result = _run_async(
            adapter.generate_video(
                prompt=prompt, model_id=model, image_url=image_url,
                duration=duration, resolution=resolution,
            )
        )

        self.update_state(state="PROGRESS", meta={"current_stage": "uploading", "progress": 85})
        _update_task(db_task_id, progress=85, current_stage="uploading")
        _broadcast_progress(db_task_id, 85, "uploading", "正在上传视频结果...")

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
        _update_task(
            db_task_id, status="completed", progress=100, current_stage="completed",
            completed_at=datetime.now(timezone.utc),
            results=json.dumps(output), actual_cost=cost,
        )
        _broadcast_progress(db_task_id, 100, "completed", "视频生成完成！")
        return {"status": "completed", "results": output, "cost": cost}

    except RuntimeError as e:
        return _handle_retryable(self, db_task_id, model, str(e), prompt, image_url, duration, resolution)
    except Exception as e:
        return _mark_failed(db_task_id, str(e))


def _handle_retryable(self, db_task_id, model, error, prompt, image_url, duration, resolution):
    from app.fallback_handler import get_fallback, is_retryable_error

    if not is_retryable_error(error):
        return _mark_failed(db_task_id, error)

    fallback_id = get_fallback(model)
    if not fallback_id:
        return _mark_failed(db_task_id, f"{error} (no fallback)")

    logger.info(f"Fallback from {model} to {fallback_id}: {error}")
    _update_task(db_task_id, selected_model=fallback_id, current_stage="fallback_used")

    get_adapter = _load_adapters()
    fb = get_adapter(fallback_id)
    if not fb:
        return _mark_failed(db_task_id, f"Fallback not found: {fallback_id}")

    try:
        result = _run_async(
            fb.generate_video(
                prompt=prompt, model_id=fallback_id, image_url=image_url,
                duration=duration, resolution=resolution,
            )
        )
        rd = result.to_dict() if hasattr(result, "to_dict") else result
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
        return {"status": "completed_fallback", "results": output, "cost": cost}
    except Exception as fe:
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
