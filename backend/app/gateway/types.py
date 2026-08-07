"""Gateway type definitions — capability-based routing contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Capability(str, Enum):
    """Unified generation capabilities (independent of provider)."""
    IMAGE_GENERATE = "image.generate"
    IMAGE_EDIT = "image.edit"
    VIDEO_GENERATE = "video.generate"
    LIPSYNC = "lipsync"
    MOTION = "motion"
    TTS = "tts"
    LLM_CHAT = "llm.chat"


@dataclass(frozen=True)
class ProviderTarget:
    """One hop in a provider chain."""
    provider: str           # kie | replicate | seedance | kling | openai
    remote_model: str       # provider-native model id / SKU
    priority: int = 1
    fallback_only: bool = False  # only used when primary fails
    timeout_s: int = 240
    weight: int = 100       # load-balance weight among primaries
    canary_percent: int = 0  # A/B: share of traffic when >0 (same priority band)
    region: str = ""        # empty = all regions; cn | us | eu


@dataclass(frozen=True)
class RouteDefinition:
    """Route: Betty SKU + capability → ordered provider chain."""
    capability: Capability
    model: str              # Betty internal model_id (gpt-image-2, seedance-2.0, …)
    chain: tuple[ProviderTarget, ...]
    description: str = ""


@dataclass
class GatewayExecutionResult:
    """Normalized gateway output with routing metadata."""
    result: Any                           # GenerationResult or list thereof
    capability: Capability
    model_requested: str
    model_used: str
    provider_used: str
    remote_model_used: str
    fallback_used: bool = False
    attempts: list[dict] = field(default_factory=list)
    latency_ms: int = 0
    cost: float = 0.0
    trace_id: str = ""

    def to_meta(self) -> dict:
        return {
            "gateway": True,
            "capability": self.capability.value,
            "model_requested": self.model_requested,
            "model_used": self.model_used,
            "provider_used": self.provider_used,
            "remote_model_used": self.remote_model_used,
            "fallback_used": self.fallback_used,
            "attempts": self.attempts,
            "latency_ms": self.latency_ms,
        }
