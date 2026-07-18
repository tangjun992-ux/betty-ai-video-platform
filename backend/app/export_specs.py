"""Ad placement export specs — Meta / TikTok / Reels / Shorts.

Maps channel placements to canvas, aspect, recommended duration, and packaging hints.
Pixel rendering still uses ``demo_provider.EXPORT_PRESETS``; this module adds
**placement naming + validation** for "可试投" delivery.
"""
from __future__ import annotations

from typing import Any

# Placement id → policy
EXPORT_SPECS: dict[str, dict[str, Any]] = {
    "meta_feed": {
        "id": "meta_feed",
        "label": "Meta 信息流",
        "channel": "meta",
        "aspect_ratio": "16:9",
        "export_preset": "landscape_16_9",
        "width": 1920,
        "height": 1080,
        "duration_min": 6,
        "duration_max": 15,
        "duration_default": 15,
        "subtitle_style": "impact",
        "bgm_preset": "upbeat",
        "cta_hint": "了解更多 · 立即选购",
        "notes": "Facebook/Instagram Feed landscape ads",
    },
    "meta_stories": {
        "id": "meta_stories",
        "label": "Meta Stories",
        "channel": "meta",
        "aspect_ratio": "9:16",
        "export_preset": "portrait_9_16",
        "width": 1080,
        "height": 1920,
        "duration_min": 5,
        "duration_max": 15,
        "duration_default": 15,
        "subtitle_style": "bold",
        "bgm_preset": "hype",
        "cta_hint": "滑动查看 · 立即选购",
        "notes": "IG/FB Stories full-bleed vertical",
    },
    "tiktok": {
        "id": "tiktok",
        "label": "TikTok / 抖音",
        "channel": "tiktok",
        "aspect_ratio": "9:16",
        "export_preset": "portrait_9_16",
        "width": 1080,
        "height": 1920,
        "duration_min": 8,
        "duration_max": 30,
        "duration_default": 15,
        "subtitle_style": "feed",
        "bgm_preset": "energetic",
        "cta_hint": "同款安利 · 评论区见",
        "notes": "Native feed vertical; keep safe zone for UI chrome",
    },
    "reels": {
        "id": "reels",
        "label": "Instagram Reels",
        "channel": "instagram",
        "aspect_ratio": "9:16",
        "export_preset": "portrait_9_16",
        "width": 1080,
        "height": 1920,
        "duration_min": 7,
        "duration_max": 30,
        "duration_default": 15,
        "subtitle_style": "neon",
        "bgm_preset": "hype",
        "cta_hint": "点击主页 · 同款链接",
        "notes": "Reels vertical; punchy captions",
    },
    "youtube_shorts": {
        "id": "youtube_shorts",
        "label": "YouTube Shorts",
        "channel": "youtube",
        "aspect_ratio": "9:16",
        "export_preset": "portrait_9_16",
        "width": 1080,
        "height": 1920,
        "duration_min": 8,
        "duration_max": 60,
        "duration_default": 20,
        "subtitle_style": "caption_box",
        "bgm_preset": "upbeat",
        "cta_hint": "订阅了解更多",
        "notes": "Shorts vertical ≤60s",
    },
    "youtube_landscape": {
        "id": "youtube_landscape",
        "label": "YouTube 横版",
        "channel": "youtube",
        "aspect_ratio": "16:9",
        "export_preset": "landscape_16_9",
        "width": 1920,
        "height": 1080,
        "duration_min": 10,
        "duration_max": 60,
        "duration_default": 30,
        "subtitle_style": "ad",
        "bgm_preset": "cinematic",
        "cta_hint": "了解更多",
        "notes": "In-stream / discovery landscape",
    },
}

# Scenario → default placement when user doesn't pick
SCENARIO_DEFAULT_PLACEMENT: dict[str, str] = {
    "product_ad": "meta_feed",
    "product_commercial": "youtube_landscape",
    "ugc": "tiktok",
    "micro_drama": "reels",
    "anime": "youtube_landscape",
    "talking_avatar": "tiktok",
}


def list_export_specs() -> list[dict[str, Any]]:
    return [dict(v) for v in EXPORT_SPECS.values()]


def get_export_spec(placement: str | None) -> dict[str, Any] | None:
    if not placement:
        return None
    return EXPORT_SPECS.get((placement or "").strip().lower())


def resolve_placement(scenario: str | None, placement: str | None = None) -> dict[str, Any]:
    """Return a concrete placement spec (fallback to scenario default or meta_feed)."""
    spec = get_export_spec(placement)
    if spec:
        return dict(spec)
    sid = (scenario or "").strip().lower()
    pid = SCENARIO_DEFAULT_PLACEMENT.get(sid, "meta_feed")
    return dict(EXPORT_SPECS[pid])


def clamp_duration(seconds: int, spec: dict[str, Any]) -> int:
    lo = int(spec.get("duration_min") or 5)
    hi = int(spec.get("duration_max") or 60)
    return max(lo, min(int(seconds or spec.get("duration_default") or 15), hi))


def validate_plan_against_placement(plan: dict, placement: str | None) -> list[str]:
    """Return human-readable validation warnings (empty = ok for试投)."""
    warnings: list[str] = []
    spec = get_export_spec(placement) or resolve_placement(plan.get("scenario"), placement)
    aspect = None
    export_preset = None
    for s in plan.get("steps") or []:
        if s.get("action") == "compose":
            params = s.get("params") or {}
            aspect = params.get("aspect_ratio") or aspect
            export_preset = params.get("export_preset") or export_preset
        if s.get("action") in ("video", "lipsync", "image"):
            ar = (s.get("params") or {}).get("aspect_ratio")
            if ar and aspect is None:
                aspect = ar
    if aspect and aspect != spec["aspect_ratio"]:
        warnings.append(
            f"画幅 {aspect} 与投放位 {spec['label']} 要求 {spec['aspect_ratio']} 不一致"
        )
    if export_preset and export_preset != spec["export_preset"]:
        warnings.append(
            f"导出预设 {export_preset} 与投放位 {spec['id']}（{spec['export_preset']}）不一致"
        )
    dur = int(plan.get("duration") or 0)
    if dur and (dur < spec["duration_min"] or dur > spec["duration_max"]):
        warnings.append(
            f"时长 {dur}s 超出 {spec['label']} 建议区间 "
            f"{spec['duration_min']}–{spec['duration_max']}s"
        )
    return warnings
