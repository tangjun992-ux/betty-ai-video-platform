"""
Media store — persist generated media to local storage.

Provider result URLs (KIE / Replicate / ...) are temporary links that expire
or may be unreachable from the user's network. Every completed generation is
therefore downloaded into STORAGE_LOCAL_PATH/generated and its URL rewritten
to the stable /api/v1/media/generated/... path served by the backend.
"""
import logging
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GENERATED_SUBDIR = "generated"
MEDIA_URL_PREFIX = "/api/v1/media"
MAX_DOWNLOAD_BYTES = 500 * 1024 * 1024  # 500MB safety cap
DOWNLOAD_TIMEOUT = 120

_CT_EXT = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
    "image/gif": ".gif", "video/mp4": ".mp4", "video/webm": ".webm",
    "video/quicktime": ".mov", "audio/mpeg": ".mp3", "audio/wav": ".wav",
    "audio/x-wav": ".wav", "audio/mp4": ".m4a", "audio/ogg": ".ogg",
}
_KNOWN_EXTS = set(_CT_EXT.values()) | {".jpeg"}


def _is_external(url: str) -> bool:
    """True for http(s) URLs that are NOT already served by our backend."""
    if not url or not url.startswith(("http://", "https://")):
        return False
    return f"{MEDIA_URL_PREFIX}/" not in url


def _guess_ext(url: str, content_type: Optional[str]) -> str:
    path_ext = os.path.splitext(urlparse(url).path)[1].lower()
    if path_ext in _KNOWN_EXTS:
        return ".jpg" if path_ext == ".jpeg" else path_ext
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in _CT_EXT:
        return _CT_EXT[ct]
    guessed = mimetypes.guess_extension(ct) if ct else None
    return guessed or ".bin"


def localize_media_url(url: str, media_hint: str = "") -> Optional[str]:
    """
    Download an external media URL into local storage.
    Returns the local /api/v1/media/... URL, or None on failure.
    """
    if not _is_external(url):
        return None
    try:
        with httpx.Client(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            content = resp.content
            if not content or len(content) > MAX_DOWNLOAD_BYTES:
                logger.warning("media_store: skip %s (empty or too large)", url[:120])
                return None
            ct = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
            if ct and not ct.startswith(("image/", "video/", "audio/", "application/octet-stream")):
                logger.warning("media_store: skip %s (non-media content-type %s)", url[:120], ct)
                return None
            ext = _guess_ext(url, resp.headers.get("content-type"))
            if ext == ".bin" and media_hint == "image":
                ext = ".jpg"
            elif ext == ".bin" and media_hint == "video":
                ext = ".mp4"

            out_dir = Path(settings.STORAGE_LOCAL_PATH) / GENERATED_SUBDIR
            out_dir.mkdir(parents=True, exist_ok=True)
            name = f"{uuid.uuid4().hex[:12]}{ext}"
            (out_dir / name).write_bytes(content)
            local = f"{MEDIA_URL_PREFIX}/{GENERATED_SUBDIR}/{name}"
            logger.info("media_store: localized %s -> %s", url[:120], local)
            return local
    except Exception as e:
        logger.warning("media_store: failed to localize %s: %s", url[:120], e)
        return None


async def store_upload(db, filename: str, content: bytes, content_type: Optional[str] = None):
    """
    Save an uploaded file into STORAGE_LOCAL_PATH/uploads and register it as
    an Asset so every upload across the platform shows up in the library.
    Returns the Asset row.
    """
    from app.models.asset import Asset

    ext = os.path.splitext(filename or "")[1].lower() or ".bin"
    media_type = (
        "image" if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        else "video" if ext in {".mp4", ".webm", ".mov"}
        else "audio" if ext in {".mp3", ".wav", ".m4a", ".ogg"}
        else "image"
    )

    upload_dir = Path(settings.STORAGE_LOCAL_PATH) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    asset_id = str(uuid.uuid4())
    safe_name = f"{asset_id[:8]}{ext}"
    (upload_dir / safe_name).write_bytes(content)

    asset = Asset(
        asset_id=asset_id,
        media_type=media_type,
        url=f"{MEDIA_URL_PREFIX}/uploads/{safe_name}",
        filename=filename or safe_name,
        size_bytes=len(content),
        content_type=content_type,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


async def backfill_generated_media() -> None:
    """
    One-shot background job (run at startup): localize external provider URLs
    still present in completed tasks so old generations keep working after
    the temporary links expire. Best-effort; failures leave rows untouched.
    """
    import asyncio
    import json

    from sqlalchemy import select
    from sqlalchemy.orm.attributes import flag_modified

    from app.db import async_session
    from app.models.task import Task

    try:
        async with async_session() as db:
            res = await db.execute(select(Task).where(Task.status == "completed"))
            tasks = res.scalars().all()
            migrated = 0
            for t in tasks:
                raw = t.results
                if isinstance(raw, str):
                    try:
                        raw = json.loads(raw)
                    except Exception:
                        continue
                if not isinstance(raw, list):
                    continue
                if not any(
                    isinstance(r, dict) and (_is_external(r.get("url") or r.get("media_url") or "")
                                             or _is_external(r.get("thumbnail") or ""))
                    for r in raw
                ):
                    continue
                updated = await asyncio.to_thread(persist_results, raw)
                t.results = updated
                flag_modified(t, "results")
                migrated += 1
                await db.commit()
            if migrated:
                logger.info("media_store: backfilled %d task(s) with local media", migrated)
    except Exception as e:
        logger.warning("media_store: backfill skipped: %s", e)


def persist_results(results: list) -> list:
    """
    Rewrite external `url`/`thumbnail` fields of generation results to local
    copies. Original provider URL is preserved in `source_url`. Best-effort:
    entries whose download fails keep the external URL.
    """
    if not isinstance(results, list):
        return results
    for r in results:
        if not isinstance(r, dict):
            continue
        url = r.get("url") or r.get("media_url") or ""
        hint = r.get("type", "")
        if _is_external(url):
            local = localize_media_url(url, hint)
            if local:
                r["source_url"] = url
                if r.get("url"):
                    r["url"] = local
                if r.get("media_url"):
                    r["media_url"] = local
        thumb = r.get("thumbnail") or ""
        if _is_external(thumb):
            local_t = localize_media_url(thumb, "image")
            if local_t:
                r["thumbnail"] = local_t
    return results
