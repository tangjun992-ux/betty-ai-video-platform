"""
GatewayFacade — single entry point for all model provider calls.

Callers (Celery tasks, API routes, Director) should use this instead of
instantiating KieAdapter() directly.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.config import settings
from app.gateway.assets import publicize_url, upload_public_url
from app.gateway.executor import execute_route
from app.gateway.types import Capability, GatewayExecutionResult

logger = logging.getLogger(__name__)


def gateway_enabled() -> bool:
    return getattr(settings, "GATEWAY_ENABLED", True)


def _kie():
    from app.adapters.kie_adapter import KieAdapter
    return KieAdapter()


class GatewayFacade:
    """Unified model API gateway."""

    # ── Asset pipeline ────────────────────────────────────────
    upload_public_url = staticmethod(upload_public_url)
    publicize_url = staticmethod(publicize_url)

    # ── Routed generation (multi-provider failover) ───────────
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
        model_id: Optional[str] = None,
        prompt: str = "a person talking naturally on camera",
        resolution: str = "480p",
        prefer_infinitalk: bool = False,
        trace_id: str = "",
        **kwargs,
    ) -> GatewayExecutionResult:
        # Explicit KIE SKU (contains "/") → route by gateway model alias or direct chain
        route_model = model
        if model in ("lipsync-studio", "studio"):
            route_model = "lipsync-studio"
        elif model_id and "/" in model_id:
            kwargs["remote_model_override"] = model_id
        return await execute_route(
            Capability.LIPSYNC,
            route_model,
            trace_id=trace_id,
            image_url=image_url,
            audio_url=audio_url,
            prompt=prompt,
            resolution=resolution,
            prefer_infinitalk=prefer_infinitalk or route_model == "lipsync-studio",
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
        duration: int = 5,
        studio: bool = False,
        trace_id: str = "",
        **kwargs,
    ) -> GatewayExecutionResult:
        route_model = model or ("motion-control-studio" if studio else "motion-control")
        return await execute_route(
            Capability.MOTION,
            route_model,
            trace_id=trace_id,
            image_url=image_url,
            video_url=video_url,
            prompt=prompt,
            resolution=resolution,
            duration=duration,
            studio=studio,
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

    # ── Single-provider tools (KIE today; unified entry for Phase 3 routing) ──
    async def edit_image(
        self, *, image_urls: list, prompt: str, image_size: str = "auto", trace_id: str = "",
    ) -> GatewayExecutionResult:
        gw = await execute_route(
            Capability.IMAGE_EDIT, "nano-banana-edit",
            trace_id=trace_id, image_urls=image_urls, prompt=prompt, image_size=image_size,
        )
        return gw

    async def face_swap(
        self, *, face_url: str, target_url: str, prompt: Optional[str] = None, trace_id: str = "",
    ) -> Any:
        face_pub = await publicize_url(face_url, trace_id=trace_id)
        target_pub = await publicize_url(target_url, trace_id=trace_id)
        return await _kie().face_swap(face_url=face_pub, target_url=target_pub, prompt=prompt)

    async def upscale_image(self, *, image_url: str, factor: str = "2", trace_id: str = "") -> Any:
        pub = await publicize_url(image_url, trace_id=trace_id)
        return await _kie().upscale_image(image_url=pub, factor=factor)

    async def remove_background(self, *, image_url: str, trace_id: str = "") -> Any:
        pub = await publicize_url(image_url, trace_id=trace_id)
        return await _kie().remove_background(image_url=pub)

    async def extend_image(
        self, *, image_url: str, target_ratio: str = "16:9", prompt: str = "", trace_id: str = "",
    ) -> Any:
        pub = await publicize_url(image_url, trace_id=trace_id)
        return await _kie().extend_image(image_url=pub, target_ratio=target_ratio, prompt=prompt)


gateway = GatewayFacade()
