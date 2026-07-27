"""
Timeline Render Celery Task — unified with sync compose_final_video.

Async timeline render loads project settings (subtitle_track, export_preset,
narration) and delegates to the same ffmpeg composer as POST /timeline/compose.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from celery_app import app
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.tasks.task_db import update_task as _update_task

STORAGE_DIR = Path(os.getenv("STORAGE_LOCAL_PATH", os.getenv("STORAGE_PATH", "/tmp/aivideo-media")))


def _get_db_url_sync():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    if db_url.startswith("sqlite+aiosqlite"):
        db_url = db_url.replace("sqlite+aiosqlite", "sqlite")
    elif db_url.startswith("postgresql+asyncpg"):
        db_url = db_url.replace("postgresql+asyncpg", "postgresql")
    return db_url




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


def _parse_json_field(raw):
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}


@app.task(bind=True, max_retries=2, default_retry_delay=30)
def process_timeline_render(self, db_task_id: str, project_id: str):
    """Render timeline project via compose_final_video (same path as sync compose)."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if backend_dir not in os.getcwd():
        os.chdir(backend_dir)

    logger.info("Timeline render started: task=%s project=%s", db_task_id, project_id)

    project = None
    try:
        db_url = _get_db_url_sync()
        engine = create_engine(db_url)
        with Session(engine) as session:
            row = session.execute(
                text(
                    "SELECT name, clips, settings FROM timeline_projects WHERE project_id = :pid"
                ),
                {"pid": project_id},
            ).first()
            if row:
                clips_raw = _parse_json_field(row[1])
                settings = _parse_json_field(row[2])
                if not isinstance(clips_raw, list):
                    clips_raw = []
                project = {
                    "name": row[0],
                    "clips": clips_raw,
                    "settings": settings if isinstance(settings, dict) else {},
                }
        engine.dispose()
    except Exception as e:
        logger.warning("Cannot load timeline project from DB: %s", e)
        return _mark_failed(db_task_id, f"无法加载时间线项目: {e}")

    if not project:
        _update_task(db_task_id, status="failed", error_message=f"Project not found: {project_id}")
        return {"status": "failed", "error": "Project not found"}

    clips = project.get("clips", [])
    if not clips:
        _update_task(db_task_id, status="failed", error_message="No clips in project")
        return {"status": "failed", "error": "No clips"}

    settings = project.get("settings") or {}
    video_urls = [c.get("url", "") for c in clips if c.get("url")]
    if not video_urls:
        return _mark_failed(db_task_id, "时间线没有可合成的视频片段")

    from app.adapters.demo_provider import compose_final_video, _local_media_path

    missing = [u for u in video_urls if not _local_media_path(u)]
    if missing:
        return _mark_failed(
            db_task_id,
            f"时间线包含 {len(missing)} 个不可访问的片段，请先将素材保存到素材库后再合成",
        )

    try:
        output_dir = STORAGE_DIR / "renders"
        output_dir.mkdir(parents=True, exist_ok=True)

        _broadcast_progress(db_task_id, 15, "preparing", "准备合成管线...")
        _update_task(db_task_id, status="generating", progress=15, current_stage="preparing")

        clip_trims = [
            {
                "start": float(c.get("start", 0) or 0),
                "end": float(c.get("end", 0) or 0),
                "volume": float(c.get("volume", 1) or 1),
            }
            for c in clips
        ]
        transitions = [c.get("transition") or settings.get("transition") or "cut" for c in clips]
        subtitle_track = settings.get("subtitle_track") or []
        export_preset = settings.get("export_preset")
        narration_url = settings.get("narration_url")
        with_audio = settings.get("with_audio", True)

        _broadcast_progress(db_task_id, 40, "compositing", "合成最终视频（字幕+画幅）...")
        _update_task(db_task_id, progress=40, current_stage="compositing")

        final_url, poster = compose_final_video(
            video_urls,
            None,
            with_audio,
            narration_url,
            transitions=transitions,
            subtitle_track=subtitle_track,
            clip_trims=clip_trims,
            export_preset=export_preset,
        )

        _broadcast_progress(db_task_id, 90, "finalizing", "最终处理...")
        _update_task(db_task_id, progress=90, current_stage="finalizing")
        time.sleep(0.3)

        # compose_final_video writes under generated/; copy/symlink to renders/ for stable poll URL
        result_url = final_url
        try:
            src = _local_media_path(final_url)
            if src and src.exists():
                dest = output_dir / f"timeline_{db_task_id[:8]}.mp4"
                import shutil
                shutil.copy2(src, dest)
                result_url = f"/api/v1/media/renders/timeline_{db_task_id[:8]}.mp4"
        except Exception as copy_err:
            logger.warning("render copy fallback to compose url: %s", copy_err)

        total_duration = sum(
            max(0, float(c.get("end", 5)) - float(c.get("start", 0))) for c in clips
        )
        preset_label = export_preset or "source"
        results = {
            "project_id": project_id,
            "project_name": project.get("name", ""),
            "format": "mp4",
            "clips_count": len(clips),
            "duration_seconds": round(total_duration, 1),
            "export_preset": preset_label,
            "subtitle_cues": len(subtitle_track),
            "output_url": result_url,
            "thumbnail": poster,
        }

        _update_task(
            db_task_id,
            status="completed",
            progress=100,
            current_stage="completed",
            completed_at=datetime.now(timezone.utc),
            results=json.dumps(results),
            result_url=result_url,
            actual_cost=4,
        )
        _broadcast_progress(db_task_id, 100, "completed", "时间轴渲染完成！")
        logger.info("Timeline render completed: task=%s", db_task_id)
        return {"status": "completed", "result_url": result_url}

    except Exception as e:
        logger.error("Timeline render error: %s", e)
        return _mark_failed(db_task_id, str(e))


def _mark_failed(db_task_id: str, error_msg: str) -> dict:
    logger.error("Timeline render failed: %s: %s", db_task_id, error_msg)
    _update_task(
        db_task_id,
        status="failed",
        progress=0,
        current_stage="failed",
        error_message=error_msg,
        completed_at=datetime.now(timezone.utc),
    )
    _broadcast_progress(db_task_id, 0, "failed", error_msg)
    return {"status": "failed", "error": error_msg}
