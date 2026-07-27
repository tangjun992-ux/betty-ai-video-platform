"""Performance Drive — Motion Control + optional Lipsync talk.

Honest product boundary: ≠ Runway Act-One (no proprietary performance encoder).
Betty chains verified native Kling Motion + talking avatar lipsync when audio/text provided.
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import resolve_user_id
from app.db import get_db
from app.models.task import Task
from app.models.user import User
from app.services.credits import deduct_credits, resolve_team_id
from app.services.entitlements import motion_cost, lipsync_cost, require_studio_tier
from celery_app import app as celery_app

logger = logging.getLogger(__name__)
router = APIRouter()


class PerformanceRequest(BaseModel):
    image_url: str = Field(..., description="角色静帧")
    video_url: str = Field(..., description="参考动作 / 表演视频")
    prompt: Optional[str] = Field(default=None, max_length=2000)
    style: Optional[str] = None
    tier: str = Field(default="demo", description="demo | studio")
    # Optional talk stage (lipsync on source still)
    voice_text: Optional[str] = Field(default=None, max_length=500)
    audio_url: Optional[str] = Field(default=None)
    voice: Optional[str] = Field(default="Rachel")
    with_talk: bool = Field(
        default=False,
        description="True 时在 Motion 后追加 Lipsync 说话片段（源静帧+音频/文案）",
    )


class PerformanceResponse(BaseModel):
    task_id: str
    status: str = "queued"
    estimated_cost_credits: int
    mode: str = "motion_plus_optional_lipsync"
    honesty: str = (
        "Betty Performance Drive = 原生 Kling Motion Control + 可选 Lipsync；"
        "不是 Runway Act-One 表演编码器。"
    )


@router.post(
    "/performance",
    response_model=PerformanceResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Performance Drive（Motion + 可选口播）",
)
async def submit_performance(
    req: PerformanceRequest,
    request: Request,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not req.image_url.strip() or not req.video_url.strip():
        raise HTTPException(status_code=400, detail="需要 image_url 与 video_url")

    tier = (req.tier or "demo").strip().lower()
    if tier not in ("demo", "studio"):
        raise HTTPException(status_code=400, detail="tier 必须是 demo 或 studio")

    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if tier == "studio":
        require_studio_tier(u.role if u else "guest", "Performance Studio")

    with_talk = bool(req.with_talk or (req.voice_text or "").strip() or (req.audio_url or "").strip())
    if with_talk and not ((req.voice_text or "").strip() or (req.audio_url or "").strip()):
        raise HTTPException(status_code=400, detail="with_talk 需要 voice_text 或 audio_url")

    cost = motion_cost(tier) + (lipsync_cost(tier) if with_talk else 0)
    task_id = str(uuid.uuid4())
    team_id = resolve_team_id(request)
    model = "performance-drive" if tier == "demo" else "performance-drive-studio"

    if not await deduct_credits(
        db, user_id, cost, task_id, model,
        team_id=team_id, description=f"Performance {task_id[:8]}",
    ):
        raise HTTPException(status_code=402, detail=f"积分不足，需要 {cost} 积分")

    params = {
        "image_url": req.image_url,
        "video_url": req.video_url,
        "prompt": req.prompt,
        "style": req.style,
        "tier": tier,
        "with_talk": with_talk,
        "voice_text": (req.voice_text or "").strip() or None,
        "audio_url": (req.audio_url or "").strip() or None,
        "voice": req.voice or "Rachel",
        "mode": "motion_plus_optional_lipsync",
        "honesty": "≠ Runway Act-One",
    }
    task = Task(
        task_id=task_id,
        user_id=user_id,
        prompt=req.prompt or "performance drive",
        media_type="video",
        requested_model=model,
        selected_model="kling-3.0/motion-control",
        parameters=params,
        estimated_cost=cost,
        status="queued",
    )
    db.add(task)
    await db.commit()

    celery_app.send_task(
        "app.tasks.performance_tasks.process_performance",
        args=[task_id, params],
        queue="video_q",
    )
    return PerformanceResponse(task_id=task_id, estimated_cost_credits=cost)
