"""
Task management API — query status, cancel, retry, list.
Scoped by authenticated user (or shared guest account when not logged in).
"""
import json as _json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db import get_db
from app.models.task import Task
from app.auth import resolve_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


class TaskResultResponse(BaseModel):
    task_id: str
    status: str
    results: Optional[list] = None
    result_url: Optional[str] = None
    cost_credits: Optional[float] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    webhook: Optional[dict] = None
    sla: Optional[dict] = None


def _coerce_results(raw) -> Optional[list]:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = _json.loads(raw)
        except Exception:
            return None
    return raw if isinstance(raw, list) else None


def _parse_params(raw) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw:
        try:
            parsed = _json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _first_result_url(results: Optional[list], request: Request) -> Optional[str]:
    if not results:
        return None
    first = results[0] if isinstance(results[0], dict) else {}
    url = first.get("url") or first.get("media_url") or ""
    if not url:
        return None
    if url.startswith("/"):
        return str(request.base_url).rstrip("/") + url
    return url


def _sla_payload(task: Task, params: dict[str, Any], *, queue_position: int | None = None) -> dict[str, Any]:
    refund: dict[str, Any] = {"refunded": False}
    if params.get("credits_refunded"):
        refund = {
            "refunded": True,
            "amount": params.get("refund_amount"),
            "reason": params.get("refund_reason"),
            "at": params.get("refund_at"),
        }
    elif task.status in ("failed", "cancelled"):
        refund = {
            "refunded": False,
            "note": "失败/取消任务积分将自动幂等退还（通常数秒内到账）",
        }

    hints: list[str] = []
    if queue_position is not None and queue_position > 0:
        hints.append(f"排队中：前方约 {queue_position} 个任务")
    elif task.status == "queued":
        hints.append("排队中，即将开始生成")
    elif task.status == "generating":
        pct = task.progress or 0
        hints.append(f"生成中 {pct}%" if pct else "生成中，请稍候")
    if task.estimated_completion and task.status not in ("completed", "failed", "cancelled"):
        hints.append("ETA 为估算值，受模型队列影响")

    webhook = params.get("webhook") if isinstance(params.get("webhook"), dict) else None
    wh_note = None
    if task.webhook_url:
        if webhook and webhook.get("delivered"):
            wh_note = "Webhook 已投递"
        elif webhook and webhook.get("delivered") is False:
            wh_note = f"Webhook 投递失败：{(webhook.get('reason') or webhook.get('error') or '')[:80]}"
        elif task.status in ("completed", "failed", "cancelled"):
            wh_note = "Webhook 处理中或尚未配置签名密钥"

    return {
        "refund": refund,
        "webhook": webhook,
        "webhook_note": wh_note,
        "hints": hints,
        "retryable": task.status in ("failed", "cancelled") and (task.media_type in ("image", "video")),
    }


async def _owned_task(db: AsyncSession, task_id: str, user_id: int) -> Task:
    result = await db.execute(select(Task).where(Task.task_id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    return task


async def _queue_position(db: AsyncSession, task: Task, user_id: int) -> int | None:
    if task.status != "queued":
        return None
    ahead = (await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id,
            Task.status == "queued",
            Task.created_at < task.created_at,
        )
    )).scalar() or 0
    return int(ahead)


