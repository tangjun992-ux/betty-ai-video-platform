"""Seedance direct provider backend."""
from __future__ import annotations

import logging
from typing import Any

from app.gateway.providers.base import ProviderBackend
from app.gateway.types import Capability

logger = logging.getLogger(__name__)


class SeedanceBackend(ProviderBackend):
    @property
    def name(self) -> str:
        return "seedance"

    def is_configured(self) -> bool:
        from app.config import settings
        return bool(settings.SEEDANCE_API_KEY)

    def _adapter(self):
        from app.adapters.seedance_adapter import SeedanceAdapter
        return SeedanceAdapter()

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
            raise RuntimeError("SEEDANCE_API_KEY not configured")
        adapter = self._adapter()
        logger.info("[gateway/seedance] capability=%s model=%s trace=%s", capability.value, remote_model, trace_id or "-")

        if capability == Capability.VIDEO_GENERATE:
            return await adapter.generate_video(
                prompt=kwargs.get("prompt", ""),
                image_url=kwargs.get("image_url"),
                video_url=kwargs.get("video_url"),
                duration=kwargs.get("duration", 5),
                resolution=kwargs.get("resolution", "1080p"),
            )
        if capability == Capability.IMAGE_GENERATE:
            results = await adapter.generate_image(
                prompt=kwargs.get("prompt", ""),
                size=kwargs.get("size", "1024x1024"),
                style=kwargs.get("style", "auto"),
                count=kwargs.get("count", 1),
            )
            return results[0] if isinstance(results, list) and results else results

        raise RuntimeError(f"Seedance backend does not support capability: {capability.value}")
