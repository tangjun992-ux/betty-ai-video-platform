"""
Task management API — query status, cancel, list.
Scoped by authenticated user (or shared guest account when not logged in).
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db import get_db
from app.models.task import Task
from app.auth import resolve_user_id

router = APIRouter()


class TaskResultResponse(BaseModel):
    task_id: str
    status: str
    results: Optional[list]
    cost_credits: Optional[float]
    completed_at: Optional[str]
    error_message: Optional[str]


async def _owned_task(db: AsyncSession, task_id: str, user_id: int) -> Task:
    result = await db.execute(select(Task).where(Task.task_id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    return task


@router.get(
    "/{task_id}",
    summary="查询任务状态",
    description="轮询任务进度或在完成时获取结果（仅本人可见）",
)
async def get_task_status(
    task_id: str,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    task = await _owned_task(db, task_id, user_id)

    if task.status in ("completed", "failed", "cancelled"):
        return TaskResultResponse(
            task_id=task.task_id,
            status=task.status,
            results=task.results,
            cost_credits=task.actual_cost,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            error_message=task.error_message,
        )

    return {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "current_stage": task.current_stage,
        "model": task.selected_model,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "estimated_completion": task.estimated_completion.isoformat() if task.estimated_completion else None,
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
                "resolution": t.parameters.get("resolution", "1080x1080") if t.parameters else "1080x1080",
            }
            for t in tasks
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
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

    task.status = "cancelled"
    await db.flush()
    return {"task_id": task_id, "status": "cancelled"}
