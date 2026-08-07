"""Replicate provider backend — delegates to ReplicateAdapter."""
from __future__ import annotations

import logging
from typing import Any

from app.gateway.providers.base import ProviderBackend
from app.gateway.types import Capability

logger = logging.getLogger(__name__)


class ReplicateBackend(ProviderBackend):
    @property
    def name(self) -> str:
        return "replicate"

    def is_configured(self) -> bool:
        from app.config import settings
        return bool(settings.REPLICATE_API_KEY)

    def _adapter(self):
        from app.adapters.replicate_adapter import ReplicateAdapter
        return ReplicateAdapter()

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
            raise RuntimeError("REPLICATE_API_KEY not configured")

        adapter = self._adapter()
        logger.info(
            "[gateway/replicate] capability=%s model=%s trace=%s",
            capability.value, remote_model, trace_id or "-",
        )

        if capability == Capability.IMAGE_GENERATE:
            return await adapter.generate_image(
                prompt=kwargs.get("prompt", ""),
                model_id=remote_model,
                size=kwargs.get("size", "1024x1024"),
                style=kwargs.get("style"),
                count=kwargs.get("count", 1),
            )

        if capability == Capability.VIDEO_GENERATE:
            return await adapter.generate_video(
                prompt=kwargs.get("prompt", ""),
                model_id=remote_model,
                image_url=kwargs.get("image_url"),
                duration=kwargs.get("duration", 5),
                resolution=kwargs.get("resolution", "1080p"),
            )

        raise RuntimeError(f"Replicate backend does not support capability: {capability.value}")
