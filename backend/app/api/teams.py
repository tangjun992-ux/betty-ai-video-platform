"""
Team collaboration — minimal Team + TeamMember API.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models.user import User
from app.models.project import Project
from app.models.team import Team, TeamMember

router = APIRouter()


class CreateTeamRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None
    default_visibility: str = Field("team", description="private | team | public")


class InviteRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    role: str = Field("member", description="admin | member")


class VisibilityRequest(BaseModel):
    visibility: str = Field(..., description="private | team | public")


def _team_dict(t: Team, members: list[TeamMember] | None = None) -> dict:
    return {
        "team_id": t.team_id,
        "name": t.name,
        "description": t.description,
        "owner_user_id": t.owner_user_id,
        "default_visibility": t.default_visibility,
        "created_at": t.created_at.isoformat() if t.created_at else "",
        "members": [
            {
                "user_id": m.user_id,
                "role": m.role,
                "status": m.status,
                "invite_email": m.invite_email,
                "invite_username": m.invite_username,
            }
            for m in (members or [])
        ],
    }


@router.post("/", summary="创建团队")
async def create_team(
    req: CreateTeamRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    vis = req.default_visibility if req.default_visibility in ("private", "team", "public") else "team"
    team = Team(
        team_id=str(uuid.uuid4()),
        owner_user_id=user.id,
        name=req.name.strip(),
        description=req.description,
        default_visibility=vis,
    )
    owner_member = TeamMember(
        team_id=team.team_id, user_id=user.id, role="owner",
        invite_email=user.email, invite_username=user.username, status="active",
    )
    db.add(team)
    db.add(owner_member)
    await db.commit()
    return _team_dict(team, [owner_member])


@router.get("/", summary="我的团队列表")
async def list_teams(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    mem = await db.execute(select(TeamMember).where(TeamMember.user_id == user.id))
    memberships = mem.scalars().all()
    team_ids = [m.team_id for m in memberships]
    if not team_ids:
        return {"teams": []}
    res = await db.execute(select(Team).where(Team.team_id.in_(team_ids)))
    teams = res.scalars().all()
    out = []
    for t in teams:
        mres = await db.execute(select(TeamMember).where(TeamMember.team_id == t.team_id))
        out.append(_team_dict(t, list(mres.scalars().all())))
    return {"teams": out}


@router.get("/{team_id}", summary="团队详情")
async def get_team(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    member = await db.execute(select(TeamMember).where(
        and_(TeamMember.team_id == team_id, TeamMember.user_id == user.id)))
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="不是该团队成员")
    res = await db.execute(select(Team).where(Team.team_id == team_id))
    team = res.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    mres = await db.execute(select(TeamMember).where(TeamMember.team_id == team_id))
    return _team_dict(team, list(mres.scalars().all()))


@router.post("/{team_id}/invite", summary="邀请成员（email / username）")
async def invite_member(
    team_id: str,
    req: InviteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not req.email and not req.username:
        raise HTTPException(status_code=400, detail="请提供 email 或 username")
    me = await db.execute(select(TeamMember).where(
        and_(TeamMember.team_id == team_id, TeamMember.user_id == user.id)))
    my = me.scalar_one_or_none()
    if not my or my.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="仅 owner/admin 可邀请")

    target: User | None = None
    if req.username:
        r = await db.execute(select(User).where(User.username == req.username.strip()))
        target = r.scalar_one_or_none()
    if target is None and req.email:
        r = await db.execute(select(User).where(User.email == req.email.strip().lower()))
        target = r.scalar_one_or_none()

    role = req.role if req.role in ("admin", "member") else "member"
    if target:
        exists = await db.execute(select(TeamMember).where(
            and_(TeamMember.team_id == team_id, TeamMember.user_id == target.id)))
        if exists.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="用户已在团队中")
        member = TeamMember(
            team_id=team_id, user_id=target.id, role=role,
            invite_email=target.email, invite_username=target.username, status="active",
        )
    else:
        member = TeamMember(
            team_id=team_id, user_id=0, role=role,
            invite_email=(req.email or "").strip().lower() or None,
            invite_username=(req.username or "").strip() or None,
            status="pending",
        )
    db.add(member)
    await db.commit()
    return {
        "team_id": team_id,
        "invited": True,
        "status": member.status,
        "user_id": member.user_id,
        "invite_email": member.invite_email,
        "invite_username": member.invite_username,
        "role": member.role,
    }


@router.get("/{team_id}/projects", summary="团队可见项目")
async def team_projects(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    member = await db.execute(select(TeamMember).where(
        and_(TeamMember.team_id == team_id, TeamMember.user_id == user.id)))
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="不是该团队成员")
    tres = await db.execute(select(Team).where(Team.team_id == team_id))
    team = tres.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")

    mres = await db.execute(select(TeamMember).where(
        and_(TeamMember.team_id == team_id, TeamMember.status == "active")))
    member_ids = [m.user_id for m in mres.scalars().all() if m.user_id]
    if not member_ids:
        return {"team_id": team_id, "visibility": team.default_visibility, "projects": []}

    pres = await db.execute(select(Project).where(Project.user_id.in_(member_ids)))
    projects = []
    for p in pres.scalars().all():
        projects.append({
            "project_id": p.project_id,
            "name": p.name,
            "description": p.description,
            "cover": p.cover,
            "owner_user_id": p.user_id,
            "visibility": team.default_visibility,
            "item_count": len(p.items or []),
        })
    return {"team_id": team_id, "visibility": team.default_visibility, "projects": projects}


@router.patch("/{team_id}/visibility", summary="更新团队默认项目可见性")
async def update_visibility(
    team_id: str,
    req: VisibilityRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if req.visibility not in ("private", "team", "public"):
        raise HTTPException(status_code=400, detail="visibility 必须是 private|team|public")
    me = await db.execute(select(TeamMember).where(
        and_(TeamMember.team_id == team_id, TeamMember.user_id == user.id)))
    my = me.scalar_one_or_none()
    if not my or my.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="仅 owner/admin 可修改可见性")
    res = await db.execute(select(Team).where(Team.team_id == team_id))
    team = res.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    team.default_visibility = req.visibility
    await db.commit()
    return {"team_id": team_id, "default_visibility": team.default_visibility}
