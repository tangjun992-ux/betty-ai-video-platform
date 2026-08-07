"""Provider-level health tracking (extends model_health for gateway hops)."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from app.config import settings
from app.fallback_handler import is_retryable_error

PREFIX = "gw-health"
CIRCUIT_FAILURES = int(getattr(settings, "GATEWAY_CIRCUIT_FAILURES", 3))
CIRCUIT_TTL_SECONDS = int(getattr(settings, "GATEWAY_CIRCUIT_TTL_SECONDS", 300))


def provider_key(provider: str, remote_model: str) -> str:
    return f"{provider}:{remote_model}"


@dataclass
class ProviderHealthSnapshot:
    key: str
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    circuit_open: bool = False
    last_error: str = ""

    @property
    def available(self) -> bool:
        return not self.circuit_open


class ProviderHealthRegistry:
    """Lightweight in-process + optional Redis provider circuit breaker."""

    def __init__(self):
        self._memory: dict[str, dict] = {}
        self._circuits: dict[str, float] = {}
        self._lock = threading.Lock()
        self._redis = None

    def _client(self):
        if self._redis is None:
            try:
                import redis
                self._redis = redis.Redis.from_url(
                    settings.REDIS_URL, decode_responses=True, socket_timeout=1,
                )
            except Exception:
                self._redis = False  # sentinel: redis unavailable
        return self._redis if self._redis is not False else None

    def _circuit_key(self, key: str) -> str:
        return f"{PREFIX}:circuit:{key}"

    def is_available(self, provider: str, remote_model: str) -> bool:
        key = provider_key(provider, remote_model)
        client = self._client()
        if client:
            try:
                if client.exists(self._circuit_key(key)):
                    return False
            except Exception:
                pass
        with self._lock:
            expiry = self._circuits.get(key, 0)
            if expiry and expiry <= time.time():
                self._circuits.pop(key, None)
                expiry = 0
            return not bool(expiry)

    def record_success(self, provider: str, remote_model: str) -> None:
        key = provider_key(provider, remote_model)
        client = self._client()
        if client:
            try:
                client.delete(self._circuit_key(key))
            except Exception:
                pass
        with self._lock:
            self._circuits.pop(key, None)
            snap = self._memory.setdefault(key, {"successes": 0, "failures": 0, "consecutive_failures": 0})
            snap["successes"] = snap.get("successes", 0) + 1
            snap["consecutive_failures"] = 0

    def record_failure(self, provider: str, remote_model: str, error: str) -> None:
        if not is_retryable_error(error):
            return
        key = provider_key(provider, remote_model)
        with self._lock:
            snap = self._memory.setdefault(key, {"successes": 0, "failures": 0, "consecutive_failures": 0})
            snap["failures"] = snap.get("failures", 0) + 1
            snap["consecutive_failures"] = snap.get("consecutive_failures", 0) + 1
            snap["last_error"] = error[:500]
            if snap["consecutive_failures"] >= CIRCUIT_FAILURES:
                self._circuits[key] = time.time() + CIRCUIT_TTL_SECONDS
                client = self._client()
                if client:
                    try:
                        client.setex(self._circuit_key(key), CIRCUIT_TTL_SECONDS, "1")
                    except Exception:
                        pass

    def snapshot(self, provider: str, remote_model: str) -> ProviderHealthSnapshot:
        key = provider_key(provider, remote_model)
        with self._lock:
            raw = dict(self._memory.get(key, {}))
            expiry = self._circuits.get(key, 0)
            circuit_open = bool(expiry and expiry > time.time())
        return ProviderHealthSnapshot(
            key=key,
            successes=raw.get("successes", 0),
            failures=raw.get("failures", 0),
            consecutive_failures=raw.get("consecutive_failures", 0),
            circuit_open=circuit_open,
            last_error=raw.get("last_error", ""),
        )

    def all_snapshots(self) -> list[ProviderHealthSnapshot]:
        keys = set(self._memory.keys()) | set(self._circuits.keys())
        out = []
        for key in sorted(keys):
            if ":" not in key:
                continue
            provider, remote = key.split(":", 1)
            out.append(self.snapshot(provider, remote))
        return out


provider_health = ProviderHealthRegistry()
