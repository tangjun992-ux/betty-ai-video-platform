"""
Lipsync API — AI 唇形同步: 图片 + 音频/文字 → 说话视频

对标 yapper.so Lipsyncing 功能。
"""
import os
import uuid
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User
from app.auth import get_current_user
from celery_app import app as celery_app

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Schemas ────────────────────────────────────────────

class LipsyncRequest(BaseModel):
    """唇形同步请求"""
    image_url: Optional[str] = None  # 已有图片 URL
    audio_url: Optional[str] = None  # 已有音频 URL
    text: Optional[str] = None       # 文字转语音
    voice_id: str = "default"        # 音色 ID
    model: str = "auto"              # lipsync 模型


class LipsyncResponse(BaseModel):
    task_id: str
    status: str = "queued"
    estimated_time_seconds: int = 30


# ─── Endpoints ──────────────────────────────────────────

@router.post("/lipsync", response_model=LipsyncResponse, summary="提交唇形同步任务")
async def submit_lipsync(
    image_url: Optional[str] = Form(None),
    audio_url: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    voice_id: str = Form("default"),
    model: str = Form("auto"),
    image_file: Optional[UploadFile] = File(None),
    audio_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    提交唇形同步任务。
    
    - 上传图片 (image_file 或 image_url) + 音频 (audio_url) 或文字 (text)
    - 系统自动调用 TTS 将文字转语音，然后驱动唇形
    - 返回 task_id，可通过 /tasks/{task_id} 查询进度
    """
    if not image_url and not image_file:
        raise HTTPException(status_code=400, detail="请提供图片 (image_url 或 image_file)")
    if not audio_url and not text and not audio_file:
        raise HTTPException(status_code=400, detail="请提供音频 (audio_url/audio_file) 或文字 (text)")

    # Handle file upload
    uploaded_image_url = image_url
    if image_file:
        import aiofiles
        upload_dir = os.path.join("uploads", "lipsync")
        os.makedirs(upload_dir, exist_ok=True)
        ext = os.path.splitext(image_file.filename or "image.png")[1] or ".png"
        filename = f"{uuid.uuid4()}{ext}"
        filepath = os.path.join(upload_dir, filename)
        content = await image_file.read()
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(content)
        uploaded_image_url = f"/uploads/lipsync/{filename}"

    # Handle audio file upload
    uploaded_audio_url = audio_url
    if audio_file:
        import aiofiles
        ext = os.path.splitext(audio_file.filename or "audio.mp3")[1] or ".mp3"
        audio_filename = f"{uuid.uuid4()}{ext}"
        audio_filepath = os.path.join(upload_dir, audio_filename)
        content = await audio_file.read()
        async with aiofiles.open(audio_filepath, "wb") as f:
            await f.write(content)
        uploaded_audio_url = f"/uploads/lipsync/{audio_filename}"

    # Create task
    task_id = str(uuid.uuid4())
    
    # Store task in DB
    from sqlalchemy import text
    await db.execute(
        text("""
            INSERT INTO tasks (task_id, user_id, status, media_type, model, 
                             progress, current_stage, created_at, metadata)
            VALUES (:tid, :uid, 'queued', 'video', :model, 0, 'lipsync_init', 
                   datetime('now'), :meta)
        """),
        {
            "tid": task_id,
            "uid": current_user.id,
            "model": model,
            "meta": json.dumps({
                "image_url": uploaded_image_url,
                "audio_url": uploaded_audio_url,
                "text": text,
                "voice_id": voice_id,
            }),
        },
    )
    await db.commit()

    # Dispatch Celery task
    celery_app.send_task(
        "app.tasks.lipsync_tasks.process_lipsync",
        args=[task_id, uploaded_image_url, uploaded_audio_url, text, voice_id, model],
        queue="video_q",
    )

    return LipsyncResponse(task_id=task_id)


@router.get("/lipsync/voices", summary="获取可用音色列表")
async def list_voices():
    """返回可用的 TTS 音色列表。"""
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
    }
