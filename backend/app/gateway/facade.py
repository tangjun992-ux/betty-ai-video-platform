"""
GatewayFacade — single entry point for all model provider calls.

Callers (Celery tasks, API routes, Director) should use this instead of
instantiating KieAdapter() directly. When GATEWAY_ENABLED=false, falls back
to the legacy registry path for backward compatibility.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.config import settings
from app.gateway.executor import execute_route
from app.gateway.router import infer_capability
from app.gateway.types import Capability, GatewayExecutionResult

logger = logging.getLogger(__name__)


def gateway_enabled() -> bool:
    return getattr(settings, "GATEWAY_ENABLED", True)


class GatewayFacade:
    """Unified model API gateway."""

    async def generate_image(
        self,
        model: str,
        prompt: str,
        *,
        size: str = "1024x1024",
        style: Optional[str] = None,
        count: int = 1,
        seed: Optional[Any] = None,
        negative_prompt: Optional[str] = None,
        image_url: Optional[str] = None,
        image_urls: Optional[list] = None,
        trace_id: str = "",
        **kwargs,
    ) -> GatewayExecutionResult:
        has_refs = bool(image_url or image_urls)
        if has_refs:
            return await execute_route(
                Capability.IMAGE_EDIT,
                "nano-banana-edit",
                trace_id=trace_id,
                prompt=prompt,
                image_urls=image_urls or ([image_url] if image_url else []),
                image_size=size,
                **kwargs,
            )
        return await execute_route(
            Capability.IMAGE_GENERATE,
            model,
            trace_id=trace_id,
            prompt=prompt,
            size=size,
            style=style,
            count=count,
            seed=seed,
            negative_prompt=negative_prompt,
            **kwargs,
        )

    async def generate_video(
        self,
        model: str,
        prompt: str,
        *,
        image_url: Optional[str] = None,
        duration: int = 5,
        resolution: str = "1080p",
        trace_id: str = "",
        **kwargs,
    ) -> GatewayExecutionResult:
        return await execute_route(
            Capability.VIDEO_GENERATE,
            model,
            trace_id=trace_id,
            prompt=prompt,
            image_url=image_url,
            duration=duration,
            resolution=resolution,
            **kwargs,
        )

    async def generate_lipsync(
        self,
        image_url: str,
        audio_url: str,
        *,
        model: str = "kling-ai-avatar",
        trace_id: str = "",
        **kwargs,
    ) -> GatewayExecutionResult:
        return await execute_route(
            Capability.LIPSYNC,
            model,
            trace_id=trace_id,
            image_url=image_url,
            audio_url=audio_url,
            **kwargs,
        )

    async def generate_motion(
        self,
        image_url: str,
        video_url: str,
        *,
        model: str = "motion-control",
        prompt: str = "",
        resolution: str = "720p",
        trace_id: str = "",
        **kwargs,
    ) -> GatewayExecutionResult:
        return await execute_route(
            Capability.MOTION,
            model,
            trace_id=trace_id,
            image_url=image_url,
            video_url=video_url,
            prompt=prompt,
            resolution=resolution,
            **kwargs,
        )

    async def generate_speech(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        model: str = "elevenlabs-multilingual",
        trace_id: str = "",
        **kwargs,
    ) -> GatewayExecutionResult:
        return await execute_route(
            Capability.TTS,
            model,
            trace_id=trace_id,
            text=text,
            voice=voice,
            **kwargs,
        )


# Module-level singleton
gateway = GatewayFacade()
