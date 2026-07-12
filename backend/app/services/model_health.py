"""
Runtime model health, scoring, and circuit breaking.

Execution outcomes feed a Redis-backed health registry shared by all API and
worker replicas. If Redis is unavailable an in-process registry keeps the
protection active. Three consecutive retryable failures open a five-minute
circuit; a success closes it immediately.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass

from app.config import settings

PREFIX = "model-health"
CIRCUIT_FAILURES = 3
CIRCUIT_TTL_SECONDS = 300


@dataclass
class HealthSnapshot:
    model_id: str
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    latency_total_ms: int = 0
    last_error: str = ""
    circuit_open: bool = False

    @property
    def total(self) -> int:
        return self.successes + self.failures

    @property
    def success_rate(self) -> float:
        return self.successes / self.total if self.total else 1.0

    @property
    def avg_latency_ms(self) -> int:
        return round(self.latency_total_ms / self.successes) if self.successes else 0

    @property
    def score(self) -> float:
        if self.circuit_open:
            return 0.0
        latency_score = 1.0 if not self.avg_latency_ms else max(0.0, 1.0 - self.avg_latency_ms / 300_000)
        return round((self.success_rate * 0.85 + latency_score * 0.15) * 100, 1)

    def public_dict(self) -> dict:
        data = asdict(self)
        data.update(total=self.total, success_rate=round(self.success_rate, 4),
                    avg_latency_ms=self.avg_latency_ms, score=self.score)
        return data


class ModelHealthRegistry:
    def __init__(self):
        self._redis = None
        self._memory: dict[str, dict] = {}
        self._circuits: dict[str, float] = {}
        self._lock = threading.Lock()

    def _client(self):
        if self._redis is None:
            import redis
            self._redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=1)
        return self._redis

    def _stats_key(self, model_id: str) -> str:
        return f"{PREFIX}:stats:{model_id}"

    def _circuit_key(self, model_id: str) -> str:
        return f"{PREFIX}:circuit:{model_id}"

    def _memory_snapshot(self, model_id: str) -> HealthSnapshot:
        with self._lock:
            raw = dict(self._memory.get(model_id, {}))
            expiry = self._circuits.get(model_id, 0)
            if expiry and expiry <= time.time():
                self._circuits.pop(model_id, None)
                expiry = 0
            raw["circuit_open"] = bool(expiry)
        return HealthSnapshot(model_id=model_id, **raw)

    def snapshot(self, model_id: str) -> HealthSnapshot:
        try:
            client = self._client()
            raw = client.hgetall(self._stats_key(model_id))
            values = {
                "successes": int(raw.get("successes", 0)),
                "failures": int(raw.get("failures", 0)),
                "consecutive_failures": int(raw.get("consecutive_failures", 0)),
                "latency_total_ms": int(raw.get("latency_total_ms", 0)),
                "last_error": raw.get("last_error", ""),
                "circuit_open": bool(client.exists(self._circuit_key(model_id))),
            }
            return HealthSnapshot(model_id=model_id, **values)
        except Exception:
            return self._memory_snapshot(model_id)

    def is_circuit_open(self, model_id: str) -> bool:
        return self.snapshot(model_id).circuit_open

    def score(self, model_id: str) -> float:
        return self.snapshot(model_id).score

    def record_success(self, model_id: str, latency_ms: int = 0) -> HealthSnapshot:
        try:
            client = self._client()
            key = self._stats_key(model_id)
            pipe = client.pipeline()
            pipe.hincrby(key, "successes", 1)
            pipe.hincrby(key, "latency_total_ms", max(0, int(latency_ms)))
            pipe.hset(key, mapping={"consecutive_failures": 0, "last_error": ""})
            pipe.delete(self._circuit_key(model_id))
            pipe.expire(key, 30 * 24 * 3600)
            pipe.execute()
        except Exception:
            with self._lock:
                row = self._memory.setdefault(model_id, {})
                row["successes"] = row.get("successes", 0) + 1
                row["latency_total_ms"] = row.get("latency_total_ms", 0) + max(0, int(latency_ms))
                row["consecutive_failures"] = 0
                row["last_error"] = ""
                self._circuits.pop(model_id, None)
        return self.snapshot(model_id)

    def record_failure(self, model_id: str, error: str = "", retryable: bool = True) -> HealthSnapshot:
        if not retryable:
            return self.snapshot(model_id)
        opened = False
        try:
            client = self._client()
            key = self._stats_key(model_id)
            failures = client.hincrby(key, "failures", 1)
            consecutive = client.hincrby(key, "consecutive_failures", 1)
            client.hset(key, "last_error", (error or "")[:500])
            client.expire(key, 30 * 24 * 3600)
            if consecutive >= CIRCUIT_FAILURES:
                client.setex(self._circuit_key(model_id), CIRCUIT_TTL_SECONDS,
                             json.dumps({"opened_at": int(time.time()), "failures": failures}))
                opened = True
        except Exception:
            with self._lock:
                row = self._memory.setdefault(model_id, {})
                row["failures"] = row.get("failures", 0) + 1
                row["consecutive_failures"] = row.get("consecutive_failures", 0) + 1
                row["last_error"] = (error or "")[:500]
                if row["consecutive_failures"] >= CIRCUIT_FAILURES:
                    self._circuits[model_id] = time.time() + CIRCUIT_TTL_SECONDS
                    opened = True
        snap = self.snapshot(model_id)
        if opened:
            snap.circuit_open = True
        return snap

    def reset(self, model_id: str) -> None:
        try:
            client = self._client()
            client.delete(self._stats_key(model_id), self._circuit_key(model_id))
        except Exception:
            pass
        with self._lock:
            self._memory.pop(model_id, None)
            self._circuits.pop(model_id, None)


model_health = ModelHealthRegistry()


def validate_generation_results(results, media_type: str) -> tuple[bool, str]:
    """Minimal post-generation quality guard before persistence/fallback."""
    if not results:
        return False, "generation returned no results"
    rows = results if isinstance(results, list) else [results]
    for row in rows:
        data = row.to_dict() if hasattr(row, "to_dict") else row
        if not isinstance(data, dict):
            return False, "generation returned an invalid result"
        if data.get("error"):
            return False, str(data["error"])
        url = data.get("media_url") or data.get("url")
        if not isinstance(url, str) or not url.strip():
            return False, f"{media_type} result is missing media URL"
    return True, ""
