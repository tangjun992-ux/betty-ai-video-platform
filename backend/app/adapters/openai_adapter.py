"""
OpenAI GPT-5.4 Image / DALL-E 3 Adapter
"""
import os
import httpx
import logging
from typing import Optional
from app.adapters.base import BaseModelAdapter, GenerationResult, MediaSize
from app.adapters.registry import register_adapter
from app.config import settings

logger = logging.getLogger(__name__)


@register_adapter
class OpenAIAdapter(BaseModelAdapter):
    @property
    def provider_name(self) -> str:
        return "OpenAI"

    @property
    def supported_models(self) -> list[str]:
        return [
            "openai/gpt-5.4-image",
            "openai/dall-e-3",
        ]

    @property
    def capabilities(self) -> dict:
        return {
            "media_types": ["image"],
            "max_resolution": "4K",
            "max_duration_s": 0,
            "avg_latency_s": 15,
            "styles": ["vivid", "natural", "digital-art", "anime", "3d-render", "oil-painting"],
            "cost_per_image_credits": 5,
            "cost_per_5s_video_credits": 0,
        }

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: str = "vivid",
        count: int = 1,
        quality: str = "standard",
        **kwargs,
    ) -> list[GenerationResult]:
        """Generate images using OpenAI API"""
        api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")

        base_url = settings.OPENAI_BASE_URL
        model = settings.OPENAI_BASE_URL and "gpt-image-1" or "dall-e-3"
        
        results = []
        for _ in range(count):
            try:
                resp = await self._call_api(
                    api_key=api_key,
                    base_url=base_url,
                    prompt=prompt,
                    model=model,
                    size=size,
                    quality=quality,
                    style=style,
                    n=1,
                    response_format="url",
                )
                
                image_url = resp.get("data", [{}])[0].get("url", "")
                if not image_url:
                    raise RuntimeError(f"No image URL returned: {resp}")

                # Download and save locally
                saved_path = await self._save_from_url(image_url, prompt, count)
                
                results.append(GenerationResult(
                    media_url=saved_path,
                    thumbnail_url=saved_path,
                    media_type="image",
                    model=model,
                    resolution=size,
                    cost=5,
                    meta={"original_url": image_url},
                ))
            except Exception as e:
                logger.error(f"OpenAI image generation failed: {e}")
                results.append(GenerationResult(
                    media_url="",
                    media_type="image",
                    model=model,
                    cost=0,
                    error=str(e),
                ))

        return results

    async def generate_video(self, *args, **kwargs) -> GenerationResult:
        raise NotImplementedError("OpenAI adapter does not support video generation yet")

    async def _call_api(self, api_key: str, base_url: str, **params) -> dict:
        """Call OpenAI image generation API"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{base_url}/images/generations",
                json=params,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def _save_from_url(self, url: str, prompt: str, idx: int) -> str:
        """Download image from URL and save to local storage"""
        import hashlib
        import os
        from pathlib import Path
        
        storage_dir = Path(settings.STORAGE_LOCAL_PATH) / "images"
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        file_hash = hashlib.md5(f"{prompt}{idx}".encode()).hexdigest()[:12]
        file_path = storage_dir / f"{file_hash}.png"
        
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            file_path.write_bytes(resp.content)
        
        return f"/api/v1/media/images/{file_path.name}"

    async def health_check(self) -> bool:
        try:
            api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                return False
            # Simple API key validation
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{settings.OPENAI_BASE_URL}/models",
                    headers=headers,
                )
                return resp.status_code == 200
        except Exception:
            return False
