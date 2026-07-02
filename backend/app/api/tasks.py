"""
Task management API — query status, cancel, list.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db import get_db
from app.models.task import Task, TaskStatus

router = APIRouter()

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    current_stage: Optional[str]
    model: Optional[str]
    started_at: Optional[str]
    estimated_completion: Optional[str]

class TaskResultResponse(BaseModel):
    task_id: str
    status: str
    results: Optional[list]
    cost_credits: Optional[float]
    completed_at: Optional[str]
    error_message: Optional[str]

@router.get(
    "/{task_id}",
    summary="查询任务状态",
    description="轮询任务进度或在完成时获取结果",
)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    stmt = select(Task).where(Task.task_id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

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
    db: AsyncSession = Depends(get_db),
):
    from app.models.task import Task
    stmt = select(Task).order_by(Task.created_at.desc()).limit(limit).offset(offset)
    if status_filter:
        stmt = stmt.where(Task.status == status_filter)
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
        "total": len(tasks),
    }


@router.post("/{task_id}/cancel", summary="取消任务")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    stmt = select(Task).where(Task.task_id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in status: {task.status}")

    task.status = "cancelled"
    await db.flush()
    return {"task_id": task_id, "status": "cancelled"}
