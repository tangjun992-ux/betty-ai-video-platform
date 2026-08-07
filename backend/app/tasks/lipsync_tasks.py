"""Lipsync Celery task — processes image + audio to create talking video."""
import asyncio
import json
import logging
import os
import uuid
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


@app.task(
    bind=True,
    name="app.tasks.lipsync_tasks.process_lipsync",
    queue="video_q",
    max_retries=2,
    acks_late=True,
)
def process_lipsync(
    self, db_task_id: str, image_url: str, audio_url: str | None,
    text: str | None, voice_id: str, model: str
) -> dict:
    """Process lipsync: image + audio/text → talking video."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if backend_dir not in os.getcwd():
        os.chdir(backend_dir)

    self.update_state(state="PROGRESS", meta={"current_stage": "lipsync_init", "progress": 5})
    _update_task(db_task_id, status="generating", progress=5, current_stage="lipsync_init",
                 started_at=datetime.now(timezone.utc))
    _broadcast_progress(db_task_id, 5, "lipsync_init", "正在加载参考图片...")

    try:
        from app.adapters.demo_provider import demo_mode_active, _local_media_path, render_demo_video
        from app.gateway import gateway, gateway_enabled
        from app.tasks.gateway_context import gateway_call_kwargs

        demo = demo_mode_active()
        tts_engine = None
        use_gw = gateway_enabled() and not demo

        async def _to_public(url: str, default_ct: str) -> str:
            if demo or not use_gw:
                from app.adapters.kie_adapter import KieAdapter
                if not url:
                    return url
                if url.startswith(("http://", "https://")):
                    if "/api/v1/media" not in url and "localhost" not in url and "127.0.0.1" not in url:
                        return url
                p = _local_media_path(url)
                if not p:
                    return url
                with open(p, "rb") as f:
                    data = f.read()
                ext = os.path.splitext(p)[1].lstrip(".") or ("png" if "image" in default_ct else "mp3")
                ct = f"image/{ext}" if default_ct.startswith("image") else f"audio/{ext}"
                return await KieAdapter().upload_public_url(
                    data, filename=f"ls_{uuid.uuid4().hex[:8]}.{ext}", content_type=ct,
                )
            return await gateway.publicize_url(url, default_content_type=default_ct, trace_id=db_task_id)

        audio_public = audio_url
        if text and not audio_url:
            self.update_state(state="PROGRESS", meta={"current_stage": "tts", "progress": 15})
            _update_task(db_task_id, progress=15, current_stage="tts")
            _broadcast_progress(db_task_id, 15, "tts", "正在合成语音...")
            if demo:
                from app.adapters.demo_provider import render_demo_speech
                audio_public = render_demo_speech(text)
            else:
                from app.services.audio_prep import is_azure_neural_voice, synthesize_speech_edge
                voice = (voice_id or "zh-CN-XiaoxiaoNeural").strip() or "zh-CN-XiaoxiaoNeural"
                if is_azure_neural_voice(voice):
                    try:
                        wav_bytes, used_voice = _run_async(synthesize_speech_edge(text, voice))
                        audio_public = _run_async(gateway.upload_public_url(
                            wav_bytes,
                            filename=f"ls_tts_{uuid.uuid4().hex[:8]}.wav",
                            content_type="audio/wav",
                        ))
                        tts_engine = f"edge-tts:{used_voice}"
                    except Exception as e:
                        logger.warning("[lipsync] edge-tts failed (%s) → ElevenLabs fallback", e)
                        el_voice = "Rachel" if any(
                            k in voice for k in ("Xiaoxiao", "Xiaoyi", "Jenny", "Nanami")
                        ) else "Adam"
                        gw = _run_async(gateway.generate_speech(
                            text, voice=el_voice,
                            **gateway_call_kwargs(db_task_id, include_cost=False),
                            language_code="zh" if voice.startswith("zh-") else None,
                        ))
                        audio_public = gw.result.media_url
                        tts_engine = f"elevenlabs:{el_voice}"
                else:
                    gw = _run_async(gateway.generate_speech(
                        text, voice=voice, **gateway_call_kwargs(db_task_id, include_cost=False),
                    ))
                    audio_public = gw.result.media_url
                    tts_engine = f"elevenlabs:{voice}"
        elif audio_url:
            audio_public = _run_async(_to_public(audio_url, "audio/mpeg")) if not demo else audio_url

        if not demo and audio_public:
            try:
                from app.services.audio_prep import prepare_lipsync_audio_url
                _broadcast_progress(db_task_id, 22, "audio_prep", "正在均衡音量与清晰度...")
                norm_wav = prepare_lipsync_audio_url(audio_public)
                audio_public = _run_async(gateway.upload_public_url(
                    norm_wav.read_bytes(),
                    filename=f"ls_norm_{uuid.uuid4().hex[:8]}.wav",
                    content_type="audio/wav",
                ))
            except Exception as e:
                logger.warning("[lipsync] audio loudnorm skipped: %s", e)

        self.update_state(state="PROGRESS", meta={"current_stage": "face_detect", "progress": 30})
        _update_task(db_task_id, progress=30, current_stage="face_detect")
        _broadcast_progress(db_task_id, 30, "face_detect", "正在准备人物图片...")
        image_public = image_url if demo else _run_async(_to_public(image_url, "image/png"))

        self.update_state(state="PROGRESS", meta={"current_stage": "lipsync", "progress": 50})
        _update_task(db_task_id, progress=50, current_stage="lipsync")
        _broadcast_progress(db_task_id, 50, "lipsync", "正在生成唇形同步视频...")

        LIPSYNC_PROMPT = (
            "close-up talking head, mouth shapes precisely match the speech audio, "
            "natural jaw and lip motion, clear articulation, keep facial identity, "
            "subtle head motion, no dubbing mismatch"
        )

        if demo:
            v_url, thumb = render_demo_video(text or "talking avatar", "720x1280", 5, "portrait",
                                             _local_media_path(image_url) and image_url or None)
            output = persist_results([{
                "type": "video", "url": v_url, "thumbnail": thumb,
                "model": "demo-lipsync", "duration": 5,
                "mode": "ken_burns",
                "honesty": "offline_preview_not_lipsync",
            }])
        else:
            route_model = model or "kling-ai-avatar"
            model_id = None
            resolution = "720p"
            product_tier = "demo"
            if model and "/" in model:
                model_id = model
            elif model in ("lipsync-studio", "studio"):
                route_model = "lipsync-studio"
                product_tier = "studio"
            gw = _run_async(gateway.generate_lipsync(
                image_url=image_public,
                audio_url=audio_public,
                model=route_model,
                model_id=model_id,
                prompt=LIPSYNC_PROMPT,
                resolution=resolution,
                prefer_infinitalk=(product_tier == "studio"),
                **gateway_call_kwargs(db_task_id),
            ))
            res = gw.result
            _update_task(db_task_id, progress=85, current_stage="rendering")
            _broadcast_progress(db_task_id, 85, "rendering", "正在均衡成片音量...")
            final_url = res.media_url
            try:
                from app.services.audio_prep import boost_video_audio
                boosted = boost_video_audio(res.media_url)
                if boosted:
                    final_url = boosted
            except Exception as e:
                logger.warning("[lipsync] post loudnorm skipped: %s", e)
            output = persist_results([{
                "type": "video", "url": final_url,
                "thumbnail": res.thumbnail_url or "", "model": res.model, "duration": 5,
                "requested_model": model,
                "mode": "kling_avatar" if "kling" in (res.model or "") else "avatar_lipsync",
                "product_tier": product_tier,
                "resolution_intent": resolution,
                "tts_engine": tts_engine,
                "audio_prep": "loudnorm_-16LUFS",
                "gateway_provider": gw.provider_used,
                "gateway_fallback": gw.fallback_used,
            }])

        _update_task(
            db_task_id, status="completed", progress=100, current_stage="completed",
            completed_at=datetime.now(timezone.utc), results=json.dumps(output),
        )
        _broadcast_progress(db_task_id, 100, "completed", "唇形同步完成！")
        return {"status": "completed", "results": output}

    except Exception as e:
        logger.error(f"Lipsync failed: {e}", exc_info=True)
        _update_task(db_task_id, status="failed", progress=0, current_stage="failed",
                     error_message=str(e), completed_at=datetime.now(timezone.utc))
        return {"status": "failed", "error": str(e)}
