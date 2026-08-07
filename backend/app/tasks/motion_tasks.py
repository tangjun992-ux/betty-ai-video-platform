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

from app.services.media_store import persist_results

logger = logging.getLogger(__name__)

from app.tasks.task_db import update_task as _update_task

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

    from app.gateway import gateway, gateway_enabled
    from app.tasks.gateway_context import gateway_call_kwargs
    motion_model = (
        model
        or params.get("model")
        or ("motion-control-studio" if params.get("tier") == "studio" else "motion-control")
    )
    studio = params.get("tier") == "studio"

    if not gateway_enabled():
        return _fail_task(db_task_id, "Model Gateway 未启用，无法执行运动控制。")

    last_error = "Gateway motion 未返回视频 URL"
    try:
        _broadcast_progress(db_task_id, 45, "generating", "Gateway motion 通道生成中...")
        _update_task(db_task_id, progress=45, current_stage="generating")
        gw = _run_async(gateway.generate_motion(
            image_url=image_url,
            video_url=video_url,
            model=motion_model,
            prompt=motion_prompt,
            duration=int(params.get("duration", 5) or 5),
            resolution=params.get("resolution", "720p") or ("1080p" if studio else "720p"),
            studio=studio,
            character_orientation=params.get("character_orientation") or "video",
            background_source=params.get("background_source"),
            **gateway_call_kwargs(db_task_id),
        ))
        result = gw.result
        rd = result.to_dict() if hasattr(result, "to_dict") else result
        media_url = rd.get("media_url") or rd.get("url") or ""
        if not media_url:
            return _fail_task(db_task_id, last_error)

        output = [{
            "type": "video",
            "url": media_url,
            "thumbnail": rd.get("thumbnail_url", "") or image_url,
            "model": rd.get("model", "kie/motion"),
            "resolution": rd.get("resolution", "720p"),
            "duration": rd.get("duration", 5),
            "cost": rd.get("cost", 6),
            "op": "motion",
            "gateway_provider": gw.provider_used,
            "gateway_fallback": gw.fallback_used,
        }]
        voice_text = (params.get("voice_text") or "").strip()
        if voice_text:
            try:
                _broadcast_progress(db_task_id, 90, "voice", "正在生成旁白音频...")
                tgw = _run_async(gateway.generate_speech(
                    voice_text,
                    voice=params.get("voice") or "Rachel",
                    **gateway_call_kwargs(db_task_id, include_cost=False),
                ))
                tts_d = tgw.result.to_dict() if hasattr(tgw.result, "to_dict") else tgw.result
                audio_url_out = tts_d.get("media_url") or tts_d.get("url") or ""
                if audio_url_out:
                    output.append({
                        "type": "audio",
                        "url": audio_url_out,
                        "model": tts_d.get("model", "tts"),
                        "cost": tts_d.get("cost", 0),
                        "op": "motion_voice",
                        "note": "旁白 TTS；非实时变声引擎",
                    })
            except Exception as ve:
                logger.warning("motion voice TTS failed (non-fatal): %s", ve)
        output = persist_results(output)
        _update_task(
            db_task_id, status="completed", progress=100, current_stage="completed",
            completed_at=datetime.now(timezone.utc),
            results=json.dumps(output),
            actual_cost=rd.get("cost", 6),
        )
        _broadcast_progress(db_task_id, 100, "completed", "运动控制生成完成！")
        return {"status": "completed", "results": output}
    except Exception as e:
        logger.exception("Gateway motion failed task=%s", db_task_id)
        return _fail_task(db_task_id, f"运动控制生成失败：{e}")
