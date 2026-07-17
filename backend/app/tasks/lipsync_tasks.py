"""
Lipsync Celery task — processes image + audio to create talking video.
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from celery_app import app
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.media_store import persist_results

logger = logging.getLogger(__name__)

from app.tasks.task_db import update_task as _update_task




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

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_send())
        finally:
            loop.close()
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

    # Stage 1: Init
    self.update_state(state="PROGRESS", meta={"current_stage": "lipsync_init", "progress": 5})
    _update_task(db_task_id, status="generating", progress=5, current_stage="lipsync_init",
                 started_at=datetime.now(timezone.utc))
    _broadcast_progress(db_task_id, 5, "lipsync_init", "正在加载参考图片...")

    try:
        from app.adapters.demo_provider import demo_mode_active, _local_media_path
        from app.adapters.kie_adapter import KieAdapter

        def _to_public(url: str, default_ct: str) -> str:
            """Ensure a URL is publicly fetchable by KIE (upload local files)."""
            if not url:
                return url
            if url.startswith("http://") or url.startswith("https://"):
                # local backend URLs aren't reachable by KIE → upload
                if "/api/v1/media" not in url and "localhost" not in url and "127.0.0.1" not in url:
                    return url
            p = _local_media_path(url)
            if not p:
                return url
            with open(p, "rb") as f:
                data = f.read()
            ext = os.path.splitext(p)[1].lstrip(".") or ("png" if "image" in default_ct else "mp3")
            ct = f"image/{ext}" if default_ct.startswith("image") else f"audio/{ext}"
            return asyncio.run(KieAdapter().upload_public_url(
                data, filename=f"ls_{uuid.uuid4().hex[:8]}.{ext}", content_type=ct))

        demo = demo_mode_active()
        tts_engine = None

        # Stage 2: voiceover — real TTS if text given
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
                # Prefer real Neural TTS for Azure-style ids (matches FE labels;
                # ElevenLabs remap caused 「配音感」+ weaker Chinese phonemes).
                if is_azure_neural_voice(voice):
                    try:
                        wav_bytes, used_voice = asyncio.run(synthesize_speech_edge(text, voice))
                        audio_public = asyncio.run(KieAdapter().upload_public_url(
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
                        res = asyncio.run(KieAdapter().generate_speech(
                            text, voice=el_voice, language_code="zh" if voice.startswith("zh-") else None,
                        ))
                        audio_public = res.media_url
                        tts_engine = f"elevenlabs:{el_voice}"
                else:
                    res = asyncio.run(KieAdapter().generate_speech(text, voice=voice))
                    audio_public = res.media_url
                    tts_engine = f"elevenlabs:{voice}"
        elif audio_url:
            audio_public = _to_public(audio_url, "audio/mpeg") if not demo else audio_url

        # Stage 2b: loudnorm driving audio (−16 LUFS) before lip-sync
        if not demo and audio_public:
            try:
                from app.services.audio_prep import prepare_lipsync_audio_url
                _broadcast_progress(db_task_id, 22, "audio_prep", "正在均衡音量与清晰度...")
                norm_wav = prepare_lipsync_audio_url(audio_public)
                audio_public = asyncio.run(KieAdapter().upload_public_url(
                    norm_wav.read_bytes(),
                    filename=f"ls_norm_{uuid.uuid4().hex[:8]}.wav",
                    content_type="audio/wav",
                ))
            except Exception as e:
                logger.warning("[lipsync] audio loudnorm skipped: %s", e)

        # Stage 3: make the portrait publicly reachable by KIE
        self.update_state(state="PROGRESS", meta={"current_stage": "face_detect", "progress": 30})
        _update_task(db_task_id, progress=30, current_stage="face_detect")
        _broadcast_progress(db_task_id, 30, "face_detect", "正在准备人物图片...")
        image_public = image_url if demo else _to_public(image_url, "image/png")

        # Stage 4/5: real lip-sync generation
        self.update_state(state="PROGRESS", meta={"current_stage": "lipsync", "progress": 50})
        _update_task(db_task_id, progress=50, current_stage="lipsync")
        _broadcast_progress(db_task_id, 50, "lipsync", "正在生成唇形同步视频...")

        LIPSYNC_PROMPT = (
            "close-up talking head, mouth shapes precisely match the speech audio, "
            "natural jaw and lip motion, clear articulation, keep facial identity, "
            "subtle head motion, no dubbing mismatch"
        )

        if demo:
            from app.adapters.demo_provider import render_demo_video
            v_url, thumb = render_demo_video(text or "talking avatar", "720x1280", 5, "portrait",
                                             _local_media_path(image_url) and image_url or None)
            # Honest mode tag: Ken Burns is NOT lip-sync / digital human.
            output = persist_results([{
                "type": "video", "url": v_url, "thumbnail": thumb,
                "model": "demo-lipsync", "duration": 5,
                "mode": "ken_burns",
                "honesty": "offline_preview_not_lipsync",
            }])
        else:
            # Studio: prefer infinitalk@720p when available; Demo stays on Kling.
            # Explicit KIE ids (contain "/") are honored as-is.
            model_id = "kling/ai-avatar-pro"
            resolution = "720p"
            product_tier = "demo"
            if model and "/" in model:
                model_id = model
            elif model in ("lipsync-studio", "studio"):
                model_id = "infinitalk/from-audio"
                resolution = "720p"
                product_tier = "studio"
            res = asyncio.run(KieAdapter().generate_lipsync(
                image_url=image_public, audio_url=audio_public,
                prompt=LIPSYNC_PROMPT,
                model_id=model_id,
                resolution=resolution,
            ))
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
