"""
Director API — 导演式编排端点 (对标 yapper Agent)
  POST /director/plan  → 生成创作计划 (用户先看导演方案)
  POST /director/run   → 执行计划，产出多资产
  默认策略：有真实模型 Key 时允许真实执行；显式 DIRECTOR_DRY_RUN=1 才强制预览。
"""
import json
import os
import uuid
import re
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.director import (
    planner, DirectorExecutor, DirectorPlanner, plan_from_dict, DirectorStep,
    build_storyboard_plan,
)
from app.db import get_db
from app.models.director_session import DirectorSession
from app.auth import resolve_user_id
from app.models.user import User
from app.services.credits import deduct_credits, resolve_team_id
from app.services.director_brain import ideate as brain_ideate, refine_with_llm

router = APIRouter()


def _dry_run_default() -> bool:
    """Preview-only when explicitly forced OR no provider keys are configured.
    When real models are available, default to real execution (client can still
    request dry_run=true for free preview)."""
    val = os.getenv("DIRECTOR_DRY_RUN") or os.getenv("DRY_RUN") or ""
    if val:
        return val.lower() in ("1", "true", "yes", "on")
    try:
        from app.adapters.demo_provider import demo_mode_active
        if demo_mode_active():
            return True  # no keys → only demo/preview makes sense
        from app.config import settings
        if getattr(settings, "is_production", False):
            return False
        return False  # keys present → real by default
    except Exception:
        return True


class PlanRequest(BaseModel):
    brief: str = Field(..., description="一句话创作意图，例如：做一个30秒的咖啡产品宣传片")
    has_ref_image: bool = Field(default=False)
    duration: int = Field(default=5, ge=1, le=60)
    ref_image_url: Optional[str] = Field(default=None, description="参考图 URL（真正参与图生视频/关键帧）")
    minimal: bool = Field(
        default=False,
        description="最短路径：跳过配音/字幕，多镜仍会合成一条成片（对标 Yapper quick-direct）",
    )
    scenario: Optional[str] = Field(
        default=None,
        description="Agent 场景卡 id：product_ad|product_commercial|ugc|micro_drama|anime|product_photo|ai_portrait|talking_avatar",
    )
    identity_lock: str = Field(
        default="edit",
        description="跨镜身份锁：off|hero|edit（edit=shot>1 先 edit_image 再 i2v）",
    )


class RunRequest(PlanRequest):
    dry_run: bool | None = Field(default=None, description="留空则按服务端默认")
    plan: Optional[dict] = Field(default=None, description="可选：客户端已编辑的计划，优先于 brief 自动规划")
    session_uid: Optional[str] = Field(default=None, description="可选：异步完成后回写导演会话")


class StepRerunRequest(BaseModel):
    step: dict = Field(..., description="要重新执行的单个步骤")
    dry_run: bool | None = None


def _moderate_brief(brief: str | None):
    """Pre-generation content gate for the director brief."""
    if not brief:
        return
    from app.services.moderation import check_prompt, moderation_reject
    m = check_prompt(brief)
    if not m.allowed:
        raise moderation_reject(m)


def _resolve_plan(req: RunRequest):
    """Use the (edited) client plan when provided, else auto-plan from the brief."""
    if req.plan and req.plan.get("steps"):
        return plan_from_dict(req.plan)
    _moderate_brief(req.brief)
    return DirectorPlanner().plan(
        req.brief,
        has_ref_image=req.has_ref_image,
        duration=req.duration,
        ref_image_url=req.ref_image_url,
        minimal=bool(req.minimal),
        scenario=getattr(req, "scenario", None),
        identity_lock=getattr(req, "identity_lock", None) or "edit",
    )


async def _charge_director_plan(
    db: AsyncSession, user_id: int, plan, *, team_id: str | None, dry_run: bool,
) -> None:
    """Deduct estimated plan credits before real execution."""
    if dry_run:
        return
    cost = sum(s.est_credits for s in plan.steps if not s.skip)
    if cost <= 0:
        return
    task_id = uuid.uuid4().hex
    ok = await deduct_credits(
        db, user_id, cost, task_id, "director",
        team_id=team_id,
        description=f"Director plan ({len(plan.steps)} steps)",
    )
    if not ok:
        raise HTTPException(status_code=402, detail=f"积分不足，需要 {cost} 积分")
    await db.commit()


