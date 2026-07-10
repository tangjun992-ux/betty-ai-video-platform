"""
Director API — 导演式编排端点 (对标 yapper Agent)
  POST /director/plan  → 生成创作计划 (用户先看导演方案)
  POST /director/run   → 执行计划，产出多资产 (默认 DRY_RUN)
"""
import json
import os
import uuid
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.director import planner, DirectorExecutor, DirectorPlanner, plan_from_dict, refine_plan, DirectorStep
from app.db import get_db
from app.models.director_session import DirectorSession

router = APIRouter()


def _dry_run_default() -> bool:
    val = os.getenv("DIRECTOR_DRY_RUN") or os.getenv("DRY_RUN") or ""
    if val:
        return val.lower() in ("1", "true", "yes", "on")
    try:
        from app.config import settings  # type: ignore
        return bool(getattr(settings, "LOCAL_MODE", False) or getattr(settings, "DRY_RUN", False))
    except Exception:
        return True  # 安全默认：不真实烧钱


class PlanRequest(BaseModel):
    brief: str = Field(..., description="一句话创作意图，例如：做一个30秒的咖啡产品宣传片")
    has_ref_image: bool = Field(default=False)
    duration: int = Field(default=5, ge=1, le=60)
    ref_image_url: Optional[str] = Field(default=None, description="参考图 URL（真正参与图生视频/关键帧）")


class RunRequest(PlanRequest):
    dry_run: bool | None = Field(default=None, description="留空则按服务端默认")
    plan: Optional[dict] = Field(default=None, description="可选：客户端已编辑的计划，优先于 brief 自动规划")


class StepRerunRequest(BaseModel):
    step: dict = Field(..., description="要重新执行的单个步骤")
    dry_run: bool | None = None


def _resolve_plan(req: RunRequest):
    """Use the (edited) client plan when provided, else auto-plan from the brief."""
    if req.plan and req.plan.get("steps"):
        return plan_from_dict(req.plan)
    return DirectorPlanner().plan(req.brief, has_ref_image=req.has_ref_image,
                                  duration=req.duration, ref_image_url=req.ref_image_url)


@router.post("/plan", summary="生成导演式创作计划")
async def make_plan(req: PlanRequest):
    plan = planner.plan(req.brief, has_ref_image=req.has_ref_image,
                        duration=req.duration, ref_image_url=req.ref_image_url)
    return plan.to_dict()


class RefineRequest(BaseModel):
    plan: dict = Field(..., description="当前计划")
    directive: str = Field(..., description="导演指令，如：把第2镜改暖一点 / 加一个镜头 / 换成 Veo 3.1 / 竖屏")


class IdeateRequest(BaseModel):
    brief: str = Field(..., min_length=1)


@router.post("/ideate", summary="帮我构思：从一句话发散多个创意方向")
async def ideate(req: IdeateRequest):
    """Expand a rough idea into several distinct creative concepts to pick from
    (对标 yapper 'Help Ideate')."""
    b = req.brief.strip()
    angles = [
        ("电影感大片", f"{b}，电影级运镜与调色，史诗氛围，宽银幕构图"),
        ("高能快剪", f"{b}，快节奏踩点剪辑，动感转场，强视觉冲击，竖屏"),
        ("情绪治愈", f"{b}，柔和自然光，舒缓节奏，温暖治愈氛围"),
        ("悬念钩子", f"{b}，强钩子开场加剧情反转，抓住前 3 秒注意力，竖屏"),
        ("高级质感", f"{b}，极简高级质感，精致布光，商业大片级细节"),
    ]
    return {"concepts": [{"title": t, "brief": br} for t, br in angles]}


@router.post("/refine", summary="对话式导演：用自然语言迭代计划")
async def refine(req: RefineRequest):
    plan = plan_from_dict(req.plan)
    updated, changes = refine_plan(plan, req.directive)
    return {"plan": updated.to_dict(), "changes": changes}


@router.post("/run", summary="执行导演计划，产出多资产 (非流式)")
async def run_plan(req: RunRequest):
    plan = _resolve_plan(req)
    dry = _dry_run_default() if req.dry_run is None else req.dry_run
    executor = DirectorExecutor(dry_run=dry)
    return await executor.run(plan)


