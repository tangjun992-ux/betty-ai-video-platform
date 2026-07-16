"""Resolve social *page* URLs to extractable media (thumbnail / direct file).

Honesty rules:
- YouTube: oEmbed thumbnail (reliable) or yt-dlp metadata thumbnail.
- TikTok / Instagram / X: best-effort via yt-dlp; IP blocks → clear failure.
- Never invent media; callers must surface honesty fields to the UI.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

import httpx

logger = logging.getLogger(__name__)

_YT_HOSTS = ("youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com")
_TIKTOK_HOSTS = ("tiktok.com", "www.tiktok.com", "vm.tiktok.com")
_IG_HOSTS = ("instagram.com", "www.instagram.com")
_X_HOSTS = ("x.com", "twitter.com", "www.x.com", "www.twitter.com")


def classify_social_platform(url: str) -> Optional[str]:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return None
    if not host:
        return None
    if host in _YT_HOSTS or host.endswith(".youtube.com"):
        return "youtube"
    if any(host == h or host.endswith("." + h) for h in ("tiktok.com",)):
        return "tiktok"
    if any(host == h or host.endswith("." + h) for h in ("instagram.com",)):
        return "instagram"
    if host in _X_HOSTS or host.endswith(".twitter.com"):
        return "x"
    if host.endswith("facebook.com") or host.endswith("fb.watch"):
        return "facebook"
    if host.endswith("douyin.com"):
        return "douyin"
    if host.endswith("xiaohongshu.com") or host.endswith("xhslink.com"):
        return "xiaohongshu"
    return None


def is_social_page_url(url: str) -> bool:
    return classify_social_platform(url) is not None


async def _youtube_oembed_thumbnail(url: str) -> Optional[dict[str, Any]]:
    api = "https://www.youtube.com/oembed"
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(api, params={"url": url, "format": "json"})
            if r.status_code != 200:
                return None
            data = r.json()
            thumb = data.get("thumbnail_url") or ""
            if not thumb:
                return None
            return {
                "ok": True,
                "platform": "youtube",
                "media_url": thumb,
                "media_kind": "image",
                "title": data.get("title") or "",
                "author": data.get("author_name") or "",
                "source": "youtube_oembed",
                "honesty": "YouTube oEmbed 封面图（非原片视频流）；用于 Vision/启发式反推提示词。",
            }
    except Exception as e:
        logger.info("youtube oembed failed: %s", e)
        return None


def _yt_dlp_resolve(url: str, platform: str) -> Optional[dict[str, Any]]:
    try:
        import yt_dlp
    except ImportError:
        logger.warning("yt-dlp not installed — social resolve limited to oEmbed")
        return None

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 20,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        logger.info("yt-dlp resolve failed for %s: %s", platform, e)
        return {
            "ok": False,
            "platform": platform,
            "error": str(e)[:300],
            "honesty": f"{platform} 页面解析失败（网络/反爬/地区限制）。请上传文件或粘贴直链。",
        }

    thumb = info.get("thumbnail") or ""
    # Prefer a reasonably large thumbnail
    for t in info.get("thumbnails") or []:
        u = t.get("url") or ""
        if u and (t.get("height") or 0) >= 360:
            thumb = u
    if not thumb:
        return {
            "ok": False,
            "platform": platform,
            "error": "no thumbnail",
            "honesty": f"已识别 {platform} 链接但未拿到可提取封面。",
        }
    return {
        "ok": True,
        "platform": platform,
        "media_url": thumb,
        "media_kind": "image",
        "title": info.get("title") or "",
        "author": info.get("uploader") or info.get("channel") or "",
        "duration": info.get("duration"),
        "source": "yt_dlp_thumbnail",
        "honesty": (
            f"{platform} 经 yt-dlp 解析封面图（非完整视频下载）；"
            "用于 Prompt Extract，不对标 URL-to-Viral 成片搬运。"
        ),
    }


async def resolve_social_page_to_media(url: str) -> dict[str, Any]:
    """Resolve a social page URL to a publicly fetchable media URL for extract."""
    platform = classify_social_platform(url)
    if not platform:
        return {"ok": False, "error": "not_social", "honesty": "非社媒页面链接"}

    if platform == "youtube":
        oembed = await _youtube_oembed_thumbnail(url)
        if oembed and oembed.get("ok"):
            return oembed
        # Fallback yt-dlp
        return _yt_dlp_resolve(url, platform) or {
            "ok": False,
            "platform": "youtube",
            "honesty": "YouTube 封面解析失败，请上传截图或粘贴图片直链。",
        }

    if platform in ("tiktok", "instagram", "x", "facebook"):
        result = _yt_dlp_resolve(url, platform)
        if result:
            return result
        return {
            "ok": False,
            "platform": platform,
            "honesty": (
                f"暂无法从 {platform} 页面稳定抓取媒体（常见原因：IP 封锁/需登录）。"
                "请上传文件或粘贴可直链访问的图片/视频 URL。"
            ),
        }

    # douyin / xhs — no verified free resolver in this env
    return {
        "ok": False,
        "platform": platform,
        "honesty": f"{platform} 页面抓取未接入可信解析器；请上传文件或直链。",
    }
