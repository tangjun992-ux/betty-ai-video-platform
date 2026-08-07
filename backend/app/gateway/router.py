"""Gateway router — resolve Betty SKU → ordered, health-filtered provider chain."""
from __future__ import annotations

import hashlib
import logging
from typing import Optional

from app.config import settings
from app.gateway.config import find_route, get_routes
from app.gateway.health import provider_health
from app.gateway.registry import gateway_registry
from app.gateway.types import Capability, ProviderTarget, RouteDefinition

logger = logging.getLogger(__name__)

_IMAGE_MODELS = frozenset({
    "gpt-image-2", "dall-e-3", "nano-banana", "nano-banana-pro", "nano-banana-2",
    "nano-banana-basic", "imagen-4", "imagen-4-fast", "imagen-4-ultra",
    "flux-1.1-pro", "flux-1-dev", "flux-kontext", "ideogram-v3", "recraft-v3",
    "seedream-3", "qwen-image", "hidream-i1", "sdxl", "midjourney-v7", "grok-image",
    "flux-schnell", "flux-dev", "flux-pro", "sd3.5",
})


def _gateway_region() -> str:
    return (getattr(settings, "GATEWAY_REGION", "") or "").strip().lower()


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


def resolve_route(capability: Capability, model: str) -> Optional[RouteDefinition]:
    route = find_route(capability, model)
    if route:
        return route
    if capability == Capability.IMAGE_EDIT:
        return find_route(Capability.IMAGE_EDIT, "nano-banana-edit")
    return None


def _region_match(target: ProviderTarget) -> bool:
    region = _gateway_region()
    if not target.region:
        return True
    if not region:
        return True
    return target.region == region


def _stable_bucket(trace_id: str, seed: str) -> int:
    """0–99 deterministic bucket for canary routing."""
    raw = hashlib.sha256(f"{trace_id or 'default'}:{seed}".encode()).hexdigest()
    return int(raw[:8], 16) % 100


def _order_with_canary(
    primaries: list[ProviderTarget],
    *,
    trace_id: str = "",
) -> list[ProviderTarget]:
    """Weighted / canary pick among primary targets, then append fallbacks order."""
    if len(primaries) <= 1:
        return primaries

    has_canary = any(t.canary_percent > 0 for t in primaries)
    if not has_canary:
        return sorted(primaries, key=lambda t: t.priority)

    # Build weights: canary targets use canary_percent; others use weight
    weights: list[tuple[ProviderTarget, int]] = []
    for t in primaries:
        w = t.canary_percent if t.canary_percent > 0 else max(t.weight, 1)
        weights.append((t, w))
    total = sum(w for _, w in weights)
    bucket = _stable_bucket(trace_id, "canary")
    cum = 0
    chosen = weights[0][0]
    for t, w in weights:
        cum += int(w * 100 / max(total, 1))
        if bucket < cum or cum >= 100:
            chosen = t
            break
    rest = [t for t, _ in weights if t != chosen]
    return [chosen] + rest


def select_targets(
    route: RouteDefinition,
    *,
    allow_fallback: bool = True,
    primary_only: bool = False,
    trace_id: str = "",
) -> list[ProviderTarget]:
    from app.gateway.providers import get_backend

    if gateway_registry.kill_switch_active():
        logger.warning("[gateway] kill switch active — no targets")
        return []

    candidates: list[ProviderTarget] = []
    for target in route.chain:
        if primary_only and target.fallback_only:
            continue
        if not allow_fallback and target.fallback_only:
            continue
        if not _region_match(target):
            continue
        if gateway_registry.is_disabled(target.provider, target.remote_model):
            logger.info("[gateway] skip %s:%s — admin disabled", target.provider, target.remote_model)
            continue
        backend = get_backend(target.provider)
        if not backend or not backend.is_configured():
            continue
        if not provider_health.is_available(target.provider, target.remote_model):
            continue
        candidates.append(target)

    primaries = [t for t in candidates if not t.fallback_only]
    fallbacks = [t for t in candidates if t.fallback_only]
    ordered_primaries = _order_with_canary(primaries, trace_id=trace_id)
    return ordered_primaries + fallbacks


def route_summary() -> dict:
    routes = get_routes()
    return {
        "route_count": len(routes),
        "registry_version": gateway_registry.version(),
        "region": _gateway_region() or "global",
        "routes": [
            {
                "capability": r.capability.value,
                "model": r.model,
                "description": r.description,
                "chain": [
                    {
                        "provider": t.provider,
                        "remote_model": t.remote_model,
                        "fallback_only": t.fallback_only,
                        "canary_percent": t.canary_percent,
                        "region": t.region or "global",
                        "weight": t.weight,
                    }
                    for t in r.chain
                ],
            }
            for r in routes
        ],
    }
