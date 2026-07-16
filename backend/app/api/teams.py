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
from app.models.team_balance import TeamBalance
from app.services.credits import _ensure_team_balance, transfer_to_team, is_active_team_member

router = APIRouter()

# Default seat caps by owner plan tier (对标 Creator 5席 / Pro 10席).
SEAT_LIMIT_BY_ROLE = {"creator": 5, "pro": 10, "admin": 20}
DEFAULT_SEAT_LIMIT = 3
TEAM_STARTER_CREDITS = 500


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


def _seat_limit_for_role(role: str | None) -> int:
    return SEAT_LIMIT_BY_ROLE.get((role or "").lower(), DEFAULT_SEAT_LIMIT)


def _team_dict(t: Team, members: list[TeamMember] | None = None, balance: TeamBalance | None = None) -> dict:
    return {
        "team_id": t.team_id,
        "name": t.name,
        "description": t.description,
        "owner_user_id": t.owner_user_id,
        "default_visibility": t.default_visibility,
        "seat_limit": getattr(t, "seat_limit", None) or DEFAULT_SEAT_LIMIT,
        "shared_credits": (balance.credits + getattr(balance, "daily_credits", 0)) if balance else 0,
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
    if user.role not in ("creator", "pro", "admin"):
        raise HTTPException(
            status_code=402,
            detail="团队协作需要 Creator 及以上套餐。请升级后创建团队。",
        )
    vis = req.default_visibility if req.default_visibility in ("private", "team", "public") else "team"
    seats = _seat_limit_for_role(user.role)
    team = Team(
        team_id=str(uuid.uuid4()),
        owner_user_id=user.id,
        name=req.name.strip(),
        description=req.description,
        default_visibility=vis,
        seat_limit=seats,
    )
    owner_member = TeamMember(
        team_id=team.team_id, user_id=user.id, role="owner",
        invite_email=user.email, invite_username=user.username, status="active",
    )
    team_balance = TeamBalance(team_id=team.team_id, credits=TEAM_STARTER_CREDITS, daily_credits=0)
    db.add(team)
    db.add(owner_member)
    db.add(team_balance)
    await db.commit()
    return _team_dict(team, [owner_member], team_balance)


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
        bres = await db.execute(select(TeamBalance).where(TeamBalance.team_id == t.team_id))
        out.append(_team_dict(t, list(mres.scalars().all()), bres.scalar_one_or_none()))
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
    bres = await db.execute(select(TeamBalance).where(TeamBalance.team_id == team_id))
    return _team_dict(team, list(mres.scalars().all()), bres.scalar_one_or_none())


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

    count_res = await db.execute(select(TeamMember).where(TeamMember.team_id == team_id))
    tres = await db.execute(select(Team).where(Team.team_id == team_id))
    team_row = tres.scalar_one_or_none()
    seat_cap = (team_row.seat_limit if team_row else None) or DEFAULT_SEAT_LIMIT
    if len(count_res.scalars().all()) >= seat_cap:
        raise HTTPException(status_code=400, detail=f"团队席位已满（上限 {seat_cap} 人）")

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
        vis = (getattr(p, "visibility", None) or "private").lower()
        # Enforce per-project ACL for team listing:
        # private → owner only; team → this team (or unbound); public → all members
        if vis == "private" and p.user_id != user.id:
            continue
        if vis == "team":
            pid_team = getattr(p, "team_id", None)
            if pid_team and pid_team != team_id:
                continue
        projects.append({
            "project_id": p.project_id,
            "name": p.name,
            "description": p.description,
            "cover": p.cover,
            "owner_user_id": p.user_id,
            "visibility": vis,
            "team_id": getattr(p, "team_id", None),
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


@router.delete("/{team_id}/members/{member_user_id}", summary="移除团队成员")
async def remove_member(
    team_id: str,
    member_user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    me = await db.execute(select(TeamMember).where(
        and_(TeamMember.team_id == team_id, TeamMember.user_id == user.id)))
    my = me.scalar_one_or_none()
    if not my or my.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="仅 owner/admin 可移除成员")
    if member_user_id == user.id:
        raise HTTPException(status_code=400, detail="不能移除自己，请转让所有权后退出")
    target = await db.execute(select(TeamMember).where(
        and_(TeamMember.team_id == team_id, TeamMember.user_id == member_user_id)))
    row = target.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="成员不存在")
    if row.role == "owner":
        raise HTTPException(status_code=400, detail="不能移除团队所有者")
    await db.delete(row)
    await db.commit()
    return {"removed": member_user_id, "team_id": team_id}


class FundTeamRequest(BaseModel):
    amount: int = Field(..., ge=1, le=50_000, description="从个人账户转入团队的积分")


@router.get("/{team_id}/billing", summary="团队共享积分池")
async def team_billing(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await is_active_team_member(db, team_id, user.id):
        raise HTTPException(status_code=403, detail="不是该团队成员")
    bal = await _ensure_team_balance(db, team_id)
    return {
        "team_id": team_id,
        "credits": bal.credits + getattr(bal, "daily_credits", 0),
        "purchased_credits": bal.credits,
        "total_spent": bal.total_spent,
        "total_tasks": bal.total_tasks,
        "total_purchased": bal.total_purchased,
    }


@router.post("/{team_id}/fund", summary="从个人账户充值团队共享池")
async def fund_team(
    team_id: str,
    req: FundTeamRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        new_balance = await transfer_to_team(db, user.id, team_id, req.amount)
    except PermissionError:
        raise HTTPException(status_code=403, detail="不是该团队成员")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return {"team_id": team_id, "credits": new_balance, "transferred": req.amount}


@router.post("/members/accept", summary="接受待处理的团队邀请")
async def accept_pending_invites(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Activate pending invites that match the logged-in user's email or username."""
    res = await db.execute(
        select(TeamMember).where(
            and_(
                TeamMember.status == "pending",
                TeamMember.user_id == 0,
            )
        )
    )
    rows = list(res.scalars().all())
    accepted = []
    email = (user.email or "").lower()
    username = (user.username or "").strip()
    for row in rows:
        match = (
            (row.invite_email and row.invite_email.lower() == email)
            or (row.invite_username and row.invite_username == username)
        )
        if not match:
            continue
        exists = await db.execute(select(TeamMember).where(
            and_(TeamMember.team_id == row.team_id, TeamMember.user_id == user.id, TeamMember.status == "active")))
        if exists.scalar_one_or_none():
            await db.delete(row)
            continue
        row.user_id = user.id
        row.status = "active"
        accepted.append(row.team_id)
    await db.commit()
    return {"accepted": accepted, "count": len(accepted)}
