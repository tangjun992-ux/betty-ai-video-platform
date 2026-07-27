"""
Authentication API — register, login, profile.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.db import get_db
from app.models.user import User
from app.models.billing import UserBalance
from app.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, get_optional_user,
)

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    """Accept email (preferred, matches frontend) or username for backward compat."""
    password: str
    email: str | None = None
    username: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def _user_payload(user: User, credits: int | None = None) -> dict:
    payload = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "name": user.display_name or user.username,
        "role": user.role,
    }
    if credits is not None:
        payload["credits"] = credits
    return payload


@router.post("/register", summary="注册")
async def register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    # Check if username exists
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    existing_email = await db.execute(select(User).where(User.email == req.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=get_password_hash(req.password),
        display_name=req.display_name or req.username,
    )
    db.add(user)
    await db.flush()

    # Initialize balance with free credits
    balance = UserBalance(user_id=user.id, credits=10, daily_credits=5, daily_credits_max=10)
    db.add(balance)
    await db.flush()

    token = create_access_token({"sub": str(user.id), "username": user.username})

    return AuthResponse(
        access_token=token,
        user=_user_payload(user, credits=10),
    )


@router.post("/login", summary="登录")
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login by email (preferred) or username. Frontend sends {email, password}."""
    identifier = (req.email or req.username or "").strip()
    if not identifier:
        raise HTTPException(status_code=400, detail="请输入邮箱或用户名")

    user = None
    if "@" in identifier:
        result = await db.execute(select(User).where(User.email == identifier))
        user = result.scalar_one_or_none()
    if user is None:
        result = await db.execute(select(User).where(User.username == identifier))
        user = result.scalar_one_or_none()
    # Also try email lookup when username field was used without @
    if user is None and req.username and "@" not in identifier:
        result = await db.execute(select(User).where(User.email == identifier))
        user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="邮箱/用户名或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已停用")

    token = create_access_token({"sub": str(user.id), "username": user.username})

    return AuthResponse(
        access_token=token,
        user=_user_payload(user),
    )


@router.get("/me", summary="获取当前用户信息")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }


@router.post("/me/daily-claim", summary="领取每日免费积分")
async def claim_daily_credits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.billing import UserBalance, Transaction, TransactionType
    from datetime import date

    result = await db.execute(select(UserBalance).where(UserBalance.user_id == current_user.id))
    balance = result.scalar_one_or_none()

    if not balance:
        raise HTTPException(status_code=404, detail="账户不存在")

    today = date.today()
    if balance.last_reset_date and balance.last_reset_date.date() >= today:
        raise HTTPException(status_code=400, detail="今日已领取")

    old_credits = balance.credits
    balance.credits += balance.daily_credits
    balance.last_reset_date = datetime.now(timezone.utc)

    txn = Transaction(
        user_id=current_user.id,
        type=TransactionType.DAILY_FREE.value,
        amount=balance.daily_credits,
        balance_before=old_credits,
        balance_after=balance.credits,
        description="每日免费积分",
    )
    db.add(txn)
    await db.flush()

    return {
        "claimed_credits": balance.daily_credits,
        "total_credits": balance.credits,
        "next_claim": "明天",
    }
