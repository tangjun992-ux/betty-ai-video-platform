"""Kling direct provider backend."""
from __future__ import annotations

import logging
from typing import Any

from app.gateway.providers.base import ProviderBackend
from app.gateway.types import Capability

logger = logging.getLogger(__name__)


class KlingBackend(ProviderBackend):
    @property
    def name(self) -> str:
        return "kling"

    def is_configured(self) -> bool:
        from app.config import settings
        return bool(settings.KLING_ACCESS_KEY and settings.KLING_SECRET_KEY)

    def _adapter(self):
        from app.adapters.kling_adapter import KlingAdapter
        return KlingAdapter()

    async def execute(
        self,
        capability: Capability,
        remote_model: str,
        *,
        timeout_s: int = 240,
        trace_id: str = "",
        **kwargs: Any,
    ) -> Any:
        if not self.is_configured():
            raise RuntimeError("Kling API keys not configured")
        adapter = self._adapter()
        logger.info("[gateway/kling] capability=%s model=%s trace=%s", capability.value, remote_model, trace_id or "-")

        if capability == Capability.VIDEO_GENERATE:
            return await adapter.generate_video(
                prompt=kwargs.get("prompt", ""),
                image_url=kwargs.get("image_url"),
                duration=kwargs.get("duration", 5),
                resolution=kwargs.get("resolution", "1080p"),
            )

        raise RuntimeError(f"Kling backend does not support capability: {capability.value}")
