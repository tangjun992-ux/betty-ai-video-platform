"""
Abstract base class for all content sources.
Every source must implement collect() → list[RawPost].
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.collector.schemas import RawPost

logger = logging.getLogger(__name__)


@dataclass
class CollectResult:
    """Result of a collect operation with metadata."""
    source: str
    posts: list[RawPost]
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    duration_ms: float = 0.0

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def count(self) -> int:
        return len(self.posts)


class BaseSource(ABC):
    """Base class for all content sources.

    Subclasses must implement:
      - collect(params) -> CollectResult
      - source_name -> str
    """

    source_name: str = "base"

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._error_count = 0
        self._circuit_open = False
        self._circuit_opened_at: Optional[datetime] = None
        self._last_success_at: Optional[datetime] = None

    @abstractmethod
    async def collect(self, **kwargs) -> CollectResult:
        """Collect trending/hot content from the source.

        Args:
            **kwargs: Source-specific parameters (subreddit, query, limit, etc.)

        Returns:
            CollectResult with normalized RawPost objects.
        """
        ...

    async def collect_safe(self, **kwargs) -> CollectResult:
        """Circuit-breaker wrapped collect. Falls back to empty on failure."""
        import time

        # Circuit breaker check
        if self._circuit_open:
            if self._circuit_opened_at:
                elapsed = (datetime.now(timezone.utc) - self._circuit_opened_at).total_seconds()
                if elapsed < 300:  # 5min cooldown
                    return CollectResult(
                        source=self.source_name, posts=[],
                        error=f"Circuit open, {300 - elapsed:.0f}s remaining",
                    )
                else:
                    self._circuit_open = False
                    self._error_count = 0

        t0 = time.monotonic()
        try:
            result = await self.collect(**kwargs)
            result.duration_ms = (time.monotonic() - t0) * 1000
            self._error_count = 0
            self._last_success_at = datetime.now(timezone.utc)
            return result
        except Exception as e:
            self._error_count += 1
            logger.exception("[%s] Collection failed: %s", self.source_name, e)
            if self._error_count >= 5:
                self._circuit_open = True
                self._circuit_opened_at = datetime.now(timezone.utc)
                logger.error("[%s] Circuit breaker OPEN after 5 consecutive failures", self.source_name)
            return CollectResult(
                source=self.source_name, posts=[],
                error=str(e),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    def _normalize(self, raw: dict) -> RawPost:
        """Normalize a raw source item into a RawPost. Override per source."""
        return RawPost(**raw)

    @property
    def is_healthy(self) -> bool:
        return not self._circuit_open
