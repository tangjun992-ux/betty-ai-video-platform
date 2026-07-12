"""
Rate limiter — sliding window rate limiting for API endpoints.

Primary backend is Redis (shared across workers). If Redis is unavailable the
limiter falls back to an in-process sliding window so limits STILL apply (fail
-closed to protection rather than silently disabling all limits).
"""
import threading
import time
import redis
from collections import defaultdict, deque
from typing import Optional
from functools import wraps
from fastapi import Request, HTTPException, Depends

from app.config import settings

# Default limits
DEFAULT_LIMITS = {
    "submit_generation": {"rpm": 10, "rph": 50},   # 10/min, 50/hour
    "upload": {"rpm": 5, "rph": 30},
    "default": {"rpm": 60, "rph": 500},
}


class _MemoryWindow:
    """Per-process sliding-window fallback used when Redis is unavailable."""

    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, rpm: int, rph: int) -> dict:
        now = time.time()
        with self._lock:
            dq = self._hits[key]
            while dq and dq[0] < now - 3600:
                dq.popleft()
            minute = sum(1 for t in dq if t >= now - 60)
            if minute >= rpm:
                return {"allowed": False, "retry_after": 60, "limit_key": "rpm"}
            if len(dq) >= rph:
                return {"allowed": False, "retry_after": 3600, "limit_key": "rph"}
            dq.append(now)
            return {"allowed": True}


_memory = _MemoryWindow()


class RateLimiter:
    """Redis-based sliding window rate limiter."""

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis(
                host="localhost", port=6379, db=3,
                decode_responses=True, socket_timeout=2,
            )
        return self._client

    def is_rate_limited(
        self,
        key: str,
        requests_per_minute: int = 60,
        requests_per_hour: int = 500,
    ) -> dict:
        """
        Check if the key has exceeded rate limits.
        Returns {"allowed": True/False, "retry_after": seconds}
        """
        try:
            now = time.time()
            pipe = self.client.pipeline()

            # Sliding window: 1-minute bucket
            minute_key = f"ratelimit:{key}:m"
            hour_key = f"ratelimit:{key}:h"

            # Clean old entries
            pipe.zremrangebyscore(minute_key, 0, now - 60)
            pipe.zremrangebyscore(hour_key, 0, now - 3600)

            # Count
            pipe.zcard(minute_key)
            pipe.zcard(hour_key)

            results = pipe.execute()
            minute_count = results[2]
            hour_count = results[3]

            if minute_count >= requests_per_minute:
                return {"allowed": False, "retry_after": 60, "limit_key": "rpm"}
            if hour_count >= requests_per_hour:
                return {"allowed": False, "retry_after": 3600, "limit_key": "rph"}

            # Record this request
            self.client.zadd(minute_key, {str(now): now})
            self.client.zadd(hour_key, {str(now): now})
            self.client.expire(minute_key, 70)
            self.client.expire(hour_key, 3700)

            return {"allowed": True}

        except Exception:
            # Redis unavailable → fall back to in-process limiting (still enforced)
            return _memory.check(key, requests_per_minute, requests_per_hour)


rate_limiter = RateLimiter()


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(bucket: str, rpm: int = 60, rph: int = 500):
    """FastAPI dependency factory — throttle a route by client IP (+ bearer sub
    when present). Raises 429 with Retry-After when exceeded."""
    async def _dep(request: Request):
        subject = _client_ip(request)
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            subject = "u:" + auth[7:][:24]  # coarse per-token bucket
        res = rate_limiter.is_rate_limited(f"{bucket}:{subject}", rpm, rph)
        if not res.get("allowed", True):
            raise HTTPException(
                status_code=429,
                detail="请求过于频繁，请稍后再试",
                headers={"Retry-After": str(res.get("retry_after", 60))},
            )
    return _dep
