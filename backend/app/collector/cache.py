"""
VIS Cache Layer — Redis-backed caching for read-heavy endpoints.
Reduces DB load by 90%+ for trends/signals/dashboard queries.
"""
from __future__ import annotations

import json
import logging
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

DEFAULT_TTL = 300  # 5 minutes
SHORT_TTL = 60     # 1 minute
LONG_TTL = 1800    # 30 minutes


class VISCache:
    """Redis cache for VIS data with per-endpoint TTL configuration."""

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._enabled = redis_client is not None
        self._memory_fallback: dict[str, tuple[Any, float]] = {}
        import time
        self._time = time

    def get(self, key: str) -> Optional[Any]:
        """Get cached value by key. Returns None on miss or error."""
        if self._redis:
            return self._redis_get(key)
        return self._memory_get(key)

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """Set cache value with TTL in seconds."""
        if self._redis:
            return self._redis_set(key, value, ttl)
        return self._memory_set(key, value, ttl)

    def delete(self, key: str):
        """Delete a cache key."""
        if self._redis:
            try:
                self._redis.delete(key)
            except Exception:
                pass
        self._memory_fallback.pop(key, None)

    def invalidate_pattern(self, pattern: str):
        """Delete all keys matching a pattern."""
        if self._redis:
            try:
                keys = self._redis.keys(pattern)
                if keys:
                    self._redis.delete(*keys)
            except Exception:
                pass
        # Memory fallback: simpler prefix match
        to_delete = [k for k in self._memory_fallback if k.startswith(pattern.replace("*", ""))]
        for k in to_delete:
            self._memory_fallback.pop(k, None)

    def cached(self, ttl: int = DEFAULT_TTL, key_prefix: str = "vis:cache"):
        """Decorator for caching async function results.

        Usage:
            @cache.cached(ttl=300, key_prefix="trends")
            async def get_trends(...) -> list:
                ...
        """
        def decorator(fn: Callable):
            @wraps(fn)
            async def wrapper(*args, **kwargs):
                cache_key = self._build_key(key_prefix, args, kwargs)

                # Try cache
                cached = self.get(cache_key)
                if cached is not None:
                    return cached

                # Compute fresh
                result = await fn(*args, **kwargs)

                # Store in cache
                self.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator

    def _build_key(self, prefix: str, args: tuple, kwargs: dict) -> str:
        """Build a deterministic cache key from function args."""
        key_parts = [prefix]
        # Skip 'db', 'request', '_rate' params
        skip = {"db", "request", "_rate", "self", "cls"}
        for k, v in sorted(kwargs.items()):
            if k in skip:
                continue
            if v is not None:
                key_parts.append(f"{k}={v}")
        return ":".join(key_parts)

    def _redis_get(self, key: str) -> Optional[Any]:
        try:
            data = self._redis.get(f"vis:cache:{key}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning("[cache] Redis get failed: %s", e)
            return None

    def _redis_set(self, key: str, value: Any, ttl: int) -> bool:
        try:
            self._redis.set(f"vis:cache:{key}", json.dumps(value, default=str), ex=ttl)
            return True
        except Exception as e:
            logger.warning("[cache] Redis set failed: %s", e)
            return False

    def _memory_get(self, key: str) -> Optional[Any]:
        entry = self._memory_fallback.get(key)
        if entry:
            value, expires_at = entry
            if self._time.monotonic() < expires_at:
                return value
            del self._memory_fallback[key]
        return None

    def _memory_set(self, key: str, value: Any, ttl: int) -> bool:
        self._memory_fallback[key] = (value, self._time.monotonic() + ttl)
        # Limit memory cache size
        if len(self._memory_fallback) > 1000:
            oldest = min(self._memory_fallback, key=lambda k: self._memory_fallback[k][1])
            del self._memory_fallback[oldest]
        return True


# Try to init with Redis
_redis = None
try:
    import redis
    _redis = redis.Redis(host="localhost", port=6379, db=4, decode_responses=True, socket_timeout=2)
    _redis.ping()
    logger.info("[cache] Redis connected on db=4")
except Exception:
    logger.info("[cache] Redis unavailable — using memory fallback")

vis_cache = VISCache(_redis)
