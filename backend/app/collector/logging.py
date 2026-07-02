"""
VIS Structured Logging — JSON-line structured logs for ELK/Grafana Loki.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional
import uuid


class VISLogger:
    """Structured JSON logger for VIS pipeline observability."""

    def __init__(self, name: str = "vis"):
        self._logger = logging.getLogger(name)
        self._trace_id: Optional[str] = None

    @property
    def trace_id(self) -> str:
        if self._trace_id is None:
            self._trace_id = uuid.uuid4().hex[:12]
        return self._trace_id

    def new_trace(self) -> str:
        self._trace_id = uuid.uuid4().hex[:12]
        return self._trace_id

    def _emit(self, level: str, message: str, **extra):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "trace_id": self.trace_id,
            "module": "vis",
        }
        log_entry.update(extra)
        self._logger.log(getattr(logging, level.upper(), logging.INFO), json.dumps(log_entry))

    def info(self, msg: str, **extra): self._emit("info", msg, **extra)
    def warn(self, msg: str, **extra): self._emit("warning", msg, **extra)
    def error(self, msg: str, **extra): self._emit("error", msg, **extra)
    def debug(self, msg: str, **extra): self._emit("debug", msg, **extra)

    # Domain-specific helpers
    def collection_start(self, source: str, params: dict):
        self.info("collection.started", source=source, **params)

    def collection_done(self, source: str, count: int, duration_ms: float):
        self.info("collection.completed", source=source, items=count, duration_ms=round(duration_ms, 1))

    def collection_error(self, source: str, error: str):
        self.error("collection.failed", source=source, error=error[:200])

    def analysis_done(self, source_id: str, platform: str, viral_score: float, tier: str, duration_ms: float):
        self.info("analysis.completed", source_id=source_id, platform=platform,
                  viral_score=round(viral_score, 4), tier=tier, duration_ms=round(duration_ms, 1))

    def breakout_detected(self, topic_id: str, score: float, platform: str):
        self.info("breakout.detected", topic_id=topic_id, viral_score=round(score, 4), platform=platform)

    def rate_limited(self, client_ip: str, endpoint: str, limit: str):
        self.warn("rate_limit.hit", client_ip=client_ip, endpoint=endpoint, limit=limit)

    def cache_hit(self, key: str):
        self.debug("cache.hit", key=key)

    def cache_miss(self, key: str):
        self.debug("cache.miss", key=key)

    def circuit_open(self, source: str):
        self.error("circuit.open", source=source)

    def circuit_close(self, source: str):
        self.info("circuit.closed", source=source)


vis_log = VISLogger()
