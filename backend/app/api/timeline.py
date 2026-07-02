"""
Timeline Editor API — 时间线编辑器: 多片段编排 → 渲染合成视频

对标剪映 / CapCut 时间线剪辑功能。
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models.task import Task

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── In-Memory Store ────────────────────────────────────
# 简单内存存储，替代数据库表
_timeline_projects: dict = {}

# ─── Models ────────────────────────────────────────────

class ClipItem(BaseModel):
    """时间线片段"""
    url: str = Field(..., description="素材 URL")
    start: float = Field(0.0, description="起始时间 (秒)")
    end: float = Field(5.0, description="结束时间 (秒)")
    transition: Optional[str] = Field("cut", description="转场效果: cut | fade | dissolve | slide | zoom")
    label: Optional[str] = Field(None, description="片段标签/备注")


class TimelineProject(BaseModel):
    """时间线项目"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field("未命名项目", description="项目名称")
    clips: List[ClipItem] = Field(default_factory=list, description="时间线片段列表")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SaveProjectRequest(BaseModel):
    """创建/保存项目请求"""
    id: Optional[str] = Field(None, description="项目ID，不传则新建")
    name: str = Field("未命名项目", description="项目名称")
    clips: List[ClipItem] = Field(..., description="时间线片段列表")


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


# ─── Pre-populate Demo Projects ─────────────────────────

_DEMO_PROJECTS = [
    TimelineProject(
        id="demo-001",
        name="产品宣传片",
        clips=[
            ClipItem(url="https://example.com/media/intro.mp4", start=0.0, end=3.0, transition="fade", label="开场"),
            ClipItem(url="https://example.com/media/product-showcase.mp4", start=0.0, end=8.0, transition="dissolve", label="产品展示"),
            ClipItem(url="https://example.com/media/testimonial.mp4", start=0.0, end=5.0, transition="slide", label="客户证言"),
            ClipItem(url="https://example.com/media/outro.mp4", start=0.0, end=3.0, transition="fade", label="结尾 CTA"),
        ],
        created_at="2025-05-01T08:00:00+00:00",
        updated_at="2025-05-01T08:00:00+00:00",
    ),
    TimelineProject(
        id="demo-002",
        name="旅行 Vlog",
        clips=[
            ClipItem(url="https://example.com/media/airport.mp4", start=0.0, end=4.0, transition="cut", label="出发"),
            ClipItem(url="https://example.com/media/beach.mp4", start=2.0, end=10.0, transition="dissolve", label="海滩"),
            ClipItem(url="https://example.com/media/food.mp4", start=0.0, end=6.0, transition="zoom", label="美食"),
            ClipItem(url="https://example.com/media/sunset.mp4", start=0.0, end=5.0, transition="fade", label="日落"),
            ClipItem(url="https://example.com/media/goodbye.mp4", start=0.0, end=3.0, transition="fade", label="告别"),
        ],
        created_at="2025-05-10T12:00:00+00:00",
        updated_at="2025-05-10T12:00:00+00:00",
    ),
]

for p in _DEMO_PROJECTS:
    _timeline_projects[p.id] = p.model_dump()


# ─── Endpoints ─────────────────────────────────────────

@router.get(
    "/timeline/projects",
    summary="列出所有时间线项目",
    description="返回所有已保存的时间线项目列表。",
)
async def list_projects():
    """列出所有已保存的时间线项目。"""
    projects = list(_timeline_projects.values())
    # 按更新时间倒序排列
    projects.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    return {
        "total": len(projects),
        "projects": projects,
    }


@router.post(
    "/timeline/projects",
    response_model=SaveProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建或保存时间线项目",
    description="创建新的时间线项目或更新已有项目。传入 id 则更新，否则新建。",
)
async def save_project(req: SaveProjectRequest):
    """
    创建或保存时间线项目。

    - **id**: 可选，传入则更新已有项目，不传则新建
    - **name**: 项目名称
    - **clips**: 时间线片段数组，每个片段包含:
        - url: 素材 URL
        - start: 起始时间 (秒)
        - end: 结束时间 (秒)
        - transition: 转场效果
        - label: 标签/备注
    """
    now = datetime.now(timezone.utc).isoformat()

    if req.id and req.id in _timeline_projects:
        # 更新已有项目
        project = _timeline_projects[req.id]
        project["name"] = req.name
        project["clips"] = [c.model_dump() for c in req.clips]
        project["updated_at"] = now
        pid = req.id
        created_at = project["created_at"]
        action = "updated"
    else:
        # 新建项目
        pid = req.id or str(uuid.uuid4())
        project_data = {
            "id": pid,
            "name": req.name,
            "clips": [c.model_dump() for c in req.clips],
            "created_at": now,
            "updated_at": now,
        }
        _timeline_projects[pid] = project_data
        created_at = now
        action = "created"

    total_duration = sum(
        max(0, c.end - c.start) for c in req.clips
    )

    logger.info(f"Timeline project {action}: {pid} ({req.name}) - {len(req.clips)} clips, {total_duration:.1f}s")

    return SaveProjectResponse(
        id=pid,
        name=req.name,
        clip_count=len(req.clips),
        total_duration=round(total_duration, 1),
        created_at=created_at,
        updated_at=now,
    )


@router.get(
    "/timeline/projects/{project_id}",
    summary="获取单个时间线项目",
    description="根据项目 ID 获取项目详情。",
)
async def get_project(project_id: str):
    """获取单个时间线项目的完整信息。"""
    project = _timeline_projects.get(project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"项目不存在: {project_id}",
        )
    return project


@router.post(
    "/timeline/render",
    response_model=RenderResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="渲染时间线为视频",
    description="将指定时间线项目渲染合成为视频，返回任务 ID 用于追踪进度。",
)
async def render_timeline(req: RenderRequest):
    """
    渲染时间线项目为视频。

    - **project_id**: 要渲染的项目 ID
    - **quality**: 输出质量 (draft / balanced / high)
    - **format**: 输出格式 (mp4 / mov / webm)

    返回 task_id，可通过 `/api/v1/tasks/{task_id}` 查询渲染进度。
    """
    # Validate project exists
    project = _timeline_projects.get(req.project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"项目不存在: {req.project_id}",
        )

    clips = project.get("clips", [])
    if not clips:
        raise HTTPException(
            status_code=400,
            detail="项目中没有任何片段，无法渲染",
        )

    task_id = str(uuid.uuid4())
    model = "timeline-render"

    total_duration = sum(max(0, c.get("end", 5) - c.get("start", 0)) for c in clips)
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
