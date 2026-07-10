"""
KIE.ai unified adapter — one API key for all models (video + image).

KIE.ai uses a unified task-based API:
  POST /api/v1/jobs/createTask       → submit async job
  GET  /api/v1/jobs/getTaskDetail    → poll for results

Docs: https://docs.kie.ai/
"""

import asyncio
import json
import logging
import os
import time
from typing import Optional

import httpx

from app.adapters.base import BaseModelAdapter, GenerationResult, MediaSize
from app.adapters.registry import register_adapter
from app.config import settings

logger = logging.getLogger(__name__)

# ─── KIE model_id mapping ───────────────────────────────────
# Confirmed working model IDs (tested 2026-05-24)
# Image models use flat names; video models use provider/model format
KIE_MODEL_IDS = {
    # ─── Image models (15) internal → KIE API model ID ───
    # ✅ verified working against the live KIE gateway (unified createTask)
    "gpt-image-2": "gpt-image-2-text-to-image",
    "dall-e-3": "gpt-image-2-text-to-image",
    "nano-banana": "nano-banana-2",
    "nano-banana-2": "nano-banana-2",
    "nano-banana-pro": "nano-banana-pro",
    "nano-banana-basic": "google/nano-banana",
    "imagen-4": "google/imagen4",
    "imagen-4-fast": "google/imagen4-fast",
    "imagen-4-ultra": "google/imagen4-ultra",
    # ── unverified guesses (kept for manual selection; may 422) ──
    "flux-1.1-pro": "black-forest/flux-1.1-pro",
    "flux-1-dev": "black-forest/flux-1-dev",
    "flux-kontext": "black-forest/flux-kontext",
    "ideogram-v3": "ideogram/ideogram-v3",
    "recraft-v3": "recraft/recraft-v3",
    "seedream-3": "bytedance/seedream-3",
    "qwen-image": "alibaba/qwen-image",
    "hidream-i1": "hidream/hidream-i1",
    "sdxl": "stability/sdxl",
    "midjourney-v7": "midjourney/v7",
    "grok-image": "grok/grok-image",
    # KIE API image IDs → self (direct lookup)
    "gpt-image-2-text-to-image": "gpt-image-2-text-to-image",
    "nano-banana-2": "nano-banana-2",
    # ─── Video models (22) internal → KIE API model ID ───
    "seedance-2.0": "bytedance/seedance-2",
    "seedance-2.0-fast": "bytedance/seedance-2-fast",
    "seedance-2": "bytedance/seedance-2",
    "seedance-2-fast": "bytedance/seedance-2-fast",
    "veo-3.1": "veo3/veo-3.1",
    "veo-3.1-fast": "veo3/veo-3.1-fast",
    "veo-3": "veo3/veo-3",
    "sora-2": "sora/sora-2",
    "sora-2-pro": "sora/sora-2-pro",
    # Kling — verified-recognised IDs on the live gateway
    "kling-3.0": "kling-3.0/video",
    "kling-2.6": "kling-2.6/text-to-video",
    "kling-2.5-turbo": "kling/v2-5-turbo-text-to-video-pro",
    "kling-2.1-master": "kling/v2-1-master-text-to-video",
    "kling-2.1-pro": "kling/v2-1-pro",
    "kling-1.6": "kling/kling-v1.6",
    "wan-2.5": "wan/wan-2.5",
    "wan-2.2": "wan/wan-2.2",
    "hailuo-2.3": "minimax/hailuo-2.3",
    "hailuo-02": "minimax/hailuo-02",
    "grok-video": "grok/grok-video",
    "runway-gen4": "runway-ai/gen-4",
    "runway-gen3": "runway-ai/gen-3-alpha",
    "luma-ray-2": "luma/ray-2",
    "pika-2.2": "pika/pika-2.2",
    "hunyuan-video": "tencent/hunyuan-video",
    "ltx-video": "lightricks/ltx-video",
    # KIE video IDs → self
    "bytedance/seedance-2": "bytedance/seedance-2",
    "bytedance/seedance-2-fast": "bytedance/seedance-2-fast",
}


def _resolve_kie_model_id(model_name: str) -> str:
    """Map internal model name → KIE model_id, fallback to raw name."""
    return KIE_MODEL_IDS.get(model_name, model_name)


# ─── Video model detection ─────────────────────────────────
_KIE_VIDEO_PREFIXES = (
    "kling/", "bytedance/", "runway-ai/", "veo3/", "wan/", "happyhorse/",
    "sora/", "minimax/", "grok/", "luma/", "pika/", "tencent/", "lightricks/",
)


# ── KIE pricing + cost extraction ───────────────────────────

