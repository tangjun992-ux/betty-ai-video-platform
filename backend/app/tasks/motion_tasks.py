"""
Motion Control Celery Task — 动作迁移：图片+参考视频 → AI 生成
Uses Seedance video API with image_url + video_url for motion transfer.
On failure, marks task failed explicitly — no silent simulation.
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


def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _broadcast_progress(task_id: str, progress: int, stage: str, message: str = ""):
    try:
        from app.api.websocket import broadcast_task_progress

        async def _send():
            await broadcast_task_progress(task_id, {
                "type": "progress",
                "progress": progress,
                "current_stage": stage,
                "message": message or stage,
            })

        _run_async(_send())
    except Exception:
        pass


def _fail_task(db_task_id: str, message: str):
    """Mark motion task failed — never return fake/simulated media."""
    _update_task(
        db_task_id,
        status="failed",
        progress=0,
        current_stage="failed",
        error_message=message,
        completed_at=datetime.now(timezone.utc),
    )
    _broadcast_progress(db_task_id, 0, "failed", message)
    logger.error("Motion control failed: task=%s %s", db_task_id, message)
    return {"status": "failed", "error": message}


@app.task(bind=True, max_retries=2, default_retry_delay=30)
def process_motion_task(self, db_task_id: str, model: str, prompt: str, params: dict):
    """
    Motion control: use image_url + video_url (reference motion) → video generation.
    """
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if backend_dir not in os.getcwd():
        os.chdir(backend_dir)

    image_url = params.get("image_url", "")
    video_url = params.get("video_url", "")
    style = params.get("style", "realistic")

    logger.info("Motion control: task=%s image=%s... video=%s...", db_task_id, image_url[:50], video_url[:50])

    _broadcast_progress(db_task_id, 5, "loading", "加载运动迁移模型...")
    _update_task(db_task_id, status="generating", progress=5, current_stage="loading")

    _broadcast_progress(db_task_id, 15, "analyzing", "分析参考视频动作轨迹...")
    _update_task(db_task_id, progress=15, current_stage="analyzing")

    # No provider keys → fail fast with clear message (no demo/simulation).
    from app.adapters.demo_provider import demo_mode_active
    if demo_mode_active():
        return _fail_task(
            db_task_id,
            "运动控制需要配置模型 API Key（KIE/Seedance）。当前为演示环境，无法生成真实动作迁移视频。",
        )

    _broadcast_progress(db_task_id, 35, "transferring", "将动作迁移到目标人物...")
    _update_task(db_task_id, progress=35, current_stage="transferring")

    motion_prompt = prompt or "motion transfer, the person performs the same action as the reference video"
    if style and style != "realistic":
        motion_prompt = f"{motion_prompt}, {style} style"

    # Prefer dedicated motion API on KIE, then generic generate_video fallbacks.
    last_error = "未知错误"
    try:
        from app.adapters.kie_adapter import KieAdapter
        kie = KieAdapter()
        if kie.is_available() and hasattr(kie, "generate_motion"):
            _broadcast_progress(db_task_id, 45, "generating", "KIE motion 专用通道生成中...")
            _update_task(db_task_id, progress=45, current_stage="generating")
            result = _run_async(kie.generate_motion(
                image_url=image_url,
                video_url=video_url,
                prompt=motion_prompt,
                model_id="seedance-2.0-fast",
                duration=int(params.get("duration", 5) or 5),
                resolution=params.get("resolution", "720p"),
            ))
            rd = result.to_dict() if hasattr(result, "to_dict") else result
            media_url = rd.get("media_url") or rd.get("url") or ""
            if media_url:
                output = [{
                    "type": "video",
                    "url": media_url,
                    "thumbnail": rd.get("thumbnail_url", "") or image_url,
                    "model": rd.get("model", "kie/motion"),
                    "resolution": rd.get("resolution", "720p"),
                    "duration": rd.get("duration", 5),
                    "cost": rd.get("cost", 6),
                    "op": "motion",
                }]
                output = persist_results(output)
                _update_task(
                    db_task_id, status="completed", progress=100, current_stage="completed",
                    completed_at=datetime.now(timezone.utc),
                    results=json.dumps(output),
                    result_url=output[0].get("url", "") if output else "",
                    actual_cost=rd.get("cost", 6),
                )
                _broadcast_progress(db_task_id, 100, "completed", "运动控制生成完成！")
                return {"status": "completed", "results": output}
            last_error = "KIE motion 未返回视频 URL"
    except Exception as e:
        last_error = str(e)
        logger.warning("KIE generate_motion failed, falling back: %s", e)

    adapters_to_try = []
    try:
        from app.adapters.registry import get_adapter, _load_all_adapters
        _load_all_adapters()
        for mid in ("bytedance/seedance-2-fast", "seedance-2-fast", "seedance-2.0-fast"):
            ad = get_adapter(mid)
            if ad:
                adapters_to_try.append((mid, ad))
                break
    except Exception as e:
        logger.warning("Adapter registry load failed: %s", e)

    if not adapters_to_try:
        try:
            from app.adapters.kie_adapter import KieAdapter
            adapters_to_try.append(("kie/seedance", KieAdapter()))
        except Exception as e:
            logger.warning("KIE adapter unavailable: %s", e)

    if not adapters_to_try:
        return _fail_task(db_task_id, "未找到可用的运动控制模型适配器，请检查 KIE_API_KEY 配置。")

    for model_id, adapter in adapters_to_try:
        try:
            _broadcast_progress(db_task_id, 50, "generating", f"{model_id} 视频生成中...")
            _update_task(db_task_id, progress=50, current_stage="generating")

            gen_kwargs = dict(
                prompt=motion_prompt,
                image_url=image_url,
                duration=params.get("duration", 5),
                resolution=params.get("resolution", "1080p"),
            )
            # video_url for motion reference (adapter may ignore if unsupported)
            if hasattr(adapter, "generate_video"):
                try:
                    result = _run_async(adapter.generate_video(**gen_kwargs, video_url=video_url))
                except TypeError:
                    result = _run_async(adapter.generate_video(**gen_kwargs))
            else:
                continue

            rd = result.to_dict() if hasattr(result, "to_dict") else result
            error = rd.get("error")
            media_url = rd.get("media_url") or rd.get("url") or ""

            if error or not media_url:
                last_error = error or "模型未返回视频 URL"
                logger.warning("Motion %s failed: %s", model_id, last_error)
                continue

            output = [{
                "type": "video",
                "url": media_url,
                "thumbnail": rd.get("thumbnail_url", "") or image_url,
                "model": rd.get("model", model_id),
                "resolution": rd.get("resolution", "1080p"),
                "duration": rd.get("duration", 5),
                "cost": rd.get("cost", 6),
            }]
            output = persist_results(output)
            _update_task(
                db_task_id, status="completed", progress=100, current_stage="completed",
                completed_at=datetime.now(timezone.utc),
                results=json.dumps(output),
                result_url=output[0].get("url", "") if output else "",
                actual_cost=rd.get("cost", 6),
            )
            _broadcast_progress(db_task_id, 100, "completed", "运动控制生成完成！")
            logger.info("Motion control completed: task=%s model=%s", db_task_id, model_id)
            return {"status": "completed", "results": output}

        except Exception as e:
            last_error = str(e)
            logger.warning("Motion adapter %s error: %s", model_id, e)

    return _fail_task(db_task_id, f"运动控制生成失败：{last_error}")
