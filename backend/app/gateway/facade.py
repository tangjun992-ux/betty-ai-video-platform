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


class GatewayFacade:
    """Unified model API gateway."""

    # ── Asset pipeline ────────────────────────────────────────
    upload_public_url = staticmethod(upload_public_url)
    publicize_url = staticmethod(publicize_url)

    # ── Routed generation (multi-provider failover) ───────────
    def _route_kwargs(
        self,
        *,
        trace_id: str = "",
        user_id: int | None = None,
        team_id: str | None = None,
        estimated_cost: float = 0.0,
        **extra,
    ) -> dict:
        return {
            "trace_id": trace_id,
            "user_id": user_id,
            "team_id": team_id,
            "estimated_cost": estimated_cost,
            **extra,
        }

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
        user_id: int | None = None,
        team_id: str | None = None,
        estimated_cost: float = 0.0,
        **kwargs,
    ) -> GatewayExecutionResult:
        has_refs = bool(image_url or image_urls)
        rk = self._route_kwargs(
            trace_id=trace_id, user_id=user_id, team_id=team_id,
            estimated_cost=estimated_cost,
        )
        if has_refs:
            return await execute_route(
                Capability.IMAGE_EDIT,
                "nano-banana-edit",
                prompt=prompt,
                image_urls=image_urls or ([image_url] if image_url else []),
                image_size=size,
                **rk,
                **kwargs,
            )
        return await execute_route(
            Capability.IMAGE_GENERATE,
            model,
            prompt=prompt,
            size=size,
            style=style,
            count=count,
            seed=seed,
            negative_prompt=negative_prompt,
            **rk,
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
        user_id: int | None = None,
        team_id: str | None = None,
        estimated_cost: float = 0.0,
        **kwargs,
    ) -> GatewayExecutionResult:
        return await execute_route(
            Capability.VIDEO_GENERATE,
            model,
            prompt=prompt,
            image_url=image_url,
            duration=duration,
            resolution=resolution,
            **self._route_kwargs(
                trace_id=trace_id, user_id=user_id, team_id=team_id,
                estimated_cost=estimated_cost,
            ),
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
        user_id: int | None = None,
        team_id: str | None = None,
        estimated_cost: float = 0.0,
        **kwargs,
    ) -> GatewayExecutionResult:
        route_model = model
        if model in ("lipsync-studio", "studio"):
            route_model = "lipsync-studio"
        elif model_id and "/" in model_id:
            kwargs["remote_model_override"] = model_id
        return await execute_route(
            Capability.LIPSYNC,
            route_model,
            image_url=image_url,
            audio_url=audio_url,
            prompt=prompt,
            resolution=resolution,
            prefer_infinitalk=prefer_infinitalk or route_model == "lipsync-studio",
            **self._route_kwargs(
                trace_id=trace_id, user_id=user_id, team_id=team_id,
                estimated_cost=estimated_cost,
            ),
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
        user_id: int | None = None,
        team_id: str | None = None,
        estimated_cost: float = 0.0,
        **kwargs,
    ) -> GatewayExecutionResult:
        route_model = model or ("motion-control-studio" if studio else "motion-control")
        return await execute_route(
            Capability.MOTION,
            route_model,
            image_url=image_url,
            video_url=video_url,
            prompt=prompt,
            resolution=resolution,
            duration=duration,
            studio=studio,
            **self._route_kwargs(
                trace_id=trace_id, user_id=user_id, team_id=team_id,
                estimated_cost=estimated_cost,
            ),
            **kwargs,
        )

    async def generate_speech(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        model: str = "elevenlabs-multilingual",
        trace_id: str = "",
        user_id: int | None = None,
        team_id: str | None = None,
        estimated_cost: float = 0.0,
        **kwargs,
    ) -> GatewayExecutionResult:
        return await execute_route(
            Capability.TTS,
            model,
            text=text,
            voice=voice,
            **self._route_kwargs(
                trace_id=trace_id, user_id=user_id, team_id=team_id,
                estimated_cost=estimated_cost,
            ),
            **kwargs,
        )

    # ── Routed image tools ────────────────────────────────────
    async def edit_image(
        self, *, image_urls: list, prompt: str, image_size: str = "auto", trace_id: str = "",
        user_id: int | None = None, team_id: str | None = None, estimated_cost: float = 0.0,
    ) -> GatewayExecutionResult:
        return await execute_route(
            Capability.IMAGE_EDIT, "nano-banana-edit",
            image_urls=image_urls, prompt=prompt, image_size=image_size,
            **self._route_kwargs(
                trace_id=trace_id, user_id=user_id, team_id=team_id,
                estimated_cost=estimated_cost,
            ),
        )

    async def face_swap(
        self, *, face_url: str, target_url: str, prompt: Optional[str] = None, trace_id: str = "",
        user_id: int | None = None, team_id: str | None = None, estimated_cost: float = 0.0,
    ) -> GatewayExecutionResult:
        face_pub = await publicize_url(face_url, trace_id=trace_id)
        target_pub = await publicize_url(target_url, trace_id=trace_id)
        return await execute_route(
            Capability.IMAGE_FACE_SWAP, "face-swap",
            face_url=face_pub, target_url=target_pub, prompt=prompt,
            **self._route_kwargs(
                trace_id=trace_id, user_id=user_id, team_id=team_id,
                estimated_cost=estimated_cost,
            ),
        )

    async def upscale_image(
        self, *, image_url: str, factor: str = "2", trace_id: str = "",
        user_id: int | None = None, team_id: str | None = None, estimated_cost: float = 0.0,
    ) -> GatewayExecutionResult:
        pub = await publicize_url(image_url, trace_id=trace_id)
        return await execute_route(
            Capability.IMAGE_UPSCALE, "image-upscale",
            image_url=pub, factor=factor,
            **self._route_kwargs(
                trace_id=trace_id, user_id=user_id, team_id=team_id,
                estimated_cost=estimated_cost,
            ),
        )

    async def remove_background(
        self, *, image_url: str, trace_id: str = "",
        user_id: int | None = None, team_id: str | None = None, estimated_cost: float = 0.0,
    ) -> GatewayExecutionResult:
        pub = await publicize_url(image_url, trace_id=trace_id)
        return await execute_route(
            Capability.IMAGE_REMOVE_BG, "remove-background",
            image_url=pub,
            **self._route_kwargs(
                trace_id=trace_id, user_id=user_id, team_id=team_id,
                estimated_cost=estimated_cost,
            ),
        )

    async def extend_image(
        self, *, image_url: str, target_ratio: str = "16:9", prompt: str = "", trace_id: str = "",
        user_id: int | None = None, team_id: str | None = None, estimated_cost: float = 0.0,
    ) -> GatewayExecutionResult:
        pub = await publicize_url(image_url, trace_id=trace_id)
        return await execute_route(
            Capability.IMAGE_EXTEND, "image-extend",
            image_url=pub, target_ratio=target_ratio, prompt=prompt,
            **self._route_kwargs(
                trace_id=trace_id, user_id=user_id, team_id=team_id,
                estimated_cost=estimated_cost,
            ),
        )


gateway = GatewayFacade()