@router.post("/plan", summary="生成导演式创作计划")
async def make_plan(req: PlanRequest):
    _moderate_brief(req.brief)
    plan = planner.plan(
        req.brief,
        has_ref_image=req.has_ref_image,
        duration=req.duration,
        ref_image_url=req.ref_image_url,
        minimal=bool(req.minimal),
        scenario=req.scenario,
        identity_lock=req.identity_lock or "edit",
    )
    return plan.to_dict()


class StoryboardShot(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    duration: int = Field(default=5, ge=1, le=15)
    label: Optional[str] = None


class StoryboardRequest(BaseModel):
    shots: list[StoryboardShot] = Field(..., min_length=1, max_length=8)
    brief: Optional[str] = Field(default=None, description="整片简述（可选）")
    ref_image_url: Optional[str] = Field(default=None)
    # Omni 一体：多模态参考可随真分镜共享到每个 video step
    reference_images: Optional[list[str]] = Field(default=None, max_length=9)
    reference_videos: Optional[list[str]] = Field(default=None, max_length=3)
    reference_audios: Optional[list[str]] = Field(default=None, max_length=3)
    omni: bool = Field(default=False, description="Seedance Omni 多模态模式")
    generate_audio: bool = Field(default=False, description="Seedance 生成音轨（非 Kling 口型）")
    dry_run: bool | None = Field(default=None)
    with_compose: bool = Field(default=True, description="是否追加 ffmpeg 合成步骤")
    async_mode: bool = Field(default=True, description="默认异步执行（真分镜耗时长）")


@router.post("/storyboard", summary="真分镜：显式多镜头计划并执行（非提示词拼接）")
async def run_storyboard(
    req: StoryboardRequest,
    request: Request,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Each shot is a real Director video step — not Create-Video prompt stitching."""
    for sh in req.shots:
        _moderate_brief(sh.prompt)
    if req.brief:
        _moderate_brief(req.brief)
    try:
        plan = build_storyboard_plan(
            [s.model_dump() for s in req.shots],
            brief=req.brief or "多镜头分镜创作",
            ref_image_url=req.ref_image_url,
            reference_images=req.reference_images,
            reference_videos=req.reference_videos,
            reference_audios=req.reference_audios,
            omni=req.omni,
            generate_audio=req.generate_audio,
            with_compose=req.with_compose,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    dry = _dry_run_default() if req.dry_run is None else req.dry_run
    await _charge_director_plan(db, user_id, plan, team_id=resolve_team_id(request), dry_run=dry)

    if not req.async_mode:
        executor = DirectorExecutor(dry_run=dry)
        assets, last = [], None
        async for ev in executor.run_stream(plan):
            last = ev
            if ev.get("type") == "complete":
                assets = ev.get("assets") or []
        return {
            "plan": plan.to_dict(), "dry_run": dry, "storyboard": True,
            "assets": assets, "complete": last,
        }

    job_id = uuid.uuid4().hex
    from app.tasks.director_tasks import run_director, write_progress
    write_progress(job_id, {
        "job_id": job_id, "status": "queued", "done": False, "dry_run": dry,
        "user_id": user_id,
        "session_uid": None,
        "plan": plan.to_dict(),
        "storyboard": True,
        "steps": [
            {"id": s.id, "status": "skipped" if s.skip else "pending",
             "title": s.title, "elapsed_ms": None}
            for s in plan.steps
        ],
        "assets": [], "asset_count": 0, "total_ms": None,
    })
    run_director.delay(job_id, plan.to_dict(), dry, None, user_id)
    return {
        "job_id": job_id,
        "plan": plan.to_dict(),
        "dry_run": dry,
        "storyboard": True,
        "shot_count": len(req.shots),
        "poll_url": f"/api/v1/director/progress/{job_id}",
    }


class RefineRequest(BaseModel):
    plan: dict = Field(..., description="当前计划")
    directive: str = Field(..., description="导演指令，如：把第2镜改暖一点 / 加一个镜头 / 换成 Veo 3.1 / 竖屏")
    brain: str = Field(default="fast", description="fast | quality | rules")


class IdeateRequest(BaseModel):
    brief: str = Field(..., min_length=1)
    brain: str = Field(default="fast", description="fast | quality | rules")

@router.get("/brain/modes", summary="导演大脑模式列表")
async def brain_modes():
    from app.services.director_brain import BRAIN_MODES
    return {"modes": BRAIN_MODES}


@router.post("/ideate", summary="帮我构思：从一句话发散多个创意方向")
async def ideate(req: IdeateRequest):
    """Expand a rough idea into several distinct creative concepts to pick from
    (对标 yapper 'Help Ideate'). Uses LLM when a key is configured, else rules."""
    _moderate_brief(req.brief)
    concepts = await brain_ideate(req.brief.strip(), brain=req.brain)
    return {"concepts": concepts, "brain": req.brain}


class VariantsRequest(BaseModel):
    brief: str = Field(..., min_length=1)
    scenario: Optional[str] = Field(default=None)
    duration: int = Field(default=15, ge=5, le=60)
    minimal: bool = Field(default=True)
    n: int = Field(default=3, ge=1, le=5, description="变体数量 1–5")
    axes: Optional[list[str]] = Field(
        default=None,
        description="变体轴：hook|cta|seed（默认三者全开）",
    )
    identity_lock: str = Field(default="edit", description="off|hero|edit")


class VariantsRunRequest(VariantsRequest):
    dry_run: bool | None = Field(default=None)
    session_uid: Optional[str] = Field(default=None)
    # Optional pre-built variants from POST /variants (skip re-plan)
    variants: Optional[list[dict]] = Field(default=None)


@router.post("/variants", summary="批量创意变体：钩子/CTA/seed 扇出多计划")
async def plan_variants(req: VariantsRequest):
    """Advantage+/Creatify-style plan fan-out — returns N editable plans (not executed).

    Client can then POST ``/director/variants/run`` for parallel outings, or run each plan.
    """
    _moderate_brief(req.brief)
    variants = DirectorPlanner().plan_variants(
        req.brief.strip(),
        scenario=(req.scenario or "").strip(),
        duration=req.duration,
        minimal=bool(req.minimal),
        n=req.n,
        axes=req.axes,
        identity_lock=req.identity_lock or "edit",
    )
    return {"count": len(variants), "variants": variants, "scenario": req.scenario}


@router.post("/variants/run", summary="并行执行 2–3 个创意变体出片")
async def run_variants(
    req: VariantsRunRequest,
    request: Request,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Enqueue N variant plans as parallel Celery jobs; poll ``/variants/progress/{batch_id}``."""
    _moderate_brief(req.brief)
    dry = _dry_run_default() if req.dry_run is None else req.dry_run
    variants = req.variants
    if not variants:
        variants = DirectorPlanner().plan_variants(
            req.brief.strip(),
            scenario=(req.scenario or "").strip(),
            duration=req.duration,
            minimal=bool(req.minimal),
            n=req.n,
            axes=req.axes,
            identity_lock=req.identity_lock or "edit",
        )
    variants = variants[: max(1, min(int(req.n or 3), 5))]
    from app.tasks.director_tasks import run_director, write_progress

    jobs: list[dict] = []
    total_cost = 0
    for v in variants:
        plan = plan_from_dict(v["plan"])
        if not dry:
            cost = sum(s.est_credits for s in plan.steps if not s.skip)
            total_cost += cost
            await _charge_director_plan(db, user_id, plan, team_id=resolve_team_id(request), dry_run=False)
        job_id = uuid.uuid4().hex
        write_progress(job_id, {
            "job_id": job_id, "status": "queued", "done": False, "dry_run": dry,
            "user_id": user_id,
            "session_uid": req.session_uid,
            "variant_id": v.get("variant_id"),
            "plan": plan.to_dict(),
            "steps": [
                {"id": s.id, "status": "skipped" if s.skip else "pending",
                 "title": s.title, "elapsed_ms": None}
                for s in plan.steps
            ],
            "assets": [], "asset_count": 0, "total_ms": None,
        })
        run_director.delay(job_id, plan.to_dict(), dry, req.session_uid, user_id)
        jobs.append({
            "variant_id": v.get("variant_id"),
            "label": v.get("label"),
            "axes_applied": v.get("axes_applied") or [],
            "job_id": job_id,
        })

    batch_id = uuid.uuid4().hex
    write_progress(batch_id, {
        "batch_id": batch_id, "type": "variants_batch",
        "status": "running", "done": False,
        "user_id": user_id, "dry_run": dry,
        "jobs": jobs, "count": len(jobs), "total_credits": total_cost,
    })
    return {
        "batch_id": batch_id, "count": len(jobs), "jobs": jobs,
        "dry_run": dry, "total_credits": total_cost,
    }


@router.get("/variants/progress/{batch_id}", summary="查询变体批量出片进度")
async def variants_progress(
    batch_id: str,
    user_id: int = Depends(resolve_user_id),
):
    from app.tasks.director_tasks import read_progress
    from app.config import settings

    batch = read_progress(batch_id)
    if batch is None or batch.get("type") != "variants_batch":
        raise HTTPException(status_code=404, detail="batch not found or expired")
    owner = batch.get("user_id")
    if owner is None and settings.is_production:
        raise HTTPException(status_code=403, detail="无权查看此批次")
    if owner is not None and int(owner) != user_id:
        raise HTTPException(status_code=403, detail="无权查看此批次")

    items: list[dict] = []
    all_done = True
    any_fail = False
    for j in batch.get("jobs") or []:
        st = read_progress(j["job_id"]) or {}
        finals = [a for a in (st.get("assets") or []) if a.get("final")]
        pick = finals[0] if finals else None
        status = st.get("status") or "queued"
        done = bool(st.get("done"))
        if not done:
            all_done = False
        if status == "failed":
            any_fail = True
        items.append({
            "variant_id": j.get("variant_id"),
            "label": j.get("label"),
            "axes_applied": j.get("axes_applied") or [],
            "job_id": j["job_id"],
            "status": status,
            "done": done,
            "asset_count": st.get("asset_count") or 0,
            "final": pick,
            "assets": st.get("assets") or [],
            "error": st.get("error"),
        })
    return {
        "batch_id": batch_id,
        "done": all_done,
        "status": "failed" if (all_done and any_fail and not any(i.get("final") for i in items))
        else ("done" if all_done else "running"),
        "count": len(items),
        "variants": items,
    }


@router.post("/refine", summary="对话式导演：用自然语言迭代计划")
async def refine(req: RefineRequest):
    """LLM refine when a key is available; falls back to the rule engine."""
    plan_dict, changes = await refine_with_llm(req.plan, req.directive, brain=req.brain)
    return {"plan": plan_dict, "changes": changes, "brain": req.brain}


@router.post("/run", summary="执行导演计划，产出多资产 (非流式)")
async def run_plan(
    req: RunRequest,
    request: Request,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    plan = _resolve_plan(req)
    dry = _dry_run_default() if req.dry_run is None else req.dry_run
    await _charge_director_plan(db, user_id, plan, team_id=resolve_team_id(request), dry_run=dry)
    executor = DirectorExecutor(dry_run=dry)
    return await executor.run(plan)


@router.post("/run/stream", summary="流式执行导演计划 (SSE)")
async def run_plan_stream(
    req: RunRequest,
    request: Request,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Stream per-step events (SSE). Frontend reads the body incrementally to
    animate the director's progress and surface assets as each shot completes."""
    plan = _resolve_plan(req)
    dry = _dry_run_default() if req.dry_run is None else req.dry_run
    await _charge_director_plan(db, user_id, plan, team_id=resolve_team_id(request), dry_run=dry)
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
async def run_plan_async(
    req: RunRequest,
    request: Request,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Kick off the plan in a Celery task; poll GET /director/progress/<job_id>.
    Use this for real multi-shot films (6 shots × ~150s) that would time out over
    a live connection."""
    plan = _resolve_plan(req)
    dry = _dry_run_default() if req.dry_run is None else req.dry_run
    await _charge_director_plan(db, user_id, plan, team_id=resolve_team_id(request), dry_run=dry)
    session_uid = req.session_uid
    if session_uid:
        await _owned_session(db, session_uid, user_id)
    job_id = uuid.uuid4().hex
    from app.tasks.director_tasks import run_director, write_progress
    # Seed a 'queued' snapshot so the first poll always returns something.
    write_progress(job_id, {
        "job_id": job_id, "status": "queued", "done": False, "dry_run": dry,
        "user_id": user_id,
        "session_uid": session_uid,
        "plan": plan.to_dict(),
        "steps": [{"id": s.id, "status": "skipped" if s.skip else "pending", "title": s.title, "elapsed_ms": None} for s in plan.steps],
        "assets": [], "asset_count": 0, "total_ms": None,
    })
    run_director.delay(job_id, plan.to_dict(), dry, session_uid, user_id)
    return {"job_id": job_id, "plan": plan.to_dict(), "dry_run": dry, "session_uid": session_uid}


@router.get("/progress/{job_id}", summary="查询异步执行进度")
async def run_progress(
    job_id: str,
    user_id: int = Depends(resolve_user_id),
):
    from app.tasks.director_tasks import read_progress
    from app.config import settings
    state = read_progress(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="job not found or expired")
    owner = state.get("user_id")
    if owner is None and settings.is_production:
        raise HTTPException(status_code=403, detail="无权查看此任务进度")
    if owner is not None and int(owner) != user_id:
        raise HTTPException(status_code=403, detail="无权查看此任务进度")
    return state


@router.post("/step/rerun", summary="重新执行单个步骤 (per-step 重生成)")
async def rerun_step(
    req: StepRerunRequest,
    request: Request,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    dry = _dry_run_default() if req.dry_run is None else req.dry_run
    data = dict(req.step)
    step = DirectorStep(
        id=data.get("id") or uuid.uuid4().hex[:8],
        action=data.get("action", "image"), title=data.get("title", ""),
        model_id=data.get("model_id", ""), model_name=data.get("model_name", ""),
        reason=data.get("reason", ""), prompt=data.get("prompt", ""),
        depends_on=[], est_credits=int(data.get("est_credits", 0) or 0),
        params=data.get("params", {}) or {},
    )
    if not dry and step.est_credits > 0:
        ok = await deduct_credits(
            db, user_id, step.est_credits, step.id, step.model_id or "director",
            team_id=resolve_team_id(request),
            description=f"Director rerun {step.title[:20]}",
        )
        if not ok:
            raise HTTPException(status_code=402, detail=f"积分不足，需要 {step.est_credits} 积分")
        await db.commit()
    executor = DirectorExecutor(dry_run=dry)
    return await executor.run_single(step)


# ─────────────────────── Sessions (对标 yapper Sessions) ───────────────────────
class SessionCreate(BaseModel):
    title: str | None = None
    brief: str | None = None


class SessionUpdate(BaseModel):
    title: str | None = None
    brief: str | None = None
    intent: str | None = None
    plan: dict | None = None
    assets: list | None = None
    status: str | None = None


async def _owned_session(db: AsyncSession, uid: str, user_id: int) -> DirectorSession:
    s = (await db.execute(
        select(DirectorSession).where(DirectorSession.session_uid == uid)
    )).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    # Guests only see guest sessions; authenticated users only their own.
    if s.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    return s


@router.get("/sessions", summary="列出导演会话")
async def list_sessions(
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(DirectorSession).where(DirectorSession.user_id == user_id)
        .order_by(DirectorSession.updated_at.desc()).limit(100)
    )).scalars().all()
    return {"sessions": [s.to_dict() for s in rows], "user_id": user_id}


@router.post("/sessions", summary="创建导演会话")
async def create_session(
    req: SessionCreate,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    s = DirectorSession(
        session_uid=uuid.uuid4().hex, user_id=user_id,
        title=req.title or "新导演会话", brief=req.brief, status="draft",
    )
    db.add(s)
    await db.flush()
    return s.to_dict()


@router.get("/sessions/{uid}", summary="获取会话详情")
async def get_session(
    uid: str,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    s = await _owned_session(db, uid, user_id)
    return s.to_dict()


@router.patch("/sessions/{uid}", summary="更新会话(保存计划/资产)")
async def update_session(
    uid: str,
    req: SessionUpdate,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    s = await _owned_session(db, uid, user_id)
    for k, v in req.model_dump(exclude_none=True).items():
        setattr(s, k, v)
    await db.flush()
    return s.to_dict()


@router.delete("/sessions/{uid}", summary="删除会话")
async def delete_session(
    uid: str,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    s = await _owned_session(db, uid, user_id)
    await db.delete(s)
    return {"deleted": True}


@router.get("/mode", summary="导演执行模式（预览/真实）")
async def director_mode():
    """Tell the UI whether real generation is available vs preview-only."""
    dry = _dry_run_default()
    try:
        from app.adapters.demo_provider import demo_mode_active, any_provider_configured
        demo = demo_mode_active()
        configured = any_provider_configured()
    except Exception:
        demo, configured = True, False
    return {
        "dry_run_default": dry,
        "demo_mode": demo,
        "providers_configured": configured,
        "real_available": configured and not dry,
        "label": "预览模式" if dry or demo else "真实生成可用",
    }
