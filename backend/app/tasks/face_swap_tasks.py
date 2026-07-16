"""Face Swap Celery task — verified i2i edit via google/nano-banana-edit."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from celery_app import app
from app.tasks.task_db import update_task as _update_task

logger = logging.getLogger(__name__)


def _broadcast_progress(task_id: str, progress: int, stage: str, message: str = ""):
    try:
        from app.api.websocket import broadcast_task_progress
        import asyncio

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
        refund_task_credits_sync(db_task_id, reason="face_swap_failed")
    except Exception as e:
        logger.warning("face_swap refund failed: %s", e)
    _broadcast_progress(db_task_id, 100, "failed", err[:120])
    return {"status": "failed", "error": err}


@app.task(
    bind=True,
    name="app.tasks.face_swap_tasks.process_face_swap",
    queue="image_q",
    max_retries=1,
    acks_late=True,
)
def process_face_swap(self, db_task_id: str, face_url: str, target_url: str, prompt: str = "") -> dict:
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if backend_dir not in os.getcwd():
        os.chdir(backend_dir)

    _update_task(
        db_task_id,
        status="generating",
        progress=15,
        current_stage="face_swap",
        started_at=datetime.now(timezone.utc),
    )
    _broadcast_progress(db_task_id, 15, "face_swap", "正在进行换脸合成…")

    from app.adapters.demo_provider import demo_mode_active
    if demo_mode_active():
        return _fail(db_task_id, "演示模式无法换脸：请配置 KIE_API_KEY 后使用真实 i2i 换脸。")

    try:
        from app.adapters.kie_adapter import KieAdapter
        import asyncio

        res = asyncio.run(KieAdapter().face_swap(
            face_url=face_url,
            target_url=target_url,
            prompt=prompt or None,
        ))
        url = getattr(res, "media_url", "") or ""
        if not url:
            return _fail(db_task_id, "换脸未返回图片 URL")
        from app.services.media_store import persist_results
        output = persist_results([{
            "type": "image",
            "url": url,
            "model": getattr(res, "model", "google/nano-banana-edit"),
            "cost": getattr(res, "cost", 0),
            "op": "face_swap",
            "mode": "i2i_edit",
            "honesty": (getattr(res, "meta", {}) or {}).get("honesty"),
        }])
        _update_task(
            db_task_id,
            status="completed",
            progress=100,
            current_stage="completed",
            completed_at=datetime.now(timezone.utc),
            results=json.dumps(output),
            result_url=output[0].get("url", "") if output else url,
            actual_cost=getattr(res, "cost", 0) or 0,
        )
        _broadcast_progress(db_task_id, 100, "completed", "换脸完成")
        return {"status": "completed", "results": output}
    except Exception as e:
        logger.exception("face_swap failed")
        return _fail(db_task_id, str(e))
