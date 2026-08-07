"""Load and validate gateway route configuration."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

from app.gateway.types import Capability, ProviderTarget, RouteDefinition

logger = logging.getLogger(__name__)

_DEFAULT_ROUTES = Path(__file__).resolve().parent / "routes.yaml"
_loaded: Optional[list[RouteDefinition]] = None


def _parse_capability(raw: str) -> Capability:
    try:
        return Capability(raw)
    except ValueError as e:
        raise ValueError(f"Unknown capability: {raw!r}") from e


def _parse_target(entry: dict) -> ProviderTarget:
    if "provider" not in entry or "remote_model" not in entry:
        raise ValueError(f"Invalid chain entry (need provider + remote_model): {entry}")
    return ProviderTarget(
        provider=str(entry["provider"]).strip().lower(),
        remote_model=str(entry["remote_model"]).strip(),
        priority=int(entry.get("priority", 1)),
        fallback_only=bool(entry.get("fallback_only", False)),
        timeout_s=int(entry.get("timeout_s", 240)),
        weight=int(entry.get("weight", 100)),
        canary_percent=int(entry.get("canary_percent", 0)),
        region=str(entry.get("region", "") or "").strip().lower(),
    )


def _routes_path() -> Path:
    from app.config import settings
    custom = (getattr(settings, "GATEWAY_ROUTES_PATH", "") or "").strip()
    if custom:
        p = Path(custom)
        if p.is_file():
            return p
        logger.warning("[gateway] GATEWAY_ROUTES_PATH not found: %s — using default", custom)
    return _DEFAULT_ROUTES


def load_routes(path: Optional[Path] = None) -> list[RouteDefinition]:
    """Parse routes.yaml into RouteDefinition list."""
    p = path or _routes_path()
    if not p.exists():
        logger.warning("[gateway] routes file not found: %s", p)
        return []

    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    routes: list[RouteDefinition] = []
    for entry in data.get("routes", []):
        cap = _parse_capability(entry["capability"])
        model = str(entry["model"]).strip()
        chain_raw = entry.get("chain") or []
        if not chain_raw:
            logger.warning("[gateway] empty chain for %s/%s — skipped", cap.value, model)
            continue
        chain = tuple(_parse_target(c) for c in chain_raw)
        routes.append(RouteDefinition(
            capability=cap,
            model=model,
            chain=chain,
            description=str(entry.get("description", "")),
        ))
    return routes


def get_routes(*, reload: bool = False, path: Optional[Path] = None) -> list[RouteDefinition]:
    global _loaded
    if _loaded is None or reload:
        _loaded = load_routes(path)
        logger.info("[gateway] loaded %d route(s) from config", len(_loaded))
    return _loaded


def find_route(capability: Capability, model: str) -> Optional[RouteDefinition]:
    """Exact match on capability + Betty model SKU."""
    for r in get_routes():
        if r.capability == capability and r.model == model:
            return r
    return None


def routes_for_model(model: str) -> list[RouteDefinition]:
    return [r for r in get_routes() if r.model == model]


def validate_routes(routes: list[RouteDefinition] | None = None) -> list[str]:
    """Validate route table; return human-readable error messages (empty = ok)."""
    from app.gateway.providers import list_backends

    items = routes if routes is not None else load_routes()
    known_providers = set(list_backends().keys())
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()

    if not items:
        errors.append("No routes defined — routes.yaml is empty or missing")
        return errors

    for route in items:
        key = (route.capability.value, route.model)
        if key in seen:
            errors.append(f"Duplicate route: {route.capability.value}/{route.model}")
        seen.add(key)

        if not route.model.strip():
            errors.append(f"Empty model id for capability {route.capability.value}")

        if not route.chain:
            errors.append(f"Empty provider chain: {route.capability.value}/{route.model}")
            continue

        for hop in route.chain:
            if hop.provider not in known_providers:
                errors.append(
                    f"Unknown provider {hop.provider!r} in "
                    f"{route.capability.value}/{route.model}",
                )
            if not hop.remote_model.strip():
                errors.append(
                    f"Empty remote_model for {hop.provider} in "
                    f"{route.capability.value}/{route.model}",
                )
            if hop.timeout_s <= 0:
                errors.append(
                    f"Invalid timeout_s={hop.timeout_s} for {hop.provider} in "
                    f"{route.capability.value}/{route.model}",
                )
            if hop.canary_percent < 0 or hop.canary_percent > 100:
                errors.append(
                    f"Invalid canary_percent={hop.canary_percent} for {hop.provider} in "
                    f"{route.model}",
                )

    return errors
