"""
Prompt Extractor — reverse-prompt from image/video (Yapper Extractor parity).

Strategy:
  1. Vision LLM via OpenAI-compatible chat (OPENAI_API_KEY or KIE_API_KEY) when available
  2. Deterministic local heuristic fallback (never fake a paid vision success)
"""
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a prompt engineer for an AI content studio. "
    "Given media, write a production-ready generation prompt that would recreate "
    "the scene. Reply JSON only: "
    '{"prompt":"...","style_tags":["..."],"subjects":["..."],'
    '"camera":"...","mood":"...","media_type_hint":"image|video"}'
)


def _llm_credentials() -> Optional[tuple[str, str]]:
    if getattr(settings, "OPENAI_API_KEY", None):
        base = (settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        return settings.OPENAI_API_KEY, base
    if getattr(settings, "KIE_API_KEY", None):
        return settings.KIE_API_KEY, "https://api.kie.ai/v1"
    return None


async def _vision_extract(media_url: str, *, media_kind: str) -> Optional[dict[str, Any]]:
    creds = _llm_credentials()
    if not creds:
        return None
    api_key, base = creds
    user_content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"Extract a detailed {media_kind} generation prompt from this media. "
                "Include subject, setting, lighting, style, and camera language."
            ),
        },
        {"type": "image_url", "image_url": {"url": media_url}},
    ]
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": _SYSTEM},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.4,
                    "response_format": {"type": "json_object"},
                },
            )
            if resp.status_code >= 400:
                logger.warning("prompt_extract vision HTTP %s: %s", resp.status_code, resp.text[:200])
                return None
            data = resp.json()
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            import json

            parsed = json.loads(content)
            if not isinstance(parsed, dict) or not parsed.get("prompt"):
                return None
            return parsed
    except Exception as e:
        logger.warning("prompt_extract vision failed: %s", e)
        return None


def _local_path_from_url(url: str) -> Optional[Path]:
    """Map /api/v1/media/... or file:// to a local path when possible."""
    if not url:
        return None
    if url.startswith("file://"):
        return Path(url[7:])
    parsed = urlparse(url)
    path = parsed.path or ""
    # Common local media mount
    for marker in ("/api/v1/media/", "/media/"):
        if marker in path:
            rel = path.split(marker, 1)[1]
            candidates = [
                Path("media") / rel,
                Path("uploads") / rel,
                Path("backend/media") / rel,
                Path("/workspace/backend/media") / rel,
                Path("/workspace/backend/uploads") / rel,
            ]
            for c in candidates:
                if c.is_file():
                    return c
    return None


def _heuristic_extract(media_url: str, *, media_kind: str, filename: str = "") -> dict[str, Any]:
    """Honest local fallback — structured prompt from filename + optional PIL stats."""
    name = filename or Path(urlparse(media_url).path).name or "media"
    stem = Path(name).stem.replace("_", " ").replace("-", " ").strip() or "subject"
    w = h = None
    colors: list[str] = []
    local = _local_path_from_url(media_url)
    if local and local.is_file() and media_kind == "image":
        try:
            from PIL import Image

            with Image.open(local) as im:
                im = im.convert("RGB")
                w, h = im.size
                small = im.resize((32, 32))
                pixels = list(small.getdata())
                # Simple dominant buckets
                buckets: dict[str, int] = {}
                for r, g, b in pixels:
                    key = f"#{(r//32)*32:02x}{(g//32)*32:02x}{(b//32)*32:02x}"
                    buckets[key] = buckets.get(key, 0) + 1
                colors = [c for c, _ in sorted(buckets.items(), key=lambda x: -x[1])[:3]]
        except Exception:
            pass

    aspect = "square"
    if w and h:
        ratio = w / max(h, 1)
        if ratio > 1.3:
            aspect = "landscape widescreen"
        elif ratio < 0.75:
            aspect = "portrait"

    color_phrase = (", ".join(colors) + " color palette") if colors else "natural color grading"
    prompt = (
        f"A high-quality {media_kind} of {stem}, {aspect} composition, "
        f"{color_phrase}, sharp detail, professional lighting, cinematic look"
    )
    return {
        "prompt": prompt,
        "style_tags": ["cinematic", "professional", aspect],
        "subjects": [stem],
        "camera": "medium shot" if media_kind == "image" else "smooth tracking shot",
        "mood": "polished",
        "media_type_hint": media_kind,
        "dimensions": {"width": w, "height": h} if w and h else None,
        "dominant_colors": colors,
    }


def guess_media_kind(url: str, content_type: str = "", filename: str = "") -> str:
    ct = (content_type or "").lower()
    name = (filename or url or "").lower()
    if ct.startswith("video/") or any(name.endswith(ext) for ext in (".mp4", ".webm", ".mov", ".mkv")):
        return "video"
    return "image"


def is_unsupported_social_page_url(url: str) -> bool:
    """True for social *page* URLs we refuse to pretend we can scrape."""
    from urllib.parse import urlparse
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    if not host:
        return False
    if host.endswith("douyin.com") or host.endswith("xiaohongshu.com") or host.endswith("xhslink.com"):
        return True
    return any(host == h or host.endswith("." + h) for h in (
        "tiktok.com", "instagram.com", "x.com", "twitter.com",
        "youtube.com", "youtu.be", "facebook.com", "fb.watch",
    ))


async def extract_prompt_from_media(
    media_url: str,
    *,
    media_kind: Optional[str] = None,
    filename: str = "",
    content_type: str = "",
    prefer_vision: bool = True,
) -> dict[str, Any]:
    kind = media_kind or guess_media_kind(media_url, content_type, filename)
    mode = "heuristic"
    payload: Optional[dict[str, Any]] = None

    # Vision models typically need a publicly fetchable image URL.
    # For video, we still attempt vision if URL looks like an image poster; else heuristic.
    if prefer_vision and kind == "image" and media_url.startswith("http"):
        payload = await _vision_extract(media_url, media_kind=kind)
        if payload:
            mode = "vision"

    if not payload:
        payload = _heuristic_extract(media_url, media_kind=kind, filename=filename)
        mode = "heuristic"

    return {
        "mode": mode,
        "media_kind": kind,
        "media_url": media_url,
        "prompt": str(payload.get("prompt") or "").strip(),
        "style_tags": payload.get("style_tags") or [],
        "subjects": payload.get("subjects") or [],
        "camera": payload.get("camera") or "",
        "mood": payload.get("mood") or "",
        "media_type_hint": payload.get("media_type_hint") or kind,
        "meta": {
            "dimensions": payload.get("dimensions"),
            "dominant_colors": payload.get("dominant_colors"),
            "mime": content_type or mimetypes.guess_type(filename or media_url)[0],
        },
        "honesty": (
            "vision LLM reverse-prompt"
            if mode == "vision"
            else "local heuristic fallback (no vision key or vision failed) — not a paid model caption"
        ),
    }
