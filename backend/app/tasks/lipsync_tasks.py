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


def _update_task(db_task_id: str, **kwargs):
    db_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    if db_url.startswith("sqlite+aiosqlite"):
        db_url = db_url.replace("sqlite+aiosqlite", "sqlite")
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

    # Stage 2: TTS (if text provided)
    audio_url_final = audio_url
    if text and not audio_url:
        self.update_state(state="PROGRESS", meta={"current_stage": "tts", "progress": 15})
        _update_task(db_task_id, progress=15, current_stage="tts")
        _broadcast_progress(db_task_id, 15, "tts", f"正在合成语音 ({voice_id})...")
        
        # Simulate TTS — in production, call Azure/Edge TTS API
        audio_url_final = f"/uploads/lipsync/tts_{uuid.uuid4().hex[:8]}.mp3"
        logger.info(f"[Lipsync] TTS: text={text[:50]}... → voice={voice_id}")

    # Stage 3: Face detection
    self.update_state(state="PROGRESS", meta={"current_stage": "face_detect", "progress": 30})
    _update_task(db_task_id, progress=30, current_stage="face_detect")
    _broadcast_progress(db_task_id, 30, "face_detect", "正在分析面部特征...")

    # Stage 4: Lipsync generation
    self.update_state(state="PROGRESS", meta={"current_stage": "lipsync", "progress": 50})
    _update_task(db_task_id, progress=50, current_stage="lipsync")
    _broadcast_progress(db_task_id, 50, "lipsync", "正在生成唇形同步动画...")

    # Stage 5: Rendering
    self.update_state(state="PROGRESS", meta={"current_stage": "rendering", "progress": 75})
    _update_task(db_task_id, progress=75, current_stage="rendering")
    _broadcast_progress(db_task_id, 75, "rendering", "正在渲染最终视频...")

    try:
        # In production: call actual lipsync API (e.g., D-ID, HeyGen, SadTalker)
        # For now, return a mock result with the original image as a placeholder
        output_url = image_url  # Placeholder — would be actual video URL

        output = persist_results([{
            "type": "video",
            "url": output_url,
            "thumbnail": image_url,
            "model": model or "lipsync-v1",
            "duration": 5,
        }])
        _update_task(
            db_task_id,
            status="completed",
            progress=100,
            current_stage="completed",
            completed_at=datetime.now(timezone.utc),
            results=json.dumps(output),
        )
        _broadcast_progress(db_task_id, 100, "completed", "唇形同步完成！")

        return {
            "status": "completed",
            "results": [{"type": "video", "url": output_url}],
        }

    except Exception as e:
        logger.error(f"Lipsync failed: {e}")
        _update_task(db_task_id, status="failed", progress=0, current_stage="failed",
                     error_message=str(e), completed_at=datetime.now(timezone.utc))
        return {"status": "failed", "error": str(e)}
