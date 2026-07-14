"""
Lipsync API — AI 唇形同步: 图片 + 音频/文字 → 说话视频
"""
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User
from app.models.task import Task
from app.models.billing import UserBalance, Transaction, TransactionType
from app.auth import resolve_user_id
from app.services.moderation import check_prompt
from app.services.entitlements import lipsync_cost, require_studio_tier
from celery_app import app as celery_app

logger = logging.getLogger(__name__)
router = APIRouter()


class LipsyncResponse(BaseModel):
    task_id: str
    status: str = "queued"
    estimated_time_seconds: int = 30
    estimated_cost_credits: int = 4
    tier: str = "demo"


async def _deduct_lipsync_credits(db: AsyncSession, user_id: int, cost: int, task_id: str) -> bool:
    r = await db.execute(select(UserBalance).where(UserBalance.user_id == user_id))
    balance = r.scalar_one_or_none()
    if balance is None:
        balance = UserBalance(user_id=user_id, credits=5, daily_credits=3, daily_credits_max=3)
        db.add(balance)
        await db.flush()
    total = balance.credits + balance.daily_credits
    if total < cost:
        return False
    remaining = cost
    if balance.daily_credits > 0:
        d = min(balance.daily_credits, remaining)
        balance.daily_credits -= d
        remaining -= d
    if remaining > 0:
        balance.credits -= remaining
    before = total
    after = balance.credits + balance.daily_credits
    db.add(Transaction(
        user_id=user_id, type=TransactionType.CONSUMPTION.value, amount=-cost,
        balance_before=before, balance_after=after, model_used="lipsync",
        description=f"Lipsync task {task_id[:8]}",
    ))
    await db.flush()
    return True


@router.post("/lipsync", response_model=LipsyncResponse, summary="提交唇形同步任务")
async def submit_lipsync(
    image_url: Optional[str] = Form(None),
    audio_url: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    voice_id: str = Form("default"),
    model: str = Form("auto"),
    tier: str = Form("demo"),
    image_file: Optional[UploadFile] = File(None),
    audio_file: Optional[UploadFile] = File(None),
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not image_url and not image_file:
        raise HTTPException(status_code=400, detail="请提供图片 (image_url 或 image_file)")
    if not audio_url and not text and not audio_file:
        raise HTTPException(status_code=400, detail="请提供音频 (audio_url/audio_file) 或文字 (text)")

    tier_norm = (tier or "demo").strip().lower()
    if tier_norm not in ("demo", "studio"):
        raise HTTPException(status_code=400, detail="tier 必须是 demo 或 studio")
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if tier_norm == "studio":
        require_studio_tier(u.role if u else "guest", "Lipsync Studio")
    cost = lipsync_cost(tier_norm)

    if text:
        m = check_prompt(text)
        if not m.allowed:
            raise HTTPException(status_code=400, detail=m.reason)

    from app.services.media_store import store_upload
    uploaded_image_url = image_url
    if image_file:
        content = await image_file.read()
        asset = await store_upload(db, image_file.filename or "image.png", content, image_file.content_type)
        uploaded_image_url = asset.url

    uploaded_audio_url = audio_url
    if audio_file:
        content = await audio_file.read()
        audio_asset = await store_upload(db, audio_file.filename or "audio.mp3", content, audio_file.content_type)
        uploaded_audio_url = audio_asset.url

    task_id = str(uuid.uuid4())
    if not await _deduct_lipsync_credits(db, user_id, cost, task_id):
        raise HTTPException(status_code=402, detail=f"积分不足，需要 {cost} 积分")

    task = Task(
        task_id=task_id,
        user_id=user_id,
        prompt=text or "lipsync",
        media_type="video",
        requested_model=model if tier_norm == "demo" else "lipsync-studio",
        selected_model=model if tier_norm == "demo" else "lipsync-studio",
        parameters={
            "image_url": uploaded_image_url,
            "audio_url": uploaded_audio_url,
            "text": text,
            "voice_id": voice_id,
            "tier": tier_norm,
        },
        estimated_cost=cost,
        status="queued",
    )
    db.add(task)
    await db.commit()

    celery_app.send_task(
        "app.tasks.lipsync_tasks.process_lipsync",
        args=[task_id, uploaded_image_url, uploaded_audio_url, text, voice_id, model],
        queue="video_q",
    )

    return LipsyncResponse(task_id=task_id, estimated_cost_credits=cost, tier=tier_norm)


@router.get("/lipsync/voices", summary="获取可用音色列表")
async def list_voices():
    return {
        "voices": [
            {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓 (女)", "language": "zh-CN", "style": "温柔"},
            {"id": "zh-CN-YunxiNeural", "name": "云希 (男)", "language": "zh-CN", "style": "沉稳"},
            {"id": "zh-CN-XiaoyiNeural", "name": "晓伊 (女)", "language": "zh-CN", "style": "活泼"},
            {"id": "en-US-JennyNeural", "name": "Jenny (女)", "language": "en-US", "style": "Friendly"},
            {"id": "en-US-GuyNeural", "name": "Guy (男)", "language": "en-US", "style": "Professional"},
            {"id": "ja-JP-NanamiNeural", "name": "Nanami (女)", "language": "ja-JP", "style": "Natural"},
        ],
        "default": "zh-CN-XiaoxiaoNeural",
        "tiers": {
            "demo": {"label": "Demo", "credits": 4, "description": "标准唇形同步"},
            "studio": {"label": "Studio", "credits": 10, "description": "高保真口型 · 需 Personal+"},
        },
    }
