from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from pathlib import Path


class MediaSize(str, Enum):
    # Standard image sizes
    SQ_256 = "256x256"
    SQ_512 = "512x512"
    SQ_1024 = "1024x1024"
    HD_1080 = "1920x1080"  # landscape
    V_9_16 = "1080x1920"   # portrait (vertical/short-video)
    W_16_9 = "1920x1080"   # landscape
    W_4_3 = "1024x768"
    UHD_4K = "3840x2160"


@dataclass
class GenerationResult:
    """Unified result from any model adapter"""
    media_url: str                          # Local path or public URL
    thumbnail_url: Optional[str] = None
    media_type: str = "image"               # "image" or "video"
    model: str = ""
    resolution: str = "1024x1024"
    duration: Optional[float] = None        # seconds for video
    cost: float = 0.0                       # credits consumed
    meta: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def is_image(self) -> bool:
        return self.media_type == "image"

    @property
    def is_video(self) -> bool:
        return self.media_type == "video"

    def to_dict(self) -> dict:
        return {
            "media_url": self.media_url,
            "thumbnail_url": self.thumbnail_url,
            "media_type": self.media_type,
            "model": self.model,
            "resolution": self.resolution,
            "duration": self.duration,
            "cost": self.cost,
            "meta": self.meta,
            "error": self.error,
        }


class BaseModelAdapter(ABC):
    """All model adapters must implement this"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """e.g., 'OpenAI', 'ByteDance', 'Kling'"""
        ...

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        """Model identifiers this adapter handles"""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> dict:
        """
        {
            "media_types": ["image", "video"],
            "max_resolution": "4K",
            "max_duration_s": 60,
            "avg_latency_s": 30,
            "styles": ["realistic", "anime", ...],
            "cost_per_image_credits": 5,
            "cost_per_5s_video_credits": 3,
        }
        """
        ...

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: str = "auto",
        count: int = 1,
        **kwargs,
    ) -> list[GenerationResult]:
        """Generate image(s) from prompt"""
        ...

    @abstractmethod
    async def generate_video(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        duration: int = 5,
        resolution: str = "1080p",
        **kwargs,
    ) -> GenerationResult:
        """Generate video from prompt or image"""
        ...

    async def health_check(self) -> bool:
        """Check if the model API is accessible"""
        return True

    def estimate_cost(self, media_type: str, **kwargs) -> float:
        """Estimate credits for this request"""
        caps = self.capabilities
        if media_type == "image":
            return caps.get("cost_per_image_credits", 5)
        duration = kwargs.get("duration", 5)
        per_5s = caps.get("cost_per_5s_video_credits", 3)
        return max(per_5s, duration / 5 * per_5s)
