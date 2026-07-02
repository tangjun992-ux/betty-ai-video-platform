"""
Director API — 导演式编排端点 (对标 yapper Agent)
  POST /director/plan  → 生成创作计划 (用户先看导演方案)
  POST /director/run   → 执行计划，产出多资产 (默认 DRY_RUN)
"""
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.director import planner, DirectorExecutor, DirectorPlanner
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


class RunRequest(PlanRequest):
    dry_run: bool | None = Field(default=None, description="留空则按服务端默认")


@router.post("/plan", summary="生成导演式创作计划")
async def make_plan(req: PlanRequest):
    plan = planner.plan(req.brief, has_ref_image=req.has_ref_image, duration=req.duration)
    return plan.to_dict()


@router.post("/run", summary="执行导演计划，产出多资产")
async def run_plan(req: RunRequest):
    plan = DirectorPlanner().plan(req.brief, has_ref_image=req.has_ref_image, duration=req.duration)
    dry = _dry_run_default() if req.dry_run is None else req.dry_run
    executor = DirectorExecutor(dry_run=dry)
    return await executor.run(plan)


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
