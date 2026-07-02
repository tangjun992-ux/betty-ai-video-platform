"""
ByteDance Seedance Adapter — supports SeedArt (image) + Seedance 2.0 Fast (video)
"""
import os
import asyncio
import hashlib
import httpx
import json
import logging
from typing import Optional
from pathlib import Path
from app.adapters.base import BaseModelAdapter, GenerationResult
from app.adapters.registry import register_adapter
from app.config import settings

logger = logging.getLogger(__name__)


@register_adapter
class SeedanceAdapter(BaseModelAdapter):
    @property
    def provider_name(self) -> str:
        return "ByteDance / Seedance"

    @property
    def supported_models(self) -> list[str]:
        return [
            "bytedance/seedart",
            "bytedance/seedance-2-fast",
            "bytedance/seedance-1",
        ]

    @property
    def capabilities(self) -> dict:
        return {
            "media_types": ["image", "video"],
            "max_resolution": "2K",
            "max_duration_s": 10,
            "avg_latency_s": 30,
            "styles": ["realistic", "portrait", "landscape", "product", "anime"],
            "cost_per_image_credits": 3,
            "cost_per_5s_video_credits": 3,
        }

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: str = "realistic",
        count: int = 1,
        **kwargs,
    ) -> list[GenerationResult]:
        api_key = settings.SEEDANCE_API_KEY or os.getenv("SEEDANCE_API_KEY", "")
        if not api_key:
            raise RuntimeError("SEEDANCE_API_KEY not configured")

        model = "seedart"
        resolution = self._map_size(size)

        results = []
        for i in range(count):
            try:
                resp = await self._call_image_api(
                    api_key=api_key,
                    prompt=prompt,
                    model=model,
                    size=resolution,
                )
                image_url = resp.get("data", [{}])[0].get("url", "")
                saved_path = await self._save_from_url(
                    image_url, f"seedart_{prompt[:20]}", i
                )

                results.append(
                    GenerationResult(
                        media_url=saved_path,
                        thumbnail_url=saved_path,
                        media_type="image",
                        model=model,
                        resolution=size,
                        cost=3,
                        meta={"original_url": image_url, "style": style},
                    )
                )
            except Exception as e:
                logger.error(f"Seedance image generation failed: {e}")
                results.append(
                    GenerationResult(
                        media_url="", media_type="image", model=model, cost=0, error=str(e)
                    )
                )
        return results

    async def generate_video(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        video_url: Optional[str] = None,
        duration: int = 5,
        resolution: str = "1080p",
        **kwargs,
    ) -> GenerationResult:
        api_key = settings.SEEDANCE_API_KEY or os.getenv("SEEDANCE_API_KEY", "")
        if not api_key:
            raise RuntimeError("SEEDANCE_API_KEY not configured")

        try:
            # Step 1: Submit generation task
            submit_resp = await self._call_video_submit(
                api_key=api_key,
                prompt=prompt,
                image_url=image_url,
                video_url=video_url,
                duration=duration,
                resolution=resolution,
            )
            task_id = submit_resp.get("id", submit_resp.get("task_id", ""))
            if not task_id:
                raise RuntimeError(f"No task_id returned: {submit_resp}")

            # Step 2: Poll for completion
            video_url = await self._poll_video_status(
                api_key, task_id, timeout=600
            )

            # Step 3: Download
            saved_path = await self._save_from_url(
                video_url, f"seedance_{prompt[:20]}", 0, ext="mp4"
            )

            return GenerationResult(
                media_url=saved_path,
                thumbnail_url=saved_path.replace(".mp4", "_thumb.jpg"),
                media_type="video",
                model="seedance-2-fast",
                resolution=resolution,
                duration=duration,
                cost=max(3, duration / 5 * 3),
                meta={"original_url": video_url, "task_id": task_id},
            )
        except Exception as e:
            logger.error(f"Seedance video generation failed: {e}")
            return GenerationResult(
                media_url="",
                media_type="video",
                model="seedance-2-fast",
                cost=0,
                error=str(e),
            )

    async def health_check(self) -> bool:
        try:
            api_key = settings.SEEDANCE_API_KEY or os.getenv("SEEDANCE_API_KEY", "")
            return bool(api_key)
        except Exception:
            return False

    def _map_size(self, size: str) -> str:
        mapping = {
            "1024x1024": "1024x1024",
            "1920x1080": "1920x1080",
            "1080x1920": "1080x1920",
            "512x512": "512x512",
        }
        return mapping.get(size, "1024x1024")

    async def _call_image_api(self, api_key: str, **params) -> dict:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.SEEDANCE_BASE_URL}/images/generations",
                json=params,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def _call_video_submit(
        self, api_key: str, prompt: str, image_url: str, video_url: Optional[str] = None, duration: int = 5, resolution: str = "1080p"
    ) -> dict:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "seedance-2-fast",
            "prompt": prompt,
            "duration": duration,
        }
        if image_url:
            payload["image_url"] = image_url
        if video_url:
            payload["video_url"] = video_url
            payload["motion_reference"] = True
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.SEEDANCE_BASE_URL}/videos/generations",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def _poll_video_status(
        self, api_key: str, task_id: str, timeout: int = 600
    ) -> str:
        """Poll Seedance video task until completion or timeout.

        Uses real wall-clock time (time.monotonic) — NOT an accumulating counter —
        to correctly bound total wait time regardless of API response latency.
        """
        headers = {"Authorization": f"Bearer {api_key}"}
        started_at = asyncio.get_event_loop().time()
        poll_interval = 3  # seconds between polls
        while True:
            elapsed = asyncio.get_event_loop().time() - started_at
            if elapsed >= timeout:
                raise TimeoutError(
                    f"Seedance video generation timed out after {timeout}s "
                    f"(task_id={task_id})"
                )
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(
                        f"{settings.SEEDANCE_BASE_URL}/videos/{task_id}",
                        headers=headers,
                    )
                    resp.raise_for_status()
                    status = resp.json()
                    state = status.get("status", status.get("state", ""))
                    logger.debug(
                        f"Seedance poll: task={task_id} state={state} elapsed={elapsed:.0f}s"
                    )
                    if "completed" in state.lower() or "succeed" in state.lower():
                        video_url = status.get("result", {}).get(
                            "video_url", status.get("output", {}).get("video_url", "")
                        )
                        if video_url:
                            logger.info(
                                f"Seedance video ready: task={task_id} total_time={elapsed:.0f}s"
                            )
                            return video_url
                        # Completed but no URL yet — wait a bit
                        logger.warning(
                            f"Seedance task {task_id} completed but no URL; retrying"
                        )
                    elif "failed" in state.lower():
                        raise RuntimeError(
                            f"Seedance video generation failed: {json.dumps(status)}"
                        )
            except (httpx.ReadTimeout, httpx.ConnectTimeout):
                logger.warning(
                    f"Seedance poll timeout for task={task_id}, elapsed={elapsed:.0f}s; retrying"
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    logger.warning(
                        f"Seedance API 5xx for task={task_id}: {e.response.status_code}; retrying"
                    )
                else:
                    raise RuntimeError(
                        f"Seedance API error {e.response.status_code}: {e.response.text[:200]}"
                    ) from e
            await asyncio.sleep(poll_interval)

    async def _save_from_url(
        self, url: str, name: str, idx: int, ext: str = "png"
    ) -> str:
        storage_dir = Path(settings.STORAGE_LOCAL_PATH) / (
            "images" if ext == "png" else "videos"
        )
        storage_dir.mkdir(parents=True, exist_ok=True)
        file_hash = hashlib.md5(f"{name}{idx}".encode()).hexdigest()[:12]
        file_path = storage_dir / f"{file_hash}.{ext}"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            file_path.write_bytes(resp.content)
        subfolder = "images" if ext == "png" else "videos"
        return f"/api/v1/media/{subfolder}/{file_path.name}"
