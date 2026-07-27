"""Performance Drive task: native Motion, then optional Lipsync talk on source still."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

from celery_app import app
from app.tasks.task_db import update_task as _update_task

logger = logging.getLogger(__name__)


def _broadcast(task_id: str, progress: int, stage: str, message: str = ""):
    try:
        from app.api.websocket import broadcast_task_progress

        async def _send():
            await broadcast_task_progress(task_id, {
                "type": "progress",
                "progress": progress,
                "current_stage": stage,
                "message": message or stage,
            })

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_send())
        finally:
            loop.close()
    except Exception:
        pass


def _fail(db_task_id: str, err: str) -> dict:
    _update_task(
        db_task_id,
        status="failed",
        progress=100,
        current_stage="failed",
        error_message=err[:500],
        completed_at=datetime.now(timezone.utc),
    )
    try:
        from app.services.credits import refund_task_credits_sync
        refund_task_credits_sync(db_task_id, reason="performance_failed")
    except Exception as e:
        logger.warning("performance refund failed: %s", e)
    _broadcast(db_task_id, 100, "failed", err[:120])
    return {"status": "failed", "error": err}


@app.task(
    bind=True,
    name="app.tasks.performance_tasks.process_performance",
    queue="video_q",
    max_retries=1,
    acks_late=True,
)
def process_performance(self, db_task_id: str, params: dict) -> dict:
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if backend_dir not in os.getcwd():
        os.chdir(backend_dir)

    from app.adapters.demo_provider import demo_mode_active
    if demo_mode_active():
        return _fail(db_task_id, "演示模式无法跑 Performance Drive：请配置 KIE_API_KEY")

    image_url = (params.get("image_url") or "").strip()
    video_url = (params.get("video_url") or "").strip()
    if not image_url or not video_url:
        return _fail(db_task_id, "缺少 image_url 或 video_url")

    _update_task(
        db_task_id,
        status="generating",
        progress=10,
        current_stage="motion",
        started_at=datetime.now(timezone.utc),
    )
    _broadcast(db_task_id, 10, "motion", "Performance：原生 Motion Control…")

    from app.adapters.kie_adapter import KieAdapter
    from app.services.media_store import persist_results

    kie = KieAdapter()
    output = []
    total_cost = 0

    try:
        motion = asyncio.run(kie.generate_motion(
            image_url=image_url,
            video_url=video_url,
            prompt=params.get("prompt") or "No distortion, natural motion transfer.",
            model_id="motion-control" if params.get("tier") != "studio" else "motion-control-studio",
            duration=5,
            resolution="1080p" if params.get("tier") == "studio" else "720p",
            character_orientation="video",
            studio=params.get("tier") == "studio",
        ))
        murl = getattr(motion, "media_url", "") or ""
        if not murl:
            return _fail(db_task_id, "Motion 未返回视频")
        total_cost += int(getattr(motion, "cost", 0) or 0)
        output.append({
            "type": "video",
            "url": murl,
            "thumbnail": getattr(motion, "thumbnail_url", "") or image_url,
            "model": getattr(motion, "model", "kling-3.0/motion-control"),
            "op": "performance_motion",
            "cost": getattr(motion, "cost", 0),
            "honesty": "原生 Kling Motion Control；≠ Act-One",
        })
    except Exception as e:
        logger.exception("performance motion failed")
        return _fail(db_task_id, f"Motion 失败: {e}")

    with_talk = bool(params.get("with_talk"))
    voice_text = (params.get("voice_text") or "").strip()
    audio_url = (params.get("audio_url") or "").strip()

    if with_talk:
        _update_task(db_task_id, progress=55, current_stage="talk")
        _broadcast(db_task_id, 55, "talk", "Performance：追加口播 Lipsync…")
        try:
            talk_audio = audio_url
            if not talk_audio and voice_text:
                tts = asyncio.run(kie.generate_speech(
                    voice_text, voice=params.get("voice") or "Rachel",
                ))
                talk_audio = getattr(tts, "media_url", "") or ""
                total_cost += int(getattr(tts, "cost", 0) or 0)
                if talk_audio:
                    output.append({
                        "type": "audio",
                        "url": talk_audio,
                        "model": getattr(tts, "model", "tts"),
                        "op": "performance_tts",
                        "cost": getattr(tts, "cost", 0),
                    })
            if not talk_audio:
                logger.warning("performance talk skipped — no audio")
            else:
                # Upload local paths if needed — lipsync expects public URLs
                lip = asyncio.run(kie.generate_lipsync(
                    image_url=image_url,
                    audio_url=talk_audio,
                    prompt="natural talking performance on camera",
                    resolution="720p" if params.get("tier") == "studio" else "480p",
                ))
                lurl = getattr(lip, "media_url", "") or ""
                total_cost += int(getattr(lip, "cost", 0) or 0)
                if lurl:
                    output.append({
                        "type": "video",
                        "url": lurl,
                        "thumbnail": image_url,
                        "model": getattr(lip, "model", "kling/ai-avatar-pro"),
                        "op": "performance_talk",
                        "cost": getattr(lip, "cost", 0),
                        "honesty": "Lipsync 口播片段；与 Motion 分轨输出，非 Act-One 一体编码器",
                    })
        except Exception as e:
            logger.warning("performance talk failed (motion kept): %s", e)
            output.append({
                "type": "note",
                "op": "performance_talk_failed",
                "error": str(e)[:240],
                "honesty": "口播阶段失败；动作视频仍可用",
            })

    output = persist_results([o for o in output if o.get("url") or o.get("type") == "note"])
    result_url = next((o.get("url") for o in output if o.get("type") == "video" and o.get("url")), "")
    _update_task(
        db_task_id,
        status="completed",
        progress=100,
        current_stage="completed",
        completed_at=datetime.now(timezone.utc),
        results=json.dumps(output),
        result_url=result_url,
        actual_cost=total_cost,
    )
    _broadcast(db_task_id, 100, "completed", "Performance Drive 完成")
    return {"status": "completed", "results": output}
