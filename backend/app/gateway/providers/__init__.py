"""Provider backend registry."""
from __future__ import annotations

from typing import Optional

from app.gateway.providers.base import ProviderBackend
from app.gateway.providers.kie import KieBackend
from app.gateway.providers.replicate import ReplicateBackend

_BACKENDS: dict[str, ProviderBackend] = {
    "kie": KieBackend(),
    "replicate": ReplicateBackend(),
}


def get_backend(provider: str) -> Optional[ProviderBackend]:
    return _BACKENDS.get((provider or "").strip().lower())


def list_backends() -> dict[str, ProviderBackend]:
    return dict(_BACKENDS)
