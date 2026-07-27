"""
Collector Service — Manages source lifecycle and collection orchestration.
Single responsibility: "collect from source X and return raw posts".
"""
from __future__ import annotations

import logging
from typing import Optional

from app.collector.sources.base import CollectResult
from app.collector.sources.reddit import RedditSource
from app.collector.sources.youtube import YouTubeSource
from app.collector.sources.tiktok import TikTokSource
from app.collector.sources.x_browser import XBrowserSource

logger = logging.getLogger(__name__)


class CollectorService:
    """Orchestrates content collection from registered sources."""

    def __init__(self):
        self._sources: dict[str, BaseSource] = {}
        self.register("reddit", RedditSource())
        self.register("youtube", YouTubeSource())
        self.register("tiktok", TikTokSource())
        self.register("x", XBrowserSource())

    def register(self, name: str, source):
        """Register a new collector source."""
        from app.collector.sources.base import BaseSource
        if not isinstance(source, BaseSource):
            raise TypeError(f"Source must be BaseSource, got {type(source)}")
        self._sources[name] = source
        logger.info("[collector] Registered source: %s", name)

    def get(self, name: str):
        """Get a registered source by name."""
        if name not in self._sources:
            raise ValueError(f"Unknown source: {name}. Available: {list(self._sources.keys())}")
        return self._sources[name]

    def list_sources(self) -> list[str]:
        return list(self._sources.keys())

    async def collect(self, source: str, **kwargs) -> CollectResult:
        """Collect from a specific source, with circuit breaker protection."""
        collector = self.get(source)
        return await collector.collect_safe(**kwargs)

    def health(self) -> dict:
        """Health status of all sources."""
        return {
            name: {
                "available": True,
                "circuit_open": not src.is_healthy,
            }
            for name, src in self._sources.items()
        }

    @property
    def reddit(self): return self._sources["reddit"]
    @property
    def youtube(self): return self._sources["youtube"]


collector_service = CollectorService()
