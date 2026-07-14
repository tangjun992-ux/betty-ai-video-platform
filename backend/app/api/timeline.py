"""
Timeline Editor API — 时间线编辑器: 多片段编排 → 渲染合成视频

对标剪映 / CapCut 时间线剪辑功能。项目持久化到 DB，按 resolve_user_id 隔离。
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db import get_db
from app.auth import resolve_user_id
from app.models.timeline_project import TimelineProject as TimelineProjectRow

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Request / Response Models ─────────────────────────

class ClipItem(BaseModel):
    """时间线片段"""
    url: str = Field(..., description="素材 URL")
    start: float = Field(0.0, description="起始时间 (秒)")
    end: float = Field(5.0, description="结束时间 (秒)")
    transition: Optional[str] = Field("cut", description="转场效果: cut | fade | dissolve | slide | zoom")
    label: Optional[str] = Field(None, description="片段标签/备注")


class TimelineSettings(BaseModel):
    narration_url: Optional[str] = None
    with_audio: bool = True
    transition: str = Field("fade", description="cut | fade | dissolve")
    subtitle_track: Optional[List[dict]] = Field(default=None, description="[{text,start,end}]")


class SaveProjectRequest(BaseModel):
    """创建/保存项目请求"""
    id: Optional[str] = Field(None, description="项目ID，不传则新建")
    name: str = Field("未命名项目", description="项目名称")
    clips: List[ClipItem] = Field(..., description="时间线片段列表")
    settings: Optional[TimelineSettings] = None


class SaveProjectResponse(BaseModel):
    id: str
    name: str
    clip_count: int
    total_duration: float
    created_at: str
    updated_at: str


class RenderRequest(BaseModel):
    """渲染请求"""
    project_id: str = Field(..., description="要渲染的项目ID")
    quality: str = Field("balanced", description="输出质量: draft | balanced | high")
    format: str = Field("mp4", description="输出格式: mp4 | mov | webm")


class RenderResponse(BaseModel):
    task_id: str
    status: str = "queued"
    project_id: str
    estimated_time_seconds: int = 60
    estimated_cost_credits: int = 4
    poll_url: str = ""


async def _owned(
    db: AsyncSession, project_id: str, user_id: int,
) -> TimelineProjectRow:
    row = (await db.execute(
        select(TimelineProjectRow).where(TimelineProjectRow.project_id == project_id)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    if (row.user_id or 0) != user_id:
        raise HTTPException(status_code=403, detail="无权访问此项目")
    return row


# ─── Endpoints ─────────────────────────────────────────

@router.get(
    "/timeline/projects",
    summary="列出所有时间线项目",
    description="返回当前用户已保存的时间线项目列表。",
)
async def list_projects(
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    """列出当前用户已保存的时间线项目。"""
    rows = (await db.execute(
        select(TimelineProjectRow)
        .where(TimelineProjectRow.user_id == user_id)
        .order_by(TimelineProjectRow.updated_at.desc())
    )).scalars().all()
    projects = [r.to_api_dict() for r in rows]
    return {"total": len(projects), "projects": projects}


@router.post(
    "/timeline/projects",
    response_model=SaveProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建或保存时间线项目",
    description="创建新的时间线项目或更新已有项目。传入 id 则更新，否则新建。",
)
async def save_project(
    req: SaveProjectRequest,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    创建或保存时间线项目。

    - **id**: 可选，传入则更新已有项目，不传则新建
    - **name**: 项目名称
    - **clips**: 时间线片段数组
    """
    clips_data = [c.model_dump() for c in req.clips]
    settings_data = req.settings.model_dump() if req.settings else {}
    total_duration = sum(max(0, c.end - c.start) for c in req.clips)

    if req.id:
        row = (await db.execute(
            select(TimelineProjectRow).where(TimelineProjectRow.project_id == req.id)
        )).scalar_one_or_none()
        if row:
            if (row.user_id or 0) != user_id:
                raise HTTPException(status_code=403, detail="无权访问此项目")
            row.name = req.name
            row.clips = clips_data
            row.settings = settings_data
            flag_modified(row, "clips")
            flag_modified(row, "settings")
            await db.commit()
            await db.refresh(row)
            logger.info(
                "Timeline project updated: %s (%s) - %d clips, %.1fs",
                row.project_id, req.name, len(req.clips), total_duration,
            )
            return SaveProjectResponse(
                id=row.project_id,
                name=row.name,
                clip_count=len(req.clips),
                total_duration=round(total_duration, 1),
                created_at=row.created_at.isoformat() if row.created_at else "",
                updated_at=row.updated_at.isoformat() if row.updated_at else "",
            )

    pid = req.id or str(uuid.uuid4())
    row = TimelineProjectRow(
        project_id=pid,
        user_id=user_id,
        name=req.name,
        clips=clips_data,
        settings=settings_data,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.info(
        "Timeline project created: %s (%s) - %d clips, %.1fs",
        pid, req.name, len(req.clips), total_duration,
    )
    return SaveProjectResponse(
        id=row.project_id,
        name=row.name,
        clip_count=len(req.clips),
        total_duration=round(total_duration, 1),
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


@router.get(
    "/timeline/projects/{project_id}",
    summary="获取单个时间线项目",
    description="根据项目 ID 获取项目详情。",
)
async def get_project(
    project_id: str,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取单个时间线项目的完整信息。"""
    row = await _owned(db, project_id, user_id)
    return row.to_api_dict()


class ComposeClip(BaseModel):
    url: str = Field(..., description="片段 URL（本地 /api/v1/media 视频）")
    transition: Optional[str] = Field("cut", description="转场: cut | fade | dissolve")


class ComposeRequest(BaseModel):
    clips: List[ComposeClip] = Field(..., min_length=1, description="按顺序排列的视频片段")
    narration_url: Optional[str] = Field(None, description="可选旁白/配乐音轨 URL")
    with_audio: bool = Field(True, description="是否混入音轨")
    transition: Optional[str] = Field("cut", description="全局默认转场: cut | fade | dissolve")
    subtitle_track: Optional[List[dict]] = Field(None, description="字幕轨（可选）")


@router.post("/timeline/compose", summary="合成时间线为成片（同步）")
async def compose_timeline(req: ComposeRequest):
    """Stitch the ordered clips into one film using the proven ffmpeg composer.
    Synchronous (a few short clips finish in seconds); returns the local video."""
    import asyncio as _a
    urls = [c.url for c in req.clips if c.url]
    if not urls:
        raise HTTPException(status_code=400, detail="没有可合成的片段")
    from app.adapters.demo_provider import compose_final_video, _local_media_path
    missing = [u for u in urls if not _local_media_path(u)]
    if missing:
        raise HTTPException(status_code=400,
                            detail=f"{len(missing)} 个片段不是可访问的本地视频，无法合成")
    # Per-clip transition falls back to request-level default.
    transitions = [
        (c.transition or req.transition or "cut") for c in req.clips if c.url
    ]
    try:
        final_url, poster = await _a.to_thread(
            compose_final_video,
            urls,
            None,
            req.with_audio,
            req.narration_url,
            transitions=transitions,
            subtitle_track=req.subtitle_track or [],
        )
    except Exception as e:
        logger.error("timeline compose failed: %s", e)
        raise HTTPException(status_code=500, detail=f"合成失败: {e}")
    return {
        "url": final_url, "thumbnail": poster, "clip_count": len(urls),
        "media_type": "video",
        "transition": req.transition or "cut",
        "transitions": transitions,
        "subtitle_track": req.subtitle_track or [],
    }


@router.post(
    "/timeline/render",
    response_model=RenderResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="渲染时间线为视频",
    description="将指定时间线项目渲染合成为视频，返回任务 ID 用于追踪进度。",
)
async def render_timeline(
    req: RenderRequest,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    渲染时间线项目为视频。

    - **project_id**: 要渲染的项目 ID
    - **quality**: 输出质量 (draft / balanced / high)
    - **format**: 输出格式 (mp4 / mov / webm)

    返回 task_id，可通过 `/api/v1/tasks/{task_id}` 查询渲染进度。
    """
    row = await _owned(db, req.project_id, user_id)
    clips = row.clips if isinstance(row.clips, list) else []
    if not clips:
        raise HTTPException(
            status_code=400,
            detail="项目中没有任何片段，无法渲染",
        )

    task_id = str(uuid.uuid4())
    total_duration = sum(max(0, float(c.get("end", 5)) - float(c.get("start", 0))) for c in clips)
    estimated_time = max(30, int(total_duration * 3))  # ~3x real-time

    # Dispatch Celery task
    try:
        from app.tasks.timeline_tasks import process_timeline_render

        celery_task = process_timeline_render.delay(
            db_task_id=task_id,
            project_id=req.project_id,
        )
    except Exception as e:
        logger.error(f"Failed to dispatch timeline render task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"渲染任务调度失败: {str(e)}",
        )

    logger.info(
        f"Timeline render dispatched: task={task_id} project={req.project_id} "
        f"clips={len(clips)} duration={total_duration:.1f}s celery_id={celery_task.id}"
    )

    return RenderResponse(
        task_id=task_id,
        status="queued",
        project_id=req.project_id,
        estimated_time_seconds=estimated_time,
        estimated_cost_credits=4,
        poll_url=f"/api/v1/tasks/{task_id}",
    )
