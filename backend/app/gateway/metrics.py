"""Gateway request metrics — Redis counters for ops dashboards."""
from __future__ import annotations

import logging
import threading

from app.config import settings

logger = logging.getLogger(__name__)

PREFIX = "gw-metrics"


class GatewayMetrics:
    def __init__(self):
        self._redis = None
        self._memory: dict[str, int] = {}
        self._lock = threading.Lock()

    def _client(self):
        if self._redis is None:
            try:
                import redis
                self._redis = redis.Redis.from_url(
                    settings.REDIS_URL, decode_responses=True, socket_timeout=1,
                )
            except Exception:
                self._redis = False
        return self._redis if self._redis is not False else None

    def _incr(self, key: str) -> None:
        client = self._client()
        if client:
            try:
                client.incr(key)
                client.expire(key, 86400 * 7)
                return
            except Exception:
                pass
        with self._lock:
            self._memory[key] = self._memory.get(key, 0) + 1

    def record_request(
        self,
        *,
        provider: str,
        capability: str,
        success: bool,
        fallback: bool = False,
    ) -> None:
        status = "ok" if success else "fail"
        self._incr(f"{PREFIX}:req:{capability}:{provider}:{status}")
        if fallback:
            self._incr(f"{PREFIX}:fallback:{capability}:{provider}")

    def snapshot(self) -> dict:
        client = self._client()
        counters: dict[str, int] = {}
        if client:
            try:
                for key in client.scan_iter(f"{PREFIX}:*", count=200):
                    counters[key.replace(f"{PREFIX}:", "")] = int(client.get(key) or 0)
            except Exception:
                pass
        with self._lock:
            for k, v in self._memory.items():
                counters[k] = counters.get(k, 0) + v
        return {"counters": counters}


gateway_metrics = GatewayMetrics()