# KIE pricing table (credits per request) — fallback when API doesn't return cost
_KIE_PRICING = {
    "image": {
        "gpt-image-2-text-to-image": 5,
        "nano-banana-2": 2,
    },
    "video": {
        "bytedance/seedance-2": 4,       # per 5 seconds
        "bytedance/seedance-2-fast": 3,   # per 5 seconds
    },
}


def _extract_kie_cost(task: dict, media_type: str, duration: int = 0) -> float:
    """Extract cost from KIE API response, falling back to pricing table."""
    # 1. Try direct cost fields from KIE response
    for field in ("credits", "creditUsed", "cost", "consumedCredits", "credit", "totalCredits"):
        val = task.get(field)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass

    # 2. Try nested resultJson / billing
    for container_key in ("resultJson", "billing", "meta"):
        container = task.get(container_key, {})
        if isinstance(container, dict):
            for field in ("credits", "creditUsed", "cost"):
                val = container.get(field)
                if val is not None:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        pass

    # 3. Fallback: pricing table
    model_str = str(task.get("model", ""))
    pricing = _KIE_PRICING.get(media_type, {})
    for model_id, base_cost in pricing.items():
        if model_id in model_str:
            if media_type == "video" and duration > 0:
                return round(base_cost * max(duration, 1) / 5, 2)
            return float(base_cost)

    # 4. Generic fallback
    if media_type == "video":
        return round(max(duration, 1) * 0.6, 2)
    return 2.0


def _extract_url(result: dict, key: str = "imageUrl") -> str:
    """Extract media URL from KIE resultJson.resultUrls or top-level field."""
    # Top-level field (legacy)
    url = result.get(key, "")
    if url:
        return url
    
    # Modern KIE response: resultJson.resultUrls[0]
    result_json = result.get("resultJson", "")
    if result_json:
        try:
            parsed = json.loads(result_json) if isinstance(result_json, str) else result_json
            urls = parsed.get("resultUrls", [])
            if urls:
                return urls[0]
        except (json.JSONDecodeError, TypeError):
            pass
    return ""


def _is_video_kie_model(kie_model_id: str) -> bool:
    return any(kie_model_id.startswith(p) for p in _KIE_VIDEO_PREFIXES)


# ─── Size / ratio helpers ───────────────────────────────────
# Handles both MediaSize enum values and raw size strings
_SIZE_TO_RATIO = {
    "256x256": "1:1",
    "512x512": "1:1", 
    "1024x1024": "1:1",
    "1080x1080": "1:1",
    "1920x1080": "16:9",
    "1080x1920": "9:16",
    "1024x768": "4:3",
    "3840x2160": "16:9",
    "768x1024": "3:4",
}

_SIZE_TO_KIE_RESOLUTION = {
    "1920x1080": "1080p",
    "1080x1920": "1080p", 
    "3840x2160": "4k",
}


def _size_to_ratio(size: str) -> str:
    """Convert a raw size string to aspect ratio for KIE."""
    return _SIZE_TO_RATIO.get(size, "1:1")


def _size_to_resolution(size: str) -> str:
    """Convert a raw size string to KIE resolution."""
    return _SIZE_TO_KIE_RESOLUTION.get(size, "720p")


