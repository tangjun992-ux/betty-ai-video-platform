"""KIE.ai provider backend — delegates to KieAdapter."""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.gateway.providers.base import ProviderBackend
from app.gateway.types import Capability

logger = logging.getLogger(__name__)


class KieBackend(ProviderBackend):
    @property
    def name(self) -> str:
        return "kie"

    def is_configured(self) -> bool:
        from app.config import settings
        return bool(settings.KIE_API_KEY)

    def _adapter(self):
        from app.adapters.kie_adapter import KieAdapter
        return KieAdapter()

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
            raise RuntimeError("KIE_API_KEY not configured")

        adapter = self._adapter()
        logger.info(
            "[gateway/kie] capability=%s model=%s trace=%s",
            capability.value, remote_model, trace_id or "-",
        )

        if capability == Capability.IMAGE_GENERATE:
            return await adapter.generate_image(
                prompt=kwargs.get("prompt", ""),
                model_id=remote_model,
                size=kwargs.get("size", "1024x1024"),
                style=kwargs.get("style"),
                count=kwargs.get("count", 1),
                seed=kwargs.get("seed"),
                negative_prompt=kwargs.get("negative_prompt"),
                image_url=kwargs.get("image_url"),
                image_urls=kwargs.get("image_urls"),
                aspect_ratio=kwargs.get("aspect_ratio"),
            )

        if capability == Capability.IMAGE_EDIT:
            return await adapter.edit_image(
                image_urls=kwargs.get("image_urls") or [],
                prompt=kwargs.get("prompt", ""),
                image_size=kwargs.get("image_size", "auto"),
            )

        if capability == Capability.VIDEO_GENERATE:
            return await adapter.generate_video(
                prompt=kwargs.get("prompt", ""),
                model_id=remote_model,
                image_url=kwargs.get("image_url"),
                duration=kwargs.get("duration", 5),
                resolution=kwargs.get("resolution", "1080p"),
                aspect_ratio=kwargs.get("aspect_ratio"),
                reference_images=kwargs.get("reference_images"),
                reference_videos=kwargs.get("reference_videos"),
                reference_audios=kwargs.get("reference_audios"),
            )

        if capability == Capability.LIPSYNC:
            return await adapter.generate_lipsync(
                image_url=kwargs.get("image_url", ""),
                audio_url=kwargs.get("audio_url", ""),
                model_id=remote_model,
            )

        if capability == Capability.MOTION:
            return await adapter.generate_motion(
                image_url=kwargs.get("image_url", ""),
                video_url=kwargs.get("video_url", ""),
                prompt=kwargs.get("prompt", ""),
                model_id=remote_model,
                resolution=kwargs.get("resolution", "720p"),
            )

        if capability == Capability.TTS:
            return await adapter.generate_speech(
                text=kwargs.get("text", ""),
                voice=kwargs.get("voice"),
                model_id=remote_model,
            )

        raise RuntimeError(f"KIE backend does not support capability: {capability.value}")
