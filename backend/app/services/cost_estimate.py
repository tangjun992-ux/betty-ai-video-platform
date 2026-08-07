"""Unified credit/time estimation from models catalog (Phase 7 Yapper parity)."""
from __future__ import annotations

from app.services.entitlements import LIPSYNC_DEMO_COST


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
