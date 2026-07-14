"""
Product entitlements — Demo vs Studio tiers for lipsync / motion (对标 Yapper 分层).

Demo: available to all users at base credit cost.
Studio: higher fidelity / priority; requires personal+ plan (or admin).
"""
from __future__ import annotations

from fastapi import HTTPException

STUDIO_ROLES = frozenset({"personal", "creator", "pro", "admin"})

LIPSYNC_DEMO_COST = 4
LIPSYNC_STUDIO_COST = 10
MOTION_DEMO_COST = 6
MOTION_STUDIO_COST = 14


def user_role(role: str | None) -> str:
    return (role or "guest").lower()


def has_studio(role: str | None) -> bool:
    return user_role(role) in STUDIO_ROLES


def lipsync_cost(tier: str = "demo") -> int:
    return LIPSYNC_STUDIO_COST if tier == "studio" else LIPSYNC_DEMO_COST


def motion_cost(tier: str = "demo") -> int:
    return MOTION_STUDIO_COST if tier == "studio" else MOTION_DEMO_COST


def require_studio_tier(role: str | None, feature: str = "此功能") -> None:
    if not has_studio(role):
        raise HTTPException(
            status_code=402,
            detail=f"{feature} 需要 Personal 及以上套餐（Studio 档）。请升级后使用。",
        )
