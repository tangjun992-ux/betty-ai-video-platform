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


def load_routes(path: Optional[Path] = None) -> list[RouteDefinition]:
    """Parse routes.yaml into RouteDefinition list."""
    p = path or _DEFAULT_ROUTES
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