@register_adapter
class KieAdapter(BaseModelAdapter):
    """Unified adapter for all models via KIE.ai API."""

    @property
    def _base_url(self) -> str:
        return settings.KIE_BASE_URL or "https://api.kie.ai"

    @property
    def _api_key(self) -> str:
        return settings.KIE_API_KEY or os.getenv("KIE_API_KEY", "")

    # ── availability ─────────────────────────────────────────
    @property
    def provider_name(self) -> str:
        return "KIE.ai"

    @property
    def supported_models(self) -> list[str]:
        return list(KIE_MODEL_IDS.keys())

    @property
    def capabilities(self) -> dict:
        return {
            "max_resolution": "4K",
            "max_duration_s": 60,
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
        model_id: str = "gpt-image-2",
        size: str = "1024x1024",
        count: int = 1,
        style: Optional[str] = None,
        **kwargs,
    ) -> GenerationResult:
        """Generate image via KIE unified API."""
        kie_id = _resolve_kie_model_id(model_id)
        logger.info("[KIE] image → model=%s prompt=%r", kie_id, prompt)

        payload = {
            "model": kie_id,
            "prompt": prompt,
        }

        # Aspect ratio — model families disagree on the key name, so send the
        # verified-compatible superset (camel + snake). KIE ignores unknown keys.
        ratio = _size_to_ratio(size)
        payload["aspectRatio"] = ratio
        payload["aspect_ratio"] = ratio

        # Number of images (n varies by model)
        if count > 1:
            payload["n"] = count

        result = await self._submit_and_poll(payload, media_type="image", timeout=180)

        cost = _extract_kie_cost(result, "image")

        return GenerationResult(
            media_url=_extract_url(result, "imageUrl"),
            media_type="image",
            model=kie_id,
            cost=cost,
            meta={"kie_task_id": result.get("taskId", ""), "resolution": size},
        )

    # ── video generation ─────────────────────────────────────
    async def generate_video(
        self,
        prompt: str,
        *,
        model_id: str = "seedance-2.0",
        duration: int = 5,
        resolution: str = "1080p",
        image_url: Optional[str] = None,
        **kwargs,
    ) -> GenerationResult:
        """Generate video via KIE unified API."""
        kie_id = _resolve_kie_model_id(model_id)
        logger.info("[KIE] video → model=%s prompt=%r dur=%ds", kie_id, prompt, duration)

        payload = {
            "model": kie_id,
            "prompt": prompt,
            "duration": duration,
        }

        # Resolution mapping
        kie_res = _size_to_resolution(resolution)
        payload["resolution"] = kie_res

        # Image-to-video
        if image_url:
            payload["imageUrl"] = image_url

        # Not every model accepts every resolution token (e.g. seedance-2-fast
        # rejects 1080p). Retry down a safe ladder on "invalid resolution" (422)
        # so a valid request is never lost to a resolution mismatch.
        res_ladder = [r for r in (kie_res, "720p", "480p") if r]
        seen = set()
        result = None
        last_err: Optional[Exception] = None
        for res_try in res_ladder:
            if res_try in seen:
                continue
            seen.add(res_try)
            payload["resolution"] = res_try
            try:
                result = await self._submit_and_poll(payload, media_type="video", timeout=600)
                break
            except RuntimeError as e:
                msg = str(e).lower()
                if "resolution" in msg and ("422" in msg or "invalid" in msg):
                    logger.warning("[KIE] resolution %s rejected for %s, retrying lower", res_try, kie_id)
                    last_err = e
                    continue
                raise
        if result is None:
            raise last_err or RuntimeError("KIE video generation failed: no valid resolution")

        url = _extract_url(result, "videoUrl")
        cover = _extract_url(result, "coverUrl") or url
        cost = _extract_kie_cost(result, "video", duration)
        return GenerationResult(
            media_url=url,
            thumbnail_url=cover,
            media_type="video",
            model=kie_id,
            cost=cost,
            duration=float(duration),
            meta={
                "kie_task_id": result.get("taskId", ""),
                "resolution": kie_res,
                "duration": duration,
            },
        )

    # ── file upload: local bytes → public KIE URL (3-day TTL) ─
    async def upload_public_url(self, data: bytes, *, filename: str = "upload.png",
                                content_type: str = "image/png",
                                upload_path: str = "betty/uploads") -> str:
        """Upload raw bytes to KIE and return a publicly-fetchable URL.
        Needed so KIE models (lip-sync, i2v) can reach user-uploaded assets."""
        import base64 as _b64
        if not self._api_key:
            raise RuntimeError("KIE_API_KEY not configured")
        data_url = f"data:{content_type};base64," + _b64.b64encode(data).decode()
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                "https://kieai.redpandaai.co/api/file-base64-upload",
                headers=headers,
                json={"base64Data": data_url, "uploadPath": upload_path, "fileName": filename},
            )
            resp.raise_for_status()
            body = resp.json()
        data_obj = body.get("data") or {}
        url = (data_obj.get("downloadUrl") or data_obj.get("fileUrl")
               or data_obj.get("url") or "")
        if not url:
            raise RuntimeError(f"KIE upload returned no URL: {body}")
        return url

    # ── audio: text-to-speech ────────────────────────────────
    async def generate_speech(self, text: str, *, voice: str = "Rachel",
                              model_id: str = "elevenlabs/text-to-speech-multilingual-v2",
                              **kwargs) -> GenerationResult:
        """Generate a voiceover (TTS) → returns an audio GenerationResult."""
        logger.info("[KIE] tts → %r voice=%s", text[:40], voice)
        payload = {"model": model_id, "text": text, "voice": voice}
        for k in ("stability", "similarity_boost", "style", "speed", "language_code"):
            if k in kwargs and kwargs[k] is not None:
                payload[k] = kwargs[k]
        result = await self._submit_and_poll(payload, media_type="audio", timeout=180)
        url = _extract_url(result, "audioUrl")
        return GenerationResult(
            media_url=url, media_type="audio", model=model_id,
            cost=_extract_kie_cost(result, "audio"),
            meta={"kie_task_id": result.get("taskId", ""), "voice": voice},
        )

    # ── lip-sync / talking avatar (image + audio → video) ─────
    async def generate_lipsync(self, *, image_url: str, audio_url: str,
                               prompt: str = "a person talking naturally on camera",
                               model_id: str = "infinitalk/from-audio",
                               resolution: str = "480p", **kwargs) -> GenerationResult:
        """Drive a portrait image with an audio track → talking video."""
        logger.info("[KIE] lipsync → model=%s img=%r", model_id, image_url[:60])
        payload = {"model": model_id, "image_url": image_url,
                   "audio_url": audio_url, "prompt": prompt}
        # infinitalk supports a resolution knob; kling avatar does not.
        if model_id.startswith("infinitalk"):
            payload["resolution"] = resolution
        # Lip-sync (esp. infinitalk) can run many minutes for longer audio.
        result = await self._submit_and_poll(payload, media_type="video", timeout=1200)
        url = _extract_url(result, "videoUrl")
        cover = _extract_url(result, "coverUrl") or ""
        return GenerationResult(
            media_url=url, thumbnail_url=cover, media_type="video", model=model_id,
            cost=_extract_kie_cost(result, "video"),
            meta={"kie_task_id": result.get("taskId", ""), "lipsync": True},
        )

    # ── core: submit + poll ─────────────────────────────────
    async def _submit_and_poll(
        self, payload: dict, *, media_type: str, timeout: int = 180
    ) -> dict:
        """Submit KIE task, then poll until success/failure."""
        if not self._api_key:
            raise RuntimeError("KIE_API_KEY not configured — cannot call KIE API")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        base = self._base_url.rstrip("/")

        # Step 1: Submit — KIE expects {model, input: {...}}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base}/api/v1/jobs/createTask",
                headers=headers,
                json={"model": payload["model"], "input": {k: v for k, v in payload.items() if k != "model"}},
            )

            if resp.status_code != 200:
                raise RuntimeError(
                    f"KIE createTask HTTP {resp.status_code}: {resp.text[:300]}"
                )

            data = resp.json()
            if int(data.get("code", 0)) != 200:
                raise RuntimeError(
                    f"KIE API error: code={data.get('code')} msg={data.get('msg', '')}"
                )

            task_id = data["data"]["taskId"]
            logger.info("[KIE] task submitted: %s", task_id)

        # Step 2: Poll
        poll_interval = 6 if media_type == "video" else 3
        max_waiting_seconds = 600 if media_type == "video" else 160

        async with httpx.AsyncClient(timeout=30) as client:
            started_at = time.monotonic()
            waiting_started: float | None = None  # real wall-clock time when waiting began
            while True:
                elapsed = time.monotonic() - started_at
                if elapsed >= timeout:
                    raise RuntimeError(
                        f"KIE task {task_id} timed out after {timeout}s "
                        f"(real elapsed={elapsed:.0f}s)"
                    )

                await asyncio.sleep(poll_interval)

                try:
                    resp = await client.get(
                        f"{base}/api/v1/jobs/recordInfo",
                        headers={"Authorization": f"Bearer {self._api_key}"},
                        params={"taskId": task_id},
                    )

                    if resp.status_code != 200:
                        logger.warning("[KIE] poll error HTTP %s, retrying…", resp.status_code)
                        continue

                    data = resp.json()
                    if int(data.get("code", 0)) != 200:
                        continue  # transient, retry

                    task = data.get("data", {})
                    # KIE uses "state" field
                    status = (task.get("state") or task.get("taskStatus") or task.get("status") or "").lower()

                    logger.info("[KIE] task %s state=%s elapsed=%ds", task_id, status, elapsed)

                    if status in ("success", "completed", "done"):
                        return task

                    if status in ("failed", "fail", "error", "canceled"):
                        raise RuntimeError(
                            f"KIE task {task_id} failed: "
                            f"{task.get('failMsg', task.get('failCode', task.get('errorMessage', 'unknown')))}"
                        )

                    # Track waiting time — if stuck in queue too long, timeout early
                    if status in ("waiting", "queued", "submitting"):
                        if waiting_started is None:
                            waiting_started = elapsed
                        elif elapsed - waiting_started > max_waiting_seconds:
                            raise RuntimeError(
                                f"KIE queue timeout after {max_waiting_seconds}s — "
                                f"GPU resources busy, auto-fallback recommended. "
                                f"排队超时：GPU 资源紧张，请稍后重试或切换至更快的模型"
                            )
                    else:
                        waiting_started = None  # reset — now processing

                    # "running" / "processing" → keep polling
                except (httpx.ReadTimeout, httpx.ConnectError) as e:
                    logger.warning("[KIE] poll network error: %s, retrying…", e)
                    continue

        raise RuntimeError(
            f"KIE task {task_id} timed out after {timeout}s"
        )
