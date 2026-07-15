"""
Motion Control API — 动作迁移/驱动: 图片 + 参考视频 → 动态视频

对标 Runway Act-One / Vidu 动作驱动功能。
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.task import Task
from app.auth import resolve_user_id
from app.services.credits import deduct_credits, resolve_team_id
from app.tasks.motion_tasks import process_motion_task

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Models ────────────────────────────────────────────

class MotionRequest(BaseModel):
    """动作迁移请求"""
    image_url: str = Field(..., description="需要驱动的静态图片URL")
    video_url: str = Field(..., description="参考动作视频URL")
    prompt: Optional[str] = Field(default=None, max_length=2000, description="可选提示词，描述期望效果")
    style: Optional[str] = Field(default=None, description="风格偏好: realistic | anime | cartoon")
    tier: str = Field(default="demo", description="demo | studio — Studio 需 Personal+ 套餐")


class MotionResponse(BaseModel):
    task_id: str
    status: str = "queued"
    estimated_time_seconds: int = 90
    estimated_cost_credits: int = 6
    poll_url: str = ""


# ─── Helpers ───────────────────────────────────────────

MOTION_COST = 6  # credits
MOTION_ESTIMATED_TIME = 90  # seconds


# ─── Endpoints ─────────────────────────────────────────

@router.post(
    "/motion",
    response_model=MotionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="提交动作迁移任务",
    description="上传一张静态图片和一段参考动作视频，AI 将参考视频中的动作迁移到静态图片上，生成动态视频。",
)
async def submit_motion(
    req: MotionRequest,
    request: Request,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    动作迁移 (Motion Control):
    
    - **image_url**: 静态图片URL（人物/角色照片）
    - **video_url**: 参考动作视频URL（驱动动作来源）
    - **prompt**: 可选提示词，描述期望的效果
    - **style**: 风格偏好 (realistic / anime / cartoon)
    
    返回 task_id，可通过 `/api/v1/tasks/{task_id}` 查询进度。
    """
    task_id = str(uuid.uuid4())

    # Validate URLs
    if not req.image_url.strip():
        raise HTTPException(status_code=400, detail="请提供静态图片URL (image_url)")
    if not req.video_url.strip():
        raise HTTPException(status_code=400, detail="请提供参考动作视频URL (video_url)")

    from app.services.moderation import check_prompt
    from app.services.entitlements import motion_cost, require_studio_tier
    from app.models.user import User
    from sqlalchemy import select as sa_select

    if req.prompt:
        m = check_prompt(req.prompt)
        if not m.allowed:
            raise HTTPException(status_code=400, detail=m.reason)

    tier = (req.tier or "demo").strip().lower()
    if tier not in ("demo", "studio"):
        raise HTTPException(status_code=400, detail="tier 必须是 demo 或 studio")
    u = (await db.execute(sa_select(User).where(User.id == user_id))).scalar_one_or_none()
    if tier == "studio":
        require_studio_tier(u.role if u else "guest", "Motion Studio")
    cost = motion_cost(tier)
    team_id = resolve_team_id(request)
    model = "motion-control" if tier == "demo" else "motion-control-studio"

    # Build parameters
    params = {
        "image_url": req.image_url,
        "video_url": req.video_url,
        "style": req.style,
    }

    # Create Task record
    task = Task(
        task_id=task_id,
        user_id=user_id,
        prompt=req.prompt or "",
        media_type="video",
        quality="balanced",
        requested_model=model,
        selected_model=model,
        parameters=params,
        estimated_cost=cost,
        status="queued",
    )
    db.add(task)
    await db.flush()

    # Check and deduct credits (personal or team pool via X-Team-Id)
    credits_ok = await deduct_credits(
        db=db, user_id=user_id, cost=cost,
        task_id=task_id, model=model, team_id=team_id,
        description=f"Motion control task {task_id[:8]}...",
    )
    if not credits_ok:
        task.status = "failed"
        task.error_message = "积分不足，请充值后重试"
        await db.flush()
        return MotionResponse(
            task_id=task_id,
            status="failed",
            estimated_time_seconds=0,
            estimated_cost_credits=cost,
            poll_url=f"/api/v1/tasks/{task_id}",
        )

    task.status = "queued"

    # Dispatch Celery task
    celery_task = process_motion_task.delay(
        db_task_id=task_id,
        model=model,
        prompt=req.prompt or "",
        params=params,
    )

    task.celery_task_id = celery_task.id
    task.status = "queued"
    task.estimated_completion = datetime.now(timezone.utc) + timedelta(seconds=MOTION_ESTIMATED_TIME)
    await db.flush()

    logger.info(f"Motion task dispatched: {task_id}, celery_id={celery_task.id}")

    return MotionResponse(
        task_id=task_id,
        status="queued",
        estimated_time_seconds=MOTION_ESTIMATED_TIME,
        estimated_cost_credits=cost,
        poll_url=f"/api/v1/tasks/{task_id}",
    )
