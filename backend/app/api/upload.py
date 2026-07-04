"""
Image upload API — upload reference images for image-to-video.
Every upload is registered as an Asset so it also appears in the library.
"""
import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.media_store import store_upload

router = APIRouter()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("", summary="上传图片")
@router.post("/", include_in_schema=False)
async def upload_image(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Upload an image for use as reference in image-to-video generation."""
    # Validate extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {len(content)} bytes. Max: {MAX_FILE_SIZE}",
        )

    asset = await store_upload(db, file.filename or "", content, file.content_type)

    return {
        "url": asset.url,
        "filename": asset.filename,
        "size": asset.size_bytes,
        "type": file.content_type or "image/png",
        "asset_id": asset.asset_id,
    }
