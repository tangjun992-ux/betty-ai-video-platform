"""
Replicate adapter — high-quality, stable image/video generation.
Uses Replicate's async prediction API: submit → poll → return result.

Key advantage over KIE: pay-per-second GPU pricing, no opaque credits,
massive model selection, reliable infrastructure.

Docs: https://replicate.com/docs/reference/http
"""

import asyncio
import logging
import os
import time
from typing import Optional

import httpx

from app.adapters.base import BaseModelAdapter, GenerationResult, MediaSize
from app.adapters.registry import register_adapter
from app.config import settings

logger = logging.getLogger(__name__)

# ─── Model mapping ───────────────────────────────────────────
# Replicate uses owner/model:version_hash format.
# Using latest stable versions (2026-06).
REPLICATE_MODELS = {
    # ── Image models ──
    # FLUX Schnell — fastest, ~$0.002/image on L40S
    "flux-schnell": "black-forest-labs/flux-schnell",
    # FLUX Dev — better quality, ~$0.005/image
    "flux-dev": "black-forest-labs/flux-dev",
    # FLUX Pro 1.1 — top quality
    "flux-pro": "black-forest-labs/flux-1.1-pro",
    # SDXL — classic, very cheap
    "sdxl": "stability-ai/sdxl",
    # SD3.5 Large — newer
    "sd3.5": "stability-ai/stable-diffusion-3.5-large",

    # ── Video models ──
    # Wan 2.1 — text-to-video
    "wan-2.1": "wavespeedai/wan-2.1-t2v-720p",
    # CogVideoX — open source video
    "cogvideox": "fofr/cog-video-x-5b",
}

# Build bidirectional mapping (internal ↔ replicate ID)
_MODEL_IDS = {}
for internal, replicate_id in REPLICATE_MODELS.items():
    _MODEL_IDS[internal] = replicate_id
    _MODEL_IDS[replicate_id] = replicate_id


def _resolve_replicate_model(model_name: str) -> str:
    """Map internal → Replicate model ID, fallback to raw name."""
    return _MODEL_IDS.get(model_name, model_name)


# ─── Video detection ─────────────────────────────────────────
_VIDEO_MODELS = {"wan-2.1", "cogvideox", "wan-2.1-t2v-720p"}


def _is_video_model(model_id: str) -> bool:
    resolved = _resolve_replicate_model(model_id)
    return any(v in resolved.lower() for v in ("wan-", "cogvideo", "video"))


# ─── Pricing (USD per second on default hardware) ────────────
_PRICE_PER_SEC = {
    # Image models typically run on L40S ($0.000975/s)
    "black-forest-labs/flux-schnell": 0.000975,
    "black-forest-labs/flux-dev": 0.000975,
    "black-forest-labs/flux-1.1-pro": 0.000975,
    "stability-ai/sdxl": 0.000225,  # T4 $0.000225/s
    "stability-ai/stable-diffusion-3.5-large": 0.000975,
    # Video models
    "wan-2.1-t2v-720p": 0.000975,
    "cogvideox": 0.000975,
}

# Typical generation times (seconds) for cost estimation
_TYPICAL_DURATION = {
    "image": 3.0,    # FLUX ~2-4s on L40S
    "video": 30.0,   # varies wildly
}


def _estimate_cost(model_id: str, media_type: str, elapsed_s: float) -> float:
    """Estimate cost based on GPU time."""
    resolved = _resolve_replicate_model(model_id)
    rate = _PRICE_PER_SEC.get(resolved, 0.000975)
    return round(rate * max(elapsed_s, _TYPICAL_DURATION.get(media_type, 3)), 4)


