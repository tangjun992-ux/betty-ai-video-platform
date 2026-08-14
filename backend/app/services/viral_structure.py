"""URL-to-Viral structure — placement beats from metadata, not frame reverse.

Honesty:
- Beats come from official oEmbed/title + export placement specs.
- This is NOT reel-to-structure vision, NOT original-video download, NOT IP-Adapter.
"""
from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlencode

from app.export_specs import EXPORT_SPECS, clamp_duration, get_export_spec

HONESTY = (
    "结构来自平台投放规格 + 标题/封面元数据，不是原片逐帧分镜反推，"
    "也不是完整视频下载或搬运。"
)

_PLATFORM_PLACEMENT = {
    "tiktok": "tiktok",
    "douyin": "tiktok",
    "instagram": "reels",
    "youtube": "youtube_shorts",
    "x": "tiktok",
    "facebook": "meta_feed",
    "xiaohongshu": "reels",
}

_BEAT_TEMPLATES: tuple[tuple[str, str, str], ...] = (
    ("hook", "钩子", "开场 0–2s：强视觉停顿 + 一句冲突/利益点"),
    ("body", "展开", "中段：展示主体与场景，运镜稳定"),
    ("cta", "收束", "结尾：行动号召，字幕避开平台 UI 安全区"),
)


def infer_placement(
    platform: Optional[str],
    source_url: str = "",
    duration: Optional[int] = None,
) -> str:
    plat = (platform or "").strip().lower()
    url = (source_url or "").lower()
    if plat == "youtube":
        if "/shorts/" in url:
            return "youtube_shorts"
        if duration and int(duration) > 60:
            return "youtube_landscape"
        return "youtube_shorts"
    return _PLATFORM_PLACEMENT.get(plat, "tiktok")


def extract_from_social_metadata(
    *,
    title: str = "",
    author: str = "",
    platform: str = "",
) -> dict[str, Any]:
    """Heuristic prompt when we only have oEmbed title/author (no thumbnail fetch)."""
    stem = (title or "").strip() or f"{platform or 'social'} short"
    who = (author or "").strip()
    prompt = (
        f"A high-quality vertical short of {stem}"
        + (f", creator style inspired by {who}" if who else "")
        + ", 9:16 composition, cinematic lighting, sharp detail, native social-feed look"
    )
    return {
        "mode": "metadata",
        "media_kind": "video",
        "media_url": "",
        "prompt": prompt,
        "style_tags": ["vertical", "cinematic", "social-feed"],
        "subjects": [stem[:80]],
        "camera": "handheld close-up then pull back",
        "mood": "hook-first",
        "media_type_hint": "video",
        "meta": {"title": title, "author": author, "platform": platform},
        "honesty": (
            "仅社媒官方元数据（标题/作者），未下载原片，未跑 Vision。"
        ),
    }


