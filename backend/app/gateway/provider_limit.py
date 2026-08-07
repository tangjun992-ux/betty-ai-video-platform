"""Gateway provider rate limits + in-flight backpressure."""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)

PREFIX = "gw-plimit"


@dataclass
class ProviderLimitResult:
    allowed: bool
    reason: str = ""


class GatewayProviderLimit:
    """Per-provider RPM cap and max concurrent in-flight requests."""

    def __init__(self):
        self._redis = None
        self._memory_rpm: dict[str, list[float]] = {}
        self._memory_inflight: dict[str, int] = {}
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

    def _rpm_cap(self, provider: str) -> int:
        key = f"GATEWAY_PROVIDER_RPM_{provider.upper()}"
        specific = int(getattr(settings, key, 0) or 0)
        if specific > 0:
            return specific
        return int(getattr(settings, "GATEWAY_PROVIDER_RPM", 0) or 0)

    def _max_inflight(self) -> int:
        return int(getattr(settings, "GATEWAY_PROVIDER_MAX_INFLIGHT", 0) or 0)

    def check_rpm(self, provider: str) -> ProviderLimitResult:
        cap = self._rpm_cap(provider)
        if cap <= 0:
            return ProviderLimitResult(True)
        client = self._client()
        if client:
            try:
                import time
                now = time.time()
                key = f"{PREFIX}:rpm:{provider}"
                pipe = client.pipeline()
                pipe.zremrangebyscore(key, 0, now - 60)
                pipe.zcard(key)
                count = pipe.execute()[1]
                if count >= cap:
                    return ProviderLimitResult(False, f"Provider {provider} RPM 已达上限 ({cap}/min)")
                client.zadd(key, {str(now): now})
                client.expire(key, 70)
                return ProviderLimitResult(True)
            except Exception:
                pass
        import time
        now = time.time()
        with self._lock:
            hits = [t for t in self._memory_rpm.get(provider, []) if t >= now - 60]
            if len(hits) >= cap:
                return ProviderLimitResult(False, f"Provider {provider} RPM 已达上限 ({cap}/min)")
            hits.append(now)
            self._memory_rpm[provider] = hits
        return ProviderLimitResult(True)

    def acquire_inflight(self, provider: str) -> ProviderLimitResult:
        cap = self._max_inflight()
        if cap <= 0:
            return ProviderLimitResult(True)
        client = self._client()
        if client:
            try:
                key = f"{PREFIX}:inflight:{provider}"
                n = client.incr(key)
                client.expire(key, 900)
                if n > cap:
                    client.decr(key)
                    return ProviderLimitResult(
                        False, f"Provider {provider} 并发已满 ({cap})",
                    )
                return ProviderLimitResult(True)
            except Exception:
                pass
        with self._lock:
            cur = self._memory_inflight.get(provider, 0)
            if cur >= cap:
                return ProviderLimitResult(False, f"Provider {provider} 并发已满 ({cap})")
            self._memory_inflight[provider] = cur + 1
        return ProviderLimitResult(True)

    def release_inflight(self, provider: str) -> None:
        if self._max_inflight() <= 0:
            return
        client = self._client()
        if client:
            try:
                key = f"{PREFIX}:inflight:{provider}"
                cur = client.decr(key)
                if cur is not None and int(cur) < 0:
                    client.set(key, 0, ex=900)
                return
            except Exception:
                pass
        with self._lock:
            cur = self._memory_inflight.get(provider, 0)
            self._memory_inflight[provider] = max(0, cur - 1)

    def check_and_acquire(self, provider: str) -> ProviderLimitResult:
        rpm = self.check_rpm(provider)
        if not rpm.allowed:
            return rpm
        return self.acquire_inflight(provider)

    def inflight_snapshot(self) -> dict[str, int]:
        """Current in-flight request counts per provider (Redis + memory fallback)."""
        counts: dict[str, int] = {}
        client = self._client()
        if client:
            try:
                for key in client.scan_iter(f"{PREFIX}:inflight:*", count=100):
                    provider = key.rsplit(":", 1)[-1]
                    counts[provider] = max(0, int(client.get(key) or 0))
            except Exception:
                pass
        with self._lock:
            for provider, n in self._memory_inflight.items():
                counts[provider] = counts.get(provider, 0) + max(0, n)
        return counts

    def limits_status(self) -> dict:
        cap = self._max_inflight()
        rpm_default = int(getattr(settings, "GATEWAY_PROVIDER_RPM", 0) or 0)
        per_provider_rpm = {}
        for name in ("kie", "replicate", "seedance", "kling"):
            specific = int(getattr(settings, f"GATEWAY_PROVIDER_RPM_{name.upper()}", 0) or 0)
            if specific > 0:
                per_provider_rpm[name] = specific
        return {
            "max_inflight": cap,
            "rpm_default": rpm_default,
            "rpm_per_provider": per_provider_rpm,
            "inflight": self.inflight_snapshot(),
        }


gateway_provider_limit = GatewayProviderLimit()