@router.get(
    "/{task_id}",
    summary="查询任务状态",
    description="轮询任务进度或在完成时获取结果（仅本人可见）",
)
async def get_task_status(
    task_id: str,
    request: Request,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    task = await _owned_task(db, task_id, user_id)
    params = _parse_params(task.parameters)
    queue_position = await _queue_position(db, task, user_id)

    if task.status in ("completed", "failed", "cancelled"):
        results = _coerce_results(task.results)
        return TaskResultResponse(
            task_id=task.task_id,
            status=task.status,
            results=results,
            result_url=_first_result_url(results, request),
            cost_credits=task.actual_cost,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            error_message=task.error_message,
            webhook=params.get("webhook") if isinstance(params.get("webhook"), dict) else None,
            sla=_sla_payload(task, params, queue_position=queue_position),
        )

    return {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "current_stage": task.current_stage,
        "queue_position": queue_position,
        "model": task.selected_model,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "estimated_completion": task.estimated_completion.isoformat() if task.estimated_completion else None,
        "sla": _sla_payload(task, params, queue_position=queue_position),
    }


@router.get("/", summary="用户任务列表")
async def list_tasks(
    status_filter: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0),
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    base = select(Task).where(Task.user_id == user_id)
    if status_filter:
        base = base.where(Task.status == status_filter)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    stmt = base.order_by(Task.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    return {
        "tasks": [
            {
                "task_id": t.task_id,
                "prompt": t.prompt[:80] + ("..." if len(t.prompt) > 80 else ""),
                "full_prompt": t.prompt,
                "status": t.status,
                "media_type": t.media_type,
                "model": t.selected_model,
                "progress": t.progress,
                "current_stage": t.current_stage,
                "results": t.results,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "error_message": t.error_message,
                "resolution": (_parse_params(t.parameters).get("resolution") or "1080x1080"),
                "sla": _sla_payload(t, _parse_params(t.parameters)),
            }
            for t in tasks
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{task_id}/retry", summary="重试失败/已取消的生成任务")
async def retry_task(
    task_id: str,
    request: Request,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Re-dispatch image/video generation with the same prompt + parameters (new task_id)."""
    source = await _owned_task(db, task_id, user_id)
    if source.status not in ("failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"只能重试失败或已取消的任务，当前: {source.status}")
    media = (source.media_type or "image").lower()
    if media not in ("image", "video"):
        raise HTTPException(status_code=400, detail="此任务类型暂不支持一键重试，请从对应工具页重新提交")

    params = _parse_params(source.parameters)
    model = source.selected_model or source.requested_model or "auto"
    cost = int(source.estimated_cost or source.actual_cost or 1)
    new_id = uuid.uuid4().hex
    new_params = dict(params)
    new_params["retry_from"] = source.task_id

    new_task = Task(
        task_id=new_id,
        user_id=user_id,
        prompt=source.prompt,
        media_type=media,
        quality=source.quality or "balanced",
        requested_model=source.requested_model or model,
        selected_model=model,
        fallback_model=source.fallback_model,
        parameters=new_params,
        estimated_cost=float(cost),
        status="queued",
        webhook_url=source.webhook_url,
    )
    db.add(new_task)
    await db.flush()

    from app.services.credits import deduct_credits, resolve_team_id, refund_task_credits

    team_id = resolve_team_id(request)
    credits_ok = await deduct_credits(
        db=db, user_id=user_id, cost=cost, task_id=new_id, model=model, team_id=team_id,
    )
    if not credits_ok:
        new_task.status = "failed"
        new_task.error_message = "积分不足，请充值后重试"
        await db.flush()
        raise HTTPException(status_code=402, detail="积分不足，请充值后重试")

    celery_params = {
        "resolution": params.get("resolution", "1080x1080"),
        "duration": params.get("duration") or 5,
        "count": params.get("count") or 1,
        "style": params.get("style"),
        "seed": params.get("seed"),
        "omni": bool(params.get("omni")),
        "generate_audio": bool(params.get("generate_audio")),
    }
    for key in ("negative_prompt", "image_url", "reference_images", "reference_videos", "reference_audios",
                "post_lipsync", "lipsync_text", "lipsync_voice_id"):
        if params.get(key) is not None:
            celery_params[key] = params[key]

    try:
        if media == "image":
            from app.tasks.image_tasks import generate_image_task
            celery_task = generate_image_task.delay(
                db_task_id=new_id, model=model, prompt=source.prompt, params=celery_params,
            )
        else:
            from app.tasks.video_tasks import generate_video_task
            celery_task = generate_video_task.delay(
                db_task_id=new_id, model=model, prompt=source.prompt, params=celery_params,
            )
    except Exception as e:
        logger.error("retry dispatch failed %s -> %s: %s", task_id, new_id, e)
        new_task.status = "failed"
        new_task.error_message = f"重试调度失败: {e}"
        await refund_task_credits(db, new_id, reason="retry_dispatch_failed")
        await db.flush()
        raise HTTPException(status_code=500, detail=f"重试调度失败: {e}")

    new_task.celery_task_id = celery_task.id
    est_s = 60 if media == "image" else 120
    new_task.estimated_completion = datetime.now(timezone.utc) + timedelta(seconds=est_s)
    await db.flush()

    return {
        "task_id": new_id,
        "status": "queued",
        "retry_from": source.task_id,
        "poll_url": f"/api/v1/tasks/{new_id}",
        "estimated_cost_credits": cost,
    }


@router.post("/{task_id}/cancel", summary="取消任务")
async def cancel_task(
    task_id: str,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    task = await _owned_task(db, task_id, user_id)
    if task.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in status: {task.status}")

    revoked = False
    if task.celery_task_id:
        try:
            from celery_app import app as celery_app
            celery_app.control.revoke(task.celery_task_id, terminate=True, signal="SIGTERM")
            revoked = True
        except Exception:
            revoked = False

    try:
        from app.services.credits import refund_task_credits
        await refund_task_credits(db, task_id, reason="cancelled")
    except Exception:
        pass

    task.status = "cancelled"
    task.current_stage = "cancelled"
    await db.flush()
    return {"task_id": task_id, "status": "cancelled", "revoked": revoked}