@router.post("/run/stream", summary="流式执行导演计划 (SSE)")
async def run_plan_stream(req: RunRequest):
    """Stream per-step events (SSE). Frontend reads the body incrementally to
    animate the director's progress and surface assets as each shot completes."""
    plan = _resolve_plan(req)
    dry = _dry_run_default() if req.dry_run is None else req.dry_run
    executor = DirectorExecutor(dry_run=dry)

    async def gen():
        # Emit the (resolved) plan first so the client can render steps immediately.
        yield f"data: {json.dumps({'type': 'plan', 'plan': plan.to_dict()}, ensure_ascii=False)}\n\n"
        try:
            async for ev in executor.run_stream(plan):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as e:  # pragma: no cover
            yield f"data: {json.dumps({'type': 'step_error', 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive",
    })


@router.post("/run/async", summary="异步执行导演计划 (后台任务, 避免长视频阻塞)")
async def run_plan_async(req: RunRequest):
    """Kick off the plan in a Celery task; poll GET /director/progress/<job_id>.
    Use this for real multi-shot films (6 shots × ~150s) that would time out over
    a live connection."""
    plan = _resolve_plan(req)
    dry = _dry_run_default() if req.dry_run is None else req.dry_run
    job_id = uuid.uuid4().hex
    from app.tasks.director_tasks import run_director, write_progress
    # Seed a 'queued' snapshot so the first poll always returns something.
    write_progress(job_id, {
        "job_id": job_id, "status": "queued", "done": False, "dry_run": dry,
        "plan": plan.to_dict(),
        "steps": [{"id": s.id, "status": "skipped" if s.skip else "pending", "title": s.title, "elapsed_ms": None} for s in plan.steps],
        "assets": [], "asset_count": 0, "total_ms": None,
    })
    run_director.delay(job_id, plan.to_dict(), dry, None)
    return {"job_id": job_id, "plan": plan.to_dict(), "dry_run": dry}


@router.get("/progress/{job_id}", summary="查询异步执行进度")
async def run_progress(job_id: str):
    from app.tasks.director_tasks import read_progress
    state = read_progress(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="job not found or expired")
    return state


@router.post("/step/rerun", summary="重新执行单个步骤 (per-step 重生成)")
async def rerun_step(req: StepRerunRequest):
    dry = _dry_run_default() if req.dry_run is None else req.dry_run
    executor = DirectorExecutor(dry_run=dry)
    data = dict(req.step)
    step = DirectorStep(
        id=data.get("id") or uuid.uuid4().hex[:8],
        action=data.get("action", "image"), title=data.get("title", ""),
        model_id=data.get("model_id", ""), model_name=data.get("model_name", ""),
        reason=data.get("reason", ""), prompt=data.get("prompt", ""),
        depends_on=[], est_credits=int(data.get("est_credits", 0) or 0),
        params=data.get("params", {}) or {},
    )
    return await executor.run_single(step)


# ─────────────────────── Sessions (对标 yapper Sessions) ───────────────────────
class SessionCreate(BaseModel):
    title: str | None = None
    brief: str | None = None
    user_id: int = 0


class SessionUpdate(BaseModel):
    title: str | None = None
    brief: str | None = None
    intent: str | None = None
    plan: dict | None = None
    assets: list | None = None
    status: str | None = None


@router.get("/sessions", summary="列出导演会话")
async def list_sessions(user_id: int = 0, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(DirectorSession).where(DirectorSession.user_id == user_id)
        .order_by(DirectorSession.updated_at.desc()).limit(100)
    )).scalars().all()
    return {"sessions": [s.to_dict() for s in rows]}


@router.post("/sessions", summary="创建导演会话")
async def create_session(req: SessionCreate, db: AsyncSession = Depends(get_db)):
    s = DirectorSession(
        session_uid=uuid.uuid4().hex, user_id=req.user_id,
        title=req.title or "新导演会话", brief=req.brief, status="draft",
    )
    db.add(s)
    await db.flush()
    return s.to_dict()


@router.get("/sessions/{uid}", summary="获取会话详情")
async def get_session(uid: str, db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(DirectorSession).where(DirectorSession.session_uid == uid))).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    return s.to_dict()


@router.patch("/sessions/{uid}", summary="更新会话(保存计划/资产)")
async def update_session(uid: str, req: SessionUpdate, db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(DirectorSession).where(DirectorSession.session_uid == uid))).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    for k, v in req.model_dump(exclude_none=True).items():
        setattr(s, k, v)
    await db.flush()
    return s.to_dict()


@router.delete("/sessions/{uid}", summary="删除会话")
async def delete_session(uid: str, db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(DirectorSession).where(DirectorSession.session_uid == uid))).scalar_one_or_none()
    if s:
        await db.delete(s)
    return {"deleted": bool(s)}
