"""
Library API — unified content library: user uploads + AI-generated results.

Item id scheme:
  up_<asset_id>          -> Asset row (uploaded file)
  gen_<task_id>_<index>  -> entry <index> in Task.results (generated)
"""
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.config import settings
from app.db import get_db
from app.models.asset import Asset
from app.models.task import Task

router = APIRouter()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTS = {".mp4", ".webm", ".mov"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024    # 10MB
MAX_MEDIA_SIZE = 100 * 1024 * 1024   # 100MB (video/audio)


def _ext_media_type(ext: str) -> Optional[str]:
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    return None


def _safe_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _safe_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _asset_item(a: Asset) -> dict:
    return {
        "id": f"up_{a.asset_id}",
        "source": "upload",
        "media_type": a.media_type,
        "url": a.url,
        "thumbnail": a.thumbnail or (a.url if a.media_type == "image" else None),
        "title": a.filename or "未命名文件",
        "prompt": None,
        "model": None,
        "size_bytes": a.size_bytes,
        "duration": None,
        "created_at": a.created_at.isoformat() if a.created_at else "",
    }


def _generated_items(t: Task) -> list:
    params = _safe_dict(t.parameters)
    ts = t.completed_at or t.created_at
    out = []
    for idx, r in enumerate(_safe_list(t.results)):
        if not isinstance(r, dict):
            continue
        url = r.get("url") or r.get("media_url") or ""
        if not url:
            continue
        model = r.get("model", t.selected_model or "")
        out.append({
            "id": f"gen_{t.task_id}_{idx}",
            "source": "generated",
            "media_type": r.get("type", t.media_type),
            "url": url,
            "thumbnail": r.get("thumbnail") or (url if r.get("type", t.media_type) == "image" else None),
            "title": (t.prompt or "")[:80] or "AI 生成",
            "prompt": t.prompt,
            "model": model.split("/")[-1] if "/" in model else model,
            "size_bytes": None,
            "duration": params.get("duration"),
            "created_at": ts.isoformat() if ts else "",
        })
    return out


@router.get("/", summary="内容库列表")
async def list_library(
    media_type: str = Query(default="all"),      # all | image | video | audio
    source: str = Query(default="all"),          # all | upload | generated
    q: str = Query(default=""),
    sort: str = Query(default="recent"),         # recent | oldest
    limit: int = Query(default=48, le=200),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
):
    items: list = []

    if source in ("all", "upload"):
        res = await db.execute(select(Asset).order_by(Asset.created_at.desc()).limit(1000))
        for a in res.scalars().all():
            try:
                items.append(_asset_item(a))
            except Exception:
                continue

    if source in ("all", "generated"):
        res = await db.execute(
            select(Task).where(Task.status == "completed")
            .order_by(Task.created_at.desc()).limit(1000)
        )
        for t in res.scalars().all():
            try:
                items.extend(_generated_items(t))
            except Exception:
                continue

    kw = q.strip().lower()
    if kw:
        items = [
            it for it in items
            if kw in (it["title"] or "").lower()
            or kw in (it["prompt"] or "").lower()
            or kw in (it["model"] or "").lower()
        ]

    # Tab counts reflect the current source+search scope, computed BEFORE the
    # media_type filter so switching tabs never zeroes the other tab badges
    counts = {
        "all": len(items),
        "image": sum(1 for it in items if it["media_type"] == "image"),
        "video": sum(1 for it in items if it["media_type"] == "video"),
        "audio": sum(1 for it in items if it["media_type"] == "audio"),
        "upload": sum(1 for it in items if it["source"] == "upload"),
        "generated": sum(1 for it in items if it["source"] == "generated"),
    }

    if media_type != "all":
        items = [it for it in items if it["media_type"] == media_type]

    items.sort(key=lambda x: x["created_at"], reverse=(sort != "oldest"))
    total = len(items)
    return {
        "items": items[offset:offset + limit],
        "total": total,
        "counts": counts,
        "limit": limit,
        "offset": offset,
    }


@router.post("/upload", summary="上传到内容库")
async def upload_to_library(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    media_type = _ext_media_type(ext)
    if not media_type:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型 {ext}。支持：图片(jpg/png/webp/gif)、视频(mp4/webm/mov)、音频(mp3/wav/m4a/ogg)",
        )

    content = await file.read()
    max_size = MAX_IMAGE_SIZE if media_type == "image" else MAX_MEDIA_SIZE
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大（{len(content) // 1024 // 1024}MB），上限 {max_size // 1024 // 1024}MB",
        )

    from app.services.media_store import store_upload
    asset = await store_upload(db, file.filename or "", content, file.content_type)
    return _asset_item(asset)


@router.delete("/{item_id}", summary="删除内容库条目")
async def delete_library_item(item_id: str, db: AsyncSession = Depends(get_db)):
    if item_id.startswith("up_"):
        asset_id = item_id[3:]
        res = await db.execute(select(Asset).where(Asset.asset_id == asset_id))
        asset = res.scalar_one_or_none()
        if not asset:
            raise HTTPException(status_code=404, detail="条目不存在")
        # Remove local file (best-effort)
        try:
            prefix = "/api/v1/media/"
            if asset.url.startswith(prefix):
                p = Path(settings.STORAGE_LOCAL_PATH) / asset.url[len(prefix):]
                if p.is_file():
                    p.unlink()
        except Exception:
            pass
        await db.delete(asset)
        await db.commit()
        return {"deleted": item_id}

    if item_id.startswith("gen_"):
        try:
            task_id, idx_str = item_id[4:].rsplit("_", 1)
            idx = int(idx_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的条目 ID")
        res = await db.execute(select(Task).where(Task.task_id == task_id))
        task = res.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="条目不存在")
        results = _safe_list(task.results)
        if idx < 0 or idx >= len(results):
            raise HTTPException(status_code=404, detail="条目不存在")
        results.pop(idx)
        task.results = results
        flag_modified(task, "results")
        await db.commit()
        return {"deleted": item_id}

    raise HTTPException(status_code=400, detail="无效的条目 ID")
