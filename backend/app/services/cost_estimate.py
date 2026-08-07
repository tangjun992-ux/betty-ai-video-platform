"""Unified credit/time estimation from models catalog (Phase 7 Yapper parity)."""
from __future__ import annotations

from app.services.entitlements import LIPSYNC_DEMO_COST, lipsync_cost, motion_cost

# Tool latency hints (seconds) — aligned with backend task estimates
TOOL_ESTIMATED_SECONDS: dict[str, int] = {
    "lipsync": 180,
    "lipsync_studio": 240,
    "motion": 90,
    "motion_studio": 120,
    "performance": 150,
    "performance_studio": 180,
}


def estimate_tool(
    *,
    tool: str,
    tier: str = "demo",
    with_talk: bool = False,
) -> tuple[int, int]:
    """Return (estimated_seconds, estimated_credits) for lipsync/motion/performance."""
    t = (tool or "").strip().lower()
    tier_norm = "studio" if (tier or "demo").strip().lower() == "studio" else "demo"
    if t == "lipsync":
        credits = lipsync_cost(tier_norm)
        seconds = TOOL_ESTIMATED_SECONDS["lipsync_studio" if tier_norm == "studio" else "lipsync"]
        return seconds, credits
    if t == "motion":
        credits = motion_cost(tier_norm)
        seconds = TOOL_ESTIMATED_SECONDS["motion_studio" if tier_norm == "studio" else "motion"]
        return seconds, credits
    if t == "performance":
        credits = motion_cost(tier_norm) + (lipsync_cost(tier_norm) if with_talk else 0)
        key = "performance_studio" if tier_norm == "studio" else "performance"
        seconds = TOOL_ESTIMATED_SECONDS[key]
        if with_talk:
            seconds += 60
        return seconds, credits
    raise ValueError(f"unknown tool: {tool}")


def _model_entry(model_id: str):
    from app.api.models_info import MODELS
    for m in MODELS:
        if m.id == model_id:
            return m
    return None


def estimate_generation(
    *,
    media_type: str,
    model: str,
    duration: int = 5,
    count: int = 1,
    post_lipsync: bool = False,
) -> tuple[int, int]:
    """Return (estimated_seconds, estimated_credits)."""
    mt = (media_type or "image").lower()
    dur = max(1, int(duration or 5))
    n = max(1, min(int(count or 1), 4))
    entry = _model_entry(model)
    if entry:
        if mt == "video" or "video" in (entry.capabilities.media_types or []):
            per5 = int(entry.capabilities.cost_per_5s_video_credits or 5)
            blocks = max(1, (dur + 4) // 5)
            credits = per5 * blocks * n
            seconds = int(entry.capabilities.avg_latency_s or 60) * blocks
        else:
            per_img = int(entry.capabilities.cost_per_image_credits or 3)
            credits = per_img * n
            seconds = int(entry.capabilities.avg_latency_s or 15)
    else:
        # Legacy fallback map keys
        from app.api.generate import _estimate_time_and_cost
        seconds, credits = _estimate_time_and_cost(mt, model, dur)
        credits *= n

    if post_lipsync and mt == "video":
        credits += LIPSYNC_DEMO_COST
        seconds += 120
    return seconds, credits
