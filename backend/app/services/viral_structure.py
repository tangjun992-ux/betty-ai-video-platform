"""URL-to-Viral structure hints — hook / CTA / banner from extract + social meta."""
from __future__ import annotations

from typing import Any, Optional


_PLATFORM_CTA: dict[str, str] = {
    "youtube": "订阅了解更多 · 片尾 CTA",
    "tiktok": "同款安利 · 评论区见",
    "instagram": "滑动查看 · 立即选购",
    "x": "转发讨论 · 链接在简介",
    "facebook": "了解更多 · 立即行动",
}


def infer_viral_structure(
    *,
    prompt: str,
    social: Optional[dict[str, Any]] = None,
    style_tags: Optional[list[str]] = None,
    media_kind: str = "image",
) -> dict[str, Any]:
    """Derive honest URL-to-Viral scaffolding (not full video reverse-engineering)."""
    social = social or {}
    title = (social.get("title") or "").strip()
    platform = (social.get("platform") or "").strip().lower()
    tags = [str(t).lower() for t in (style_tags or [])]

    hook = ""
    if title:
        hook = title[:120]
    elif prompt:
        hook = prompt.split(".")[0].split("，")[0][:120]

    cta = _PLATFORM_CTA.get(platform) or "了解更多 · 立即行动"
    portrait = (
        media_kind == "video"
        or any("portrait" in t or "vertical" in t or "9:16" in t for t in tags)
    )
    banner_hint = "竖屏 9:16 社媒封面 / 短视频钩子帧" if portrait else "横屏 16:9 横幅 / 封面帧"

    brief_parts = [p for p in (hook, prompt[:240]) if p]
    agent_brief = "，".join(dict.fromkeys(brief_parts))[:320]

    return {
        "hook": hook,
        "cta": cta,
        "banner_hint": banner_hint,
        "platform": platform or None,
        "agent_brief": agent_brief,
        "honesty": (
            "由标题/封面反推的钩子与 CTA 建议，非完整视频脚本还原；"
            "成片请交给 Agent 或视频页继续编辑。"
        ),
    }
