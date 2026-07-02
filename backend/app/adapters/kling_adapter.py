"""
Kling AI Adapter — supports Kling Video v3 Pro
"""
import os, httpx, asyncio, hashlib, logging
from typing import Optional
from pathlib import Path
from app.adapters.base import BaseModelAdapter, GenerationResult
from app.adapters.registry import register_adapter
from app.config import settings

logger = logging.getLogger(__name__)


@register_adapter
class KlingAdapter(BaseModelAdapter):
    @property
    def provider_name(self) -> str:
        return "Kling AI (可灵)"

    @property
    def supported_models(self) -> list[str]:
        return ["kling/video-v3-pro", "kling/video-v2", "kling/video-v1"]

    @property
    def capabilities(self) -> dict:
        return {
            "media_types": ["video"],
            "max_resolution": "4K",
            "max_duration_s": 60,
            "avg_latency_s": 120,
            "styles": ["cinematic", "documentary", "commercial", "dramatic", "anime", "realistic"],
            "cost_per_image_credits": 0,
            "cost_per_5s_video_credits": 6,
        }

    async def generate_image(self, *args, **kwargs):
        raise NotImplementedError("Kling adapter focuses on video generation")

    async def generate_video(
        self, prompt: str, image_url: Optional[str] = None,
        duration: int = 5, resolution: str = "1080p", **kwargs,
    ) -> GenerationResult:
        ak = settings.KLING_ACCESS_KEY or os.getenv("KLING_ACCESS_KEY", "")
        sk = settings.KLING_SECRET_KEY or os.getenv("KLING_SECRET_KEY", "")
        if not ak or not sk:
            raise RuntimeError("Kling API keys not configured")

        try:
            token = await self._get_token(ak, sk)
            submit_resp = await self._submit(token, prompt, image_url, duration)
            task_id = submit_resp.get("data", {}).get("task_id", submit_resp.get("task_id", ""))
            if not task_id:
                raise RuntimeError(f"No task_id: {submit_resp}")

            video_url = await self._poll(token, task_id, timeout=300)
            saved = await self._save(video_url, f"kling_{hashlib.md5(prompt.encode()).hexdigest()[:8]}")

            return GenerationResult(
                media_url=saved, thumbnail_url=saved.replace(".mp4", "_thumb.jpg"),
                media_type="video", model="kling/video-v3-pro", resolution=resolution,
                duration=duration, cost=max(6, duration / 5 * 6),
                meta={"task_id": task_id, "original_url": video_url},
            )
        except Exception as e:
            logger.error(f"Kling failed: {e}")
            return GenerationResult(media_url="", media_type="video", model="kling/video-v3-pro", cost=0, error=str(e))

    async def health_check(self) -> bool:
        try:
            ak = settings.KLING_ACCESS_KEY or os.getenv("KLING_ACCESS_KEY", "")
            sk = settings.KLING_SECRET_KEY or os.getenv("KLING_SECRET_KEY", "")
            if not ak or not sk:
                return False
            t = await self._get_token(ak, sk)
            return bool(t)
        except Exception:
            return False

    async def _get_token(self, ak: str, sk: str) -> str:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(f"{settings.KLING_BASE_URL}/v1/token", json={"access_key": ak, "secret_key": sk})
            r.raise_for_status()
            d = r.json()
            token = d.get("data", {}).get("token", d.get("token"))
            if not token:
                raise RuntimeError(f"No token: {d}")
            return token

    async def _submit(self, token: str, prompt: str, image_url: Optional[str], duration: int) -> dict:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"model": "kling-v3-pro", "prompt": prompt, "duration": duration, "mode": "std"}
        if image_url:
            payload["image"] = image_url
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{settings.KLING_BASE_URL}/v1/videos/generation", headers=headers, json=payload)
            r.raise_for_status()
            return r.json()

    async def _poll(self, token: str, task_id: str, timeout: int = 300) -> str:
        headers = {"Authorization": f"Bearer {token}"}
        elapsed = 0
        while elapsed < timeout:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{settings.KLING_BASE_URL}/v1/videos/generation/{task_id}", headers=headers)
                r.raise_for_status()
                d = r.json()
                tr = d.get("data", d)
                state = tr.get("task_status", tr.get("state", ""))
                if state in ("succeed", "success"):
                    vu = tr.get("task_result", {}).get("videos", [{}])[0].get("url", tr.get("video_url", ""))
                    if vu:
                        return vu
                    raise RuntimeError(f"No video_url: {d}")
                elif state in ("failed", "error"):
                    raise RuntimeError(f"Task failed: {d}")
            await asyncio.sleep(5)
            elapsed += 5
        raise TimeoutError(f"Kling timeout {timeout}s")

    async def _save(self, url: str, name: str) -> str:
        d = Path(settings.STORAGE_LOCAL_PATH) / "videos"
        d.mkdir(parents=True, exist_ok=True)
        fp = d / f"{name}.mp4"
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.get(url)
            r.raise_for_status()
            fp.write_bytes(r.content)
        return f"/api/v1/media/videos/{fp.name}"
