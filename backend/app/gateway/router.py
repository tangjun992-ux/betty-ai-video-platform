"""Gateway router — resolve Betty SKU → ordered, health-filtered provider chain."""
from __future__ import annotations

import logging
from typing import Optional

from app.gateway.config import find_route, get_routes
from app.gateway.health import provider_health
from app.gateway.types import Capability, ProviderTarget, RouteDefinition

logger = logging.getLogger(__name__)

# Default capability when callers pass only a model id (image vs video inference).
_IMAGE_MODELS = frozenset({
    "gpt-image-2", "dall-e-3", "nano-banana", "nano-banana-pro", "nano-banana-2",
    "nano-banana-basic", "imagen-4", "imagen-4-fast", "imagen-4-ultra",
    "flux-1.1-pro", "flux-1-dev", "flux-kontext", "ideogram-v3", "recraft-v3",
    "seedream-3", "qwen-image", "hidream-i1", "sdxl", "midjourney-v7", "grok-image",
    "flux-schnell", "flux-dev", "flux-pro", "sd3.5",
})


def infer_capability(model: str, *, has_refs: bool = False) -> Capability:
    if has_refs:
        return Capability.IMAGE_EDIT
    if model in ("motion-control", "motion-control-studio", "kling-motion"):
        return Capability.MOTION
    if model in ("kling-ai-avatar", "lipsync"):
        return Capability.LIPSYNC
    if model in ("elevenlabs-multilingual",):
        return Capability.TTS
    if model in _IMAGE_MODELS:
        return Capability.IMAGE_GENERATE
    return Capability.VIDEO_GENERATE


def resolve_route(
    capability: Capability,
    model: str,
) -> Optional[RouteDefinition]:
    """Find route; for image.edit with refs, fall back to nano-banana-edit route."""
    route = find_route(capability, model)
    if route:
        return route
    if capability == Capability.IMAGE_EDIT:
        return find_route(Capability.IMAGE_EDIT, "nano-banana-edit")
    return None


def select_targets(
    route: RouteDefinition,
    *,
    allow_fallback: bool = True,
    primary_only: bool = False,
) -> list[ProviderTarget]:
    """
    Return ordered provider targets, skipping:
    - unconfigured providers
    - circuit-open providers
    - fallback_only hops when primary_only=True or allow_fallback=False
    """
    from app.gateway.providers import get_backend

    selected: list[ProviderTarget] = []
    for target in sorted(route.chain, key=lambda t: t.priority):
        if primary_only and target.fallback_only:
            continue
        if not allow_fallback and target.fallback_only:
            continue
        backend = get_backend(target.provider)
        if not backend or not backend.is_configured():
            logger.debug("[gateway] skip %s — not configured", target.provider)
            continue
        if not provider_health.is_available(target.provider, target.remote_model):
            logger.info("[gateway] skip %s:%s — circuit open", target.provider, target.remote_model)
            continue
        selected.append(target)
    return selected


def route_summary() -> dict:
    """Ops snapshot for health endpoint."""
    routes = get_routes()
    return {
        "route_count": len(routes),
        "routes": [
            {
                "capability": r.capability.value,
                "model": r.model,
                "chain": [
                    {"provider": t.provider, "remote_model": t.remote_model, "fallback_only": t.fallback_only}
                    for t in r.chain
                ],
            }
            for r in routes
        ],
    }
