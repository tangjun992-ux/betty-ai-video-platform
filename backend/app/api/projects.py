"""
Projects API — organize creations into named projects/collections.
对标 Runway / Yapper 的 Projects：把上传与生成的作品归入项目，便于管理与复用。
"""
import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db import get_db
from app.models.project import Project
from app.models.user import User
from app.auth import get_optional_user, resolve_user_id

router = APIRouter()


class ProjectItem(BaseModel):
    item_id: str
    url: str
    thumbnail: Optional[str] = None
    media_type: str = "image"
    title: Optional[str] = None


class CreateProject(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class UpdateProject(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None


def _serialize(p: Project) -> dict:
    items = p.items if isinstance(p.items, list) else []
    return {
        "id": p.project_id,
        "name": p.name,
        "description": p.description,
        "cover": p.cover or (items[0].get("thumbnail") or items[0].get("url") if items else None),
        "item_count": len(items),
        "items": items,
        "created_at": p.created_at.isoformat() if p.created_at else "",
        "updated_at": p.updated_at.isoformat() if p.updated_at else "",
    }


@router.get("/", summary="项目列表")
async def list_projects(current_user: Optional[User] = Depends(get_optional_user),
                        db: AsyncSession = Depends(get_db)):
    uid = current_user.id if current_user else 0
    res = await db.execute(select(Project).where(Project.user_id == uid).order_by(Project.updated_at.desc()))
    return {"projects": [_serialize(p) for p in res.scalars().all()]}


@router.post("/", summary="创建项目")
async def create_project(req: CreateProject, current_user: Optional[User] = Depends(get_optional_user),
                         db: AsyncSession = Depends(get_db)):
    p = Project(project_id=str(uuid.uuid4()), user_id=current_user.id if current_user else 0,
                name=req.name.strip(), description=(req.description or "").strip() or None, items=[])
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return _serialize(p)


async def _get(db: AsyncSession, project_id: str) -> Project:
    res = await db.execute(select(Project).where(Project.project_id == project_id))
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    return p


async def _get_owned(db: AsyncSession, project_id: str, user_id: int) -> Project:
    p = await _get(db, project_id)
    if (p.user_id or 0) != user_id:
        raise HTTPException(status_code=403, detail="无权访问此项目")
    return p


@router.get("/{project_id}", summary="项目详情")
async def get_project(
    project_id: str,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    return _serialize(await _get_owned(db, project_id, user_id))


@router.patch("/{project_id}", summary="更新项目信息")
async def update_project(
    project_id: str,
    req: UpdateProject,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    p = await _get_owned(db, project_id, user_id)
    if req.name is not None:
        p.name = req.name.strip() or p.name
    if req.description is not None:
        p.description = req.description.strip() or None
    await db.commit()
    await db.refresh(p)
    return _serialize(p)


@router.post("/{project_id}/items", summary="向项目添加作品")
async def add_item(
    project_id: str,
    item: ProjectItem,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    p = await _get_owned(db, project_id, user_id)
    items = list(p.items or [])
    if any(it.get("item_id") == item.item_id for it in items):
        return _serialize(p)  # already in project (idempotent)
    items.append(item.model_dump())
    p.items = items
    if not p.cover:
        p.cover = item.thumbnail or item.url
    flag_modified(p, "items")
    await db.commit()
    await db.refresh(p)
    return _serialize(p)


@router.delete("/{project_id}/items/{item_id}", summary="从项目移除作品")
async def remove_item(
    project_id: str,
    item_id: str,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    p = await _get_owned(db, project_id, user_id)
    items = [it for it in (p.items or []) if it.get("item_id") != item_id]
    p.items = items
    if p.cover and not any((it.get("thumbnail") == p.cover or it.get("url") == p.cover) for it in items):
        p.cover = (items[0].get("thumbnail") or items[0].get("url")) if items else None
    flag_modified(p, "items")
    await db.commit()
    await db.refresh(p)
    return _serialize(p)


@router.delete("/{project_id}", summary="删除项目")
async def delete_project(
    project_id: str,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    p = await _get_owned(db, project_id, user_id)
    await db.delete(p)
    await db.commit()
    return {"deleted": project_id}