def build_viral_structure(
    *,
    platform: Optional[str] = None,
    source_url: str = "",
    title: str = "",
    author: str = "",
    prompt: str = "",
    duration: Optional[int] = None,
    style_tags: Optional[list[str]] = None,
    camera: str = "",
    mood: str = "",
    thumbnail_url: str = "",
    source: str = "",
) -> dict[str, Any]:
    placement_id = infer_placement(platform, source_url, duration)
    spec = get_export_spec(placement_id) or dict(EXPORT_SPECS["tiktok"])
    dur = clamp_duration(int(duration or spec.get("duration_default") or 15), spec)
    visual = (prompt or title or "cinematic vertical short").strip()
    tags = [t for t in (style_tags or []) if t][:6]
    tag_phrase = ("，".join(tags) + "风格，") if tags else ""
    cam = (camera or "handheld tracking").strip()
    md = (mood or "energetic").strip()
    hook_src = (title or visual).strip()
    hook_short = hook_src[:80]

    t_hook, t_body, t_cta = 0, max(2, min(3, dur // 3)), max(dur - 3, 4)
    beats = [
        {
            "key": "hook",
            "label": "钩子",
            "t": t_hook,
            "prompt": (
                f"{hook_short} — opening hook, first 2 seconds, {cam}, "
                f"{tag_phrase}{md} mood, punchy contrast"
            ),
            "reason": _BEAT_TEMPLATES[0][2],
        },
        {
            "key": "body",
            "label": "展开",
            "t": t_body,
            "prompt": (
                f"{visual} — mid-beat, {cam}, {tag_phrase}show subject clearly, "
                f"stable framing"
            ),
            "reason": _BEAT_TEMPLATES[1][2],
        },
        {
            "key": "cta",
            "label": "收束",
            "t": t_cta,
            "prompt": (
                f"{visual} — closing beat, {spec.get('cta_hint') or 'call to action'}, "
                f"safe-zone captions, {spec.get('subtitle_style') or 'feed'} titles"
            ),
            "reason": _BEAT_TEMPLATES[2][2],
        },
    ]

    payload = {
        "platform": platform or placement_id,
        "placement": spec["id"],
        "placement_label": spec.get("label") or spec["id"],
        "aspect": spec["aspect_ratio"],
        "duration_sec": dur,
        "width": spec.get("width"),
        "height": spec.get("height"),
        "bgm_preset": spec.get("bgm_preset"),
        "cta_hint": spec.get("cta_hint"),
        "subtitle_style": spec.get("subtitle_style"),
        "title": title,
        "author": author,
        "thumbnail_url": thumbnail_url or "",
        "source": source,
        "hook": beats[0]["prompt"],
        "beats": beats,
        "honesty": HONESTY,
    }
    payload["create_query"] = _create_query(visual, payload, thumbnail_url)
    return payload


def _create_query(prompt: str, viral: dict[str, Any], thumbnail_url: str = "") -> dict[str, str]:
    q: list[tuple[str, str]] = [
        ("prompt", (prompt or "")[:1500]),
        ("duration", str(viral.get("duration_sec") or 15)),
        ("aspect", str(viral.get("aspect") or "9:16")),
        ("placement", str(viral.get("placement") or "tiktok")),
        ("viral", "1"),
    ]
    if thumbnail_url.startswith(("http://", "https://", "/api/")):
        q.append(("ref", thumbnail_url[:500]))
    for beat in viral.get("beats") or []:
        p = (beat.get("prompt") or "").strip()
        if p:
            q.append(("shot", p[:500]))
    return {
        "image": "/create/image?" + urlencode({"prompt": (prompt or "")[:1500]}),
        "video": "/create/video?" + urlencode(q),
        "agent": "/agent?" + urlencode({"brief": (prompt or "")[:1500]}),
    }


def platform_viral_spec(platform: str = "tiktok") -> dict[str, Any]:
    """Public template for a platform — no media required."""
    placement_id = infer_placement(platform)
    spec = get_export_spec(placement_id) or dict(EXPORT_SPECS["tiktok"])
    return {
        "platform": platform,
        "placement": spec["id"],
        "placement_label": spec.get("label"),
        "aspect": spec["aspect_ratio"],
        "duration_default": spec.get("duration_default"),
        "duration_min": spec.get("duration_min"),
        "duration_max": spec.get("duration_max"),
        "cta_hint": spec.get("cta_hint"),
        "bgm_preset": spec.get("bgm_preset"),
        "beats_template": [
            {"key": k, "label": lab, "reason": reason}
            for k, lab, reason in _BEAT_TEMPLATES
        ],
        "honesty": HONESTY,
    }


def list_viral_platforms() -> list[dict[str, Any]]:
    rows = []
    for plat, resolver in (
        ("youtube", "oembed"),
        ("tiktok", "oembed"),
        ("instagram", "best_effort"),
        ("x", "best_effort"),
    ):
        placement = infer_placement(plat)
        spec = EXPORT_SPECS[placement]
        rows.append({
            "platform": plat,
            "placement": placement,
            "label": spec.get("label"),
            "aspect": spec["aspect_ratio"],
            "resolver": resolver,
        })
    return rows
