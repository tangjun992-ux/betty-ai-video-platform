"""Asset gateway — make local/private media reachable by upstream providers."""
from __future__ import annotations

import logging
import os
import uuid

from app.adapters.demo_provider import _local_media_path

logger = logging.getLogger(__name__)


async def upload_public_url(
    data: bytes,
    *,
    filename: str = "upload.png",
    content_type: str = "image/png",
    upload_path: str = "betty/uploads",
) -> str:
    """Upload bytes to a public URL providers can fetch (KIE upload host today)."""
    from app.adapters.kie_adapter import KieAdapter
    return await KieAdapter().upload_public_url(
        data, filename=filename, content_type=content_type, upload_path=upload_path,
    )


async def publicize_url(
    url: str,
    *,
    default_content_type: str = "image/png",
    trace_id: str = "",
) -> str:
    """If *url* is local (/api/v1/media) or localhost, upload and return public URL."""
    if not url:
        return url
    if url.startswith(("http://", "https://")):
        if "/api/v1/media" not in url and "localhost" not in url and "127.0.0.1" not in url:
            return url
    p = _local_media_path(url)
    if not p:
        return url
    with open(p, "rb") as f:
        data = f.read()
    ext = os.path.splitext(p)[1].lstrip(".") or "png"
    ct = default_content_type
    if default_content_type.startswith("image"):
        ct = f"image/{ext}" if ext in ("png", "jpg", "jpeg", "webp", "gif") else default_content_type
    elif default_content_type.startswith("audio"):
        ct = f"audio/{ext}" if ext in ("mp3", "wav", "m4a", "ogg") else default_content_type
    fname = f"pub_{uuid.uuid4().hex[:8]}.{ext}"
    logger.debug("[gateway/assets] publicize %s trace=%s", p, trace_id or "-")
    return await upload_public_url(data, filename=fname, content_type=ct)
