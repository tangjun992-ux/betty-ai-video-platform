"""
Settings API — user preferences, API keys, notifications, billing overview.
对标 yapper.so 设置页面架构。
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models.user import User
from app.models.billing import UserBalance, Transaction
from app.auth import get_current_user

router = APIRouter()


# ─── Schemas ────────────────────────────────────────────

class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[str] = None


class UserPreferences(BaseModel):
    """User preferences stored in metadata_json field."""
    default_model: str = "auto"
    default_quality: str = "balanced"  # fast | balanced | high
    default_resolution: str = "1080x1080"
    language: str = "zh-CN"
    theme: str = "dark"  # dark | light
    auto_enhance_prompt: bool = True
    save_history: bool = True


class NotificationSettings(BaseModel):
    email_task_complete: bool = True
    email_weekly_digest: bool = False
    email_promotions: bool = False
    push_task_complete: bool = True
    push_credits_low: bool = True


class SettingsResponse(BaseModel):
    profile: dict
    preferences: UserPreferences
    notifications: NotificationSettings
    billing: dict
    api_keys: list


class SaveSettingsRequest(BaseModel):
    profile: Optional[UserProfileUpdate] = None
    preferences: Optional[UserPreferences] = None
    notifications: Optional[NotificationSettings] = None


# ─── Defaults ───────────────────────────────────────────

DEFAULT_PREFERENCES = UserPreferences()
DEFAULT_NOTIFICATIONS = NotificationSettings()


def _get_user_preferences(user: User) -> UserPreferences:
    """Parse preferences from metadata_json, falling back to defaults."""
    try:
        if user.metadata_json:
            data = json.loads(user.metadata_json)
            prefs = data.get("preferences", {})
            return UserPreferences(**prefs) if prefs else DEFAULT_PREFERENCES
    except (json.JSONDecodeError, TypeError):
        pass
    # fallback to column-based prefs
    return UserPreferences(
        default_model=user.default_model or "auto",
        default_quality=user.default_quality or "balanced",
    )


def _get_user_notifications(user: User) -> NotificationSettings:
    """Parse notification settings from metadata_json."""
    try:
        if user.metadata_json:
            data = json.loads(user.metadata_json)
            notif = data.get("notifications", {})
            return NotificationSettings(**notif) if notif else DEFAULT_NOTIFICATIONS
    except (json.JSONDecodeError, TypeError):
        pass
    return DEFAULT_NOTIFICATIONS


def _save_user_metadata(user: User, key: str, value: dict):
    """Save a section of metadata_json."""
    try:
        current = json.loads(user.metadata_json) if user.metadata_json else {}
    except (json.JSONDecodeError, TypeError):
        current = {}
    current[key] = value
    user.metadata_json = json.dumps(current, ensure_ascii=False)


# ─── Endpoints ──────────────────────────────────────────

@router.get("", summary="获取所有设置")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all user settings: profile, preferences, notifications, billing, api_keys."""
    # Billing info
    bal_result = await db.execute(
        select(UserBalance).where(UserBalance.user_id == current_user.id)
    )
    balance = bal_result.scalar_one_or_none()

    # Transaction count for billing summary
    txn_result = await db.execute(
        select(Transaction).where(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc()).limit(10)
    )
    transactions = txn_result.scalars().all()

    billing = {
        "credits": balance.credits if balance else 0,
        "daily_credits": balance.daily_credits if balance else 5,
        "daily_credits_max": balance.daily_credits_max if balance else 10,
        "total_spent": balance.total_spent if balance else 0,
        "total_tasks": balance.total_tasks if balance else 0,
        "total_purchased": balance.total_purchased if balance else 0,
        "plan": current_user.role or "free",
        "recent_transactions": [
            {
                "id": t.id,
                "type": t.type,
                "amount": t.amount,
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in transactions
        ],
    }

    # API keys (currently stored in metadata_json)
    try:
        meta = json.loads(current_user.metadata_json) if current_user.metadata_json else {}
        api_keys = meta.get("api_keys", [])
    except (json.JSONDecodeError, TypeError):
        api_keys = []

    return SettingsResponse(
        profile={
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "display_name": current_user.display_name,
            "avatar_url": current_user.avatar_url,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
        preferences=_get_user_preferences(current_user),
        notifications=_get_user_notifications(current_user),
        billing=billing,
        api_keys=api_keys,
    )


@router.put("", summary="保存设置")
async def save_settings(
    req: SaveSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user settings. Only provided sections are updated."""
    updated_sections = []

    # Update profile
    if req.profile:
        profile = req.profile
        if profile.display_name is not None:
            current_user.display_name = profile.display_name
        if profile.avatar_url is not None:
            current_user.avatar_url = profile.avatar_url
        if profile.email is not None:
            # Check uniqueness
            existing = await db.execute(
                select(User).where(User.email == profile.email, User.id != current_user.id)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="邮箱已被占用")
            current_user.email = profile.email
        updated_sections.append("profile")

    # Update preferences
    if req.preferences:
        prefs = req.preferences
        _save_user_metadata(current_user, "preferences", prefs.model_dump())
        # Also update column-level defaults
        if prefs.default_model:
            current_user.default_model = prefs.default_model
        if prefs.default_quality:
            current_user.default_quality = prefs.default_quality
        updated_sections.append("preferences")

    # Update notifications
    if req.notifications:
        notif = req.notifications
        _save_user_metadata(current_user, "notifications", notif.model_dump())
        updated_sections.append("notifications")

    await db.flush()

    return {
        "message": "设置已保存",
        "updated": updated_sections,
        "profile": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "display_name": current_user.display_name,
            "avatar_url": current_user.avatar_url,
            "role": current_user.role,
        },
    }


# ─── API Key management ─────────────────────────────────

class CreateApiKeyRequest(BaseModel):
    name: str
    provider: str = "custom"  # custom | openai | kie
    key: str


@router.post("/api-keys", summary="添加 API 密钥")
async def create_api_key(
    req: CreateApiKeyRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        meta = json.loads(current_user.metadata_json) if current_user.metadata_json else {}
    except (json.JSONDecodeError, TypeError):
        meta = {}

    api_keys = meta.get("api_keys", [])
    import uuid
    new_key = {
        "id": str(uuid.uuid4()),
        "name": req.name,
        "provider": req.provider,
        "key_preview": req.key[:4] + "****" + req.key[-4:] if len(req.key) > 8 else "****",
        "created_at": None,  # Will be set on the server side
    }
    api_keys.append(new_key)
    meta["api_keys"] = api_keys
    current_user.metadata_json = json.dumps(meta, ensure_ascii=False)

    return {"message": "API 密钥已添加", "key": new_key}


@router.delete("/api-keys/{key_id}", summary="删除 API 密钥")
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        meta = json.loads(current_user.metadata_json) if current_user.metadata_json else {}
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=404, detail="无 API 密钥")

    api_keys = meta.get("api_keys", [])
    original_len = len(api_keys)
    api_keys = [k for k in api_keys if k["id"] != key_id]

    if len(api_keys) == original_len:
        raise HTTPException(status_code=404, detail="密钥不存在")

    meta["api_keys"] = api_keys
    current_user.metadata_json = json.dumps(meta, ensure_ascii=False)

    return {"message": "API 密钥已删除"}


@router.post("/notifications/test", summary="发送测试通知（验证邮件配置）")
async def test_notification(
    current_user: User = Depends(get_current_user),
):
    """Dry-run / best-effort SMTP test using the same path as task-complete emails."""
    notif = _get_user_notifications(current_user)
    if not notif.email_task_complete:
        return {
            "sent": False,
            "reason": "email_task_complete_disabled",
            "hint": "请先开启「任务完成邮件」通知偏好",
        }
    email = (current_user.email or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="账户未设置邮箱")
    import os
    import logging
    logger = logging.getLogger(__name__)
    logger.info("notification_test: user=%s email=%s", current_user.id, email)
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_from = os.getenv("SMTP_FROM", "").strip()
    if not smtp_host or not smtp_from:
        return {
            "sent": False,
            "reason": "smtp_missing",
            "logged": True,
            "to": email,
            "hint": "配置 SMTP_HOST / SMTP_FROM 后即可投递",
        }
    try:
        import smtplib
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["Subject"] = "betty 通知测试"
        msg["From"] = smtp_from
        msg["To"] = email
        msg.set_content("这是一封 betty 任务完成通知的测试邮件。若收到说明 SMTP 配置正常。")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")
        use_tls = os.getenv("SMTP_TLS", "true").lower() == "true"
        with smtplib.SMTP(smtp_host, port, timeout=10) as smtp:
            if use_tls:
                smtp.starttls()
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
        return {"sent": True, "to": email}
    except Exception as e:
        return {"sent": False, "reason": str(e), "to": email}
