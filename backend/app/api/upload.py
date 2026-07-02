"""
Image upload API — upload reference images for image-to-video.
"""
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import settings

router = APIRouter()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/upload", summary="上传图片")
async def upload_image(file: UploadFile = File(...)):
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

    # Save to storage
    upload_dir = Path(settings.STORAGE_LOCAL_PATH) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())[:8]
    safe_name = f"{file_id}{ext}"
    file_path = upload_dir / safe_name
    file_path.write_bytes(content)

    return {
        "url": f"/api/v1/media/uploads/{safe_name}",
        "filename": safe_name,
        "size": len(content),
        "type": file.content_type or "image/png",
    }
