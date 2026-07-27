"""
Media upload API — images, videos, and audios for Omni / i2v / lipsync.
Every upload is registered as an Asset so it also appears in the library.
"""
import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.media_store import store_upload

router = APIRouter()

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024
MAX_AUDIO_BYTES = 20 * 1024 * 1024


def _max_for_ext(ext: str) -> int:
    if ext in VIDEO_EXTENSIONS:
        return MAX_VIDEO_BYTES
    if ext in AUDIO_EXTENSIONS:
        return MAX_AUDIO_BYTES
    return MAX_IMAGE_BYTES


def _kind_for_ext(ext: str) -> str:
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    return "image"


@router.post("", summary="上传媒体（图/视/音）")
@router.post("/", include_in_schema=False)
async def upload_media(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Upload reference media for Omni / image-to-video / lipsync."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: {ext}. "
                f"Allowed images={sorted(IMAGE_EXTENSIONS)}, "
                f"videos={sorted(VIDEO_EXTENSIONS)}, "
                f"audios={sorted(AUDIO_EXTENSIONS)}"
            ),
        )

    content = await file.read()
    max_bytes = _max_for_ext(ext)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {len(content)} bytes. Max for {ext}: {max_bytes}",
        )

    asset = await store_upload(db, file.filename or "", content, file.content_type)
    kind = _kind_for_ext(ext)

    return {
        "url": asset.url,
        "filename": asset.filename,
        "size": asset.size_bytes,
        "type": file.content_type or f"{kind}/octet-stream",
        "kind": kind,
        "asset_id": asset.asset_id,
    }
