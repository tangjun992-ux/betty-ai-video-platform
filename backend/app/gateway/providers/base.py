"""Provider backend protocol — one implementation per external API."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.gateway.types import Capability


class ProviderBackend(ABC):
    """Execute a single provider hop for a given capability."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True when API keys / credentials are present."""
        ...

    @abstractmethod
    async def execute(
        self,
        capability: Capability,
        remote_model: str,
        *,
        timeout_s: int = 240,
        trace_id: str = "",
        **kwargs: Any,
    ) -> Any:
        """
        Run one generation hop. Returns GenerationResult or list[GenerationResult].
        Raises RuntimeError on failure.
        """
        ...

    async def health_ping(self) -> bool:
        return self.is_configured()