@register_adapter
class ReplicateAdapter(BaseModelAdapter):
    """Adapter for Replicate's model hosting platform."""

    @property
    def _base_url(self) -> str:
        return "https://api.replicate.com"

    @property
    def _api_key(self) -> str:
        return settings.REPLICATE_API_KEY or os.getenv("REPLICATE_API_KEY", "")

    # ── availability ─────────────────────────────────────────
    @property
    def provider_name(self) -> str:
        return "Replicate"

    @property
    def supported_models(self) -> list[str]:
        return list(_MODEL_IDS.keys())

    @property
    def capabilities(self) -> dict:
        return {
            "max_resolution": "4K",
            "max_duration_s": 30,
            "supports_image": True,
            "supports_video": True,
            "supports_audio": False,
            "supports_llm": False,
        }

    def is_available(self, model_id: str = None) -> bool:
        return bool(self._api_key)

    async def is_model_available(self, model_id: str) -> bool:
        return self.is_available(model_id)

    # ── image generation ─────────────────────────────────────
    async def generate_image(
        self,
        prompt: str,
        *,
        model_id: str = "flux-schnell",
        size: str = "1024x1024",
        count: int = 1,
        style: Optional[str] = None,
        **kwargs,
    ) -> GenerationResult:
        """Generate image via Replicate API."""
        replicate_model = _resolve_replicate_model(model_id)
        logger.info(
            "[Replicate] image → model=%s size=%s prompt=%r",
            replicate_model, size, prompt,
        )

        # Parse size into width × height
        try:
            w, h = map(int, size.split("x"))
        except (ValueError, AttributeError):
            w, h = 1024, 1024

        payload = {
            "prompt": prompt,
            "width": w,
            "height": h,
            "num_outputs": count,
        }

        # Some models support extra params
        if style and "sdxl" in replicate_model:
            payload["negative_prompt"] = ""
        if "flux" in replicate_model:
            payload["num_inference_steps"] = kwargs.get("steps", 4 if "schnell" in replicate_model else 28)

        result = await self._submit_and_poll(
            replicate_model, payload, media_type="image", timeout=120
        )

        url = _extract_url(result)
        cost = _estimate_cost(replicate_model, "image", result.get("_elapsed", 3))

        return GenerationResult(
            media_url=url,
            media_type="image",
            model=replicate_model,
            cost=cost,
            meta={
                "replicate_id": result.get("id", ""),
                "resolution": size,
                "version": result.get("version", ""),
            },
        )

    # ── video generation ─────────────────────────────────────
    async def generate_video(
        self,
        prompt: str,
        *,
        model_id: str = "wan-2.1",
        duration: int = 5,
        resolution: str = "720p",
        image_url: Optional[str] = None,
        **kwargs,
    ) -> GenerationResult:
        """Generate video via Replicate API."""
        replicate_model = _resolve_replicate_model(model_id)
        logger.info(
            "[Replicate] video → model=%s dur=%ds prompt=%r",
            replicate_model, duration, prompt,
        )

        payload = {
            "prompt": prompt,
            "num_frames": duration * 16,  # 16fps
        }

        if image_url:
            payload["image_url"] = image_url

        result = await self._submit_and_poll(
            replicate_model, payload, media_type="video", timeout=600
        )

        url = _extract_url(result)
        cost = _estimate_cost(replicate_model, "video", result.get("_elapsed", 30))

        return GenerationResult(
            media_url=url,
            media_type="video",
            model=replicate_model,
            cost=cost,
            duration=float(duration),
            meta={
                "replicate_id": result.get("id", ""),
                "resolution": resolution,
                "version": result.get("version", ""),
            },
        )

    # ── core: submit + poll ─────────────────────────────────
    async def _submit_and_poll(
        self, model: str, input_data: dict, *, media_type: str, timeout: int = 180
    ) -> dict:
        """Submit Replicate prediction, then poll until success/failure."""
        if not self._api_key:
            raise RuntimeError("REPLICATE_API_KEY not configured")

        headers = {
            "Authorization": f"Token {self._api_key}",
            "Content-Type": "application/json",
            "Prefer": "wait",  # Request streaming-friendly response
        }
        base = self._base_url.rstrip("/")

        # Step 1: Create prediction
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base}/v1/predictions",
                headers=headers,
                json={
                    "version": model,  # Replicate resolves latest version from slug
                    "input": input_data,
                },
            )

            if resp.status_code == 401:
                raise RuntimeError("Replicate API key invalid or expired")
            if resp.status_code != 201:
                raise RuntimeError(
                    f"Replicate create prediction HTTP {resp.status_code}: {resp.text[:400]}"
                )

            data = resp.json()
            prediction_id = data["id"]
            status = data.get("status", "starting")
            logger.info(
                "[Replicate] prediction %s → status=%s model=%s",
                prediction_id, status, model,
            )

        # Step 2: Poll
        poll_interval = 5 if media_type == "video" else 2
        started_at = time.monotonic()

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                elapsed = time.monotonic() - started_at
                if elapsed >= timeout:
                    # Cancel the prediction to avoid runaway charges
                    try:
                        await client.post(
                            f"{base}/v1/predictions/{prediction_id}/cancel",
                            headers=headers,
                        )
                    except Exception:
                        pass
                    raise RuntimeError(
                        f"Replicate prediction {prediction_id} timed out after {timeout}s"
                    )

                await asyncio.sleep(poll_interval)

                try:
                    resp = await client.get(
                        f"{base}/v1/predictions/{prediction_id}",
                        headers=headers,
                    )

                    if resp.status_code != 200:
                        logger.warning(
                            "[Replicate] poll HTTP %s, retrying…", resp.status_code
                        )
                        continue

                    data = resp.json()
                    status = data.get("status", "")

                    logger.info(
                        "[Replicate] %s status=%s elapsed=%.0fs",
                        prediction_id, status, elapsed,
                    )

                    if status == "succeeded":
                        data["_elapsed"] = elapsed
                        return data

                    if status in ("failed", "canceled"):
                        error = data.get("error", "unknown")
                        raise RuntimeError(
                            f"Replicate prediction {prediction_id} failed: {error}"
                        )

                    # "starting", "processing" → keep polling

                except (httpx.ReadTimeout, httpx.ConnectError) as e:
                    logger.warning("[Replicate] poll network error: %s, retrying…", e)
                    continue

        raise RuntimeError(
            f"Replicate prediction {prediction_id} timed out after {timeout}s"
        )


def _extract_url(result: dict) -> str:
    """Extract media URL from Replicate prediction output."""
    output = result.get("output", "")
    if not output:
        return ""

    # Output can be a string URL, a list of URLs, or a list of FileOutput objects
    if isinstance(output, str):
        return output
    if isinstance(output, list) and len(output) > 0:
        first = output[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("url", first.get("image", "")) or str(first)
    if isinstance(output, dict):
        return output.get("url", output.get("image", "")) or ""
    return str(output)
