"""
Motion Control API — 动作迁移/驱动: 图片 + 参考视频 → 动态视频

原生 Kling Motion Control（见 capabilities.motion_transfer）。
完整「表演驱动」请用 /performance（Motion + 可选 Lipsync）；≠ Runway Act-One。
Includes a canonical fixture sample library for input validation (not quality claims).
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.task import Task
from app.auth import resolve_user_id
from app.services.credits import deduct_credits, resolve_team_id
from app.tasks.motion_tasks import process_motion_task

logger = logging.getLogger(__name__)
router = APIRouter()

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "motion"
_SAMPLE_FILES = {
    "still.png": "image/png",
    "ref.mp4": "video/mp4",
}


# ─── Models ────────────────────────────────────────────

class MotionRequest(BaseModel):
    """动作迁移请求"""
    image_url: str = Field(..., description="需要驱动的静态图片URL")
    video_url: str = Field(..., description="参考动作视频URL")
    prompt: Optional[str] = Field(default=None, max_length=2000, description="可选提示词，描述期望效果")
    style: Optional[str] = Field(default=None, description="风格偏好: realistic | anime | cartoon")
    tier: str = Field(default="demo", description="demo | studio — Studio 需 Personal+ 套餐")
    voice_text: Optional[str] = Field(
        default=None,
        max_length=500,
        description="可选：生成后附加 TTS 旁白（Yapper Motion + Voice 轻量对标，非变声引擎）",
    )
    voice: Optional[str] = Field(default="Rachel", description="TTS 音色")


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
        "tier": tier,
    }
    if req.voice_text and req.voice_text.strip():
        params["voice_text"] = req.voice_text.strip()
        params["voice"] = (req.voice or "Rachel").strip() or "Rachel"

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


@router.get("/motion/samples", summary="Motion 样片库目录（输入资产，非质量对标）")
async def list_motion_samples():
    """Canonical fixture pairs for loading sample inputs in the Motion UI / harness.

    Honesty: these are *inputs* for pipeline validation — not Act-One quality refs.
    """
    still = _FIXTURE_DIR / "still.png"
    ref = _FIXTURE_DIR / "ref.mp4"
    available = still.is_file() and ref.is_file()
    samples = []
    if available:
        samples.append({
            "id": "canonical-v1",
            "title": "标准输入样片对",
            "desc": "正面人物静帧 + 4s 参考动作（≥3s，满足 Kling Motion Control）",
            "image_path": "/api/v1/motion/samples/canonical-v1/still.png",
            "video_path": "/api/v1/motion/samples/canonical-v1/ref.mp4",
            "style": "realistic",
            "prompt": "自然肢体迁移，全身动作，柔和光影",
            "duration_seconds": 4,
            "note": "原生 SKU 输入样片（kling-3.0/motion-control）；非 Runway Act-One 质量对标",
        })
    return {
        "available": available,
        "mode": "native",
        "sku": "kling-3.0/motion-control",
        "fixture_dir": str(_FIXTURE_DIR),
        "samples": samples,
        "live_gate": "MOTION_FIXTURE_LIVE=1",
    }


@router.get("/motion/samples/{sample_id}/{filename}", summary="下载 Motion 样片文件")
async def get_motion_sample_file(sample_id: str, filename: str):
    if sample_id != "canonical-v1":
        raise HTTPException(status_code=404, detail="样片不存在")
    if filename not in _SAMPLE_FILES:
        raise HTTPException(status_code=404, detail="文件不存在")
    path = _FIXTURE_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="样片文件缺失，请运行 scripts/generate_motion_fixtures.py")
    return FileResponse(path, media_type=_SAMPLE_FILES[filename], filename=filename)
