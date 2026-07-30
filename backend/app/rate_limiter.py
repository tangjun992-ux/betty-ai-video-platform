"""
Rate limiter — sliding window rate limiting for API endpoints.

Primary backend is Redis (shared across workers). If Redis is unavailable the
limiter falls back to an in-process sliding window so limits STILL apply (fail
-closed to protection rather than silently disabling all limits).
"""
import hashlib
import threading
import time
import redis
from collections import defaultdict, deque
from typing import Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

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
            # Prefer REDIS_URL (same as WS / Celery) so multi-replica deploys share limits.
            url = (settings.REDIS_URL or "redis://localhost:6379/0").strip()
            # Use db=3 for rate-limit keys unless URL already specifies a non-default path.
            try:
                self._client = redis.Redis.from_url(
                    url,
                    db=3,
                    decode_responses=True,
                    socket_timeout=2,
                )
            except TypeError:
                # redis-py versions that reject db override when URL has path
                self._client = redis.Redis.from_url(
                    url,
                    decode_responses=True,
                    socket_timeout=2,
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


def rate_limit_subject(request: Request) -> str:
    """Stable throttling identity.

    Prefer authenticated/guest identity over raw IP so (a) users behind a shared
    NAT/CDN egress IP aren't collectively throttled, and (b) a single abuser
    can't trivially reset their budget by rotating IPs. Tokens are hashed (not
    truncated) to avoid collisions between different tokens sharing a prefix.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            return "t:" + hashlib.sha256(token.encode()).hexdigest()[:20]
    gid = request.headers.get("x-guest-id") or request.cookies.get("betty_guest_id")
    if gid:
        return "g:" + gid.strip()[:40]
    return "ip:" + _client_ip(request)


def rate_limit(bucket: str, rpm: int = 60, rph: int = 500):
    """FastAPI dependency factory — throttle a route by stable subject
    (auth/guest identity, falling back to IP). Raises 429 with Retry-After."""
    async def _dep(request: Request):
        subject = rate_limit_subject(request)
        res = rate_limiter.is_rate_limited(f"{bucket}:{subject}", rpm, rph)
        if not res.get("allowed", True):
            raise HTTPException(
                status_code=429,
                detail="请求过于频繁，请稍后再试",
                headers={"Retry-After": str(res.get("retry_after", 60))},
            )
    return _dep


# Paths exempt from the global baseline limiter (static media, health/metrics,
# websockets, docs). Prefix match against request.url.path.
_GLOBAL_EXEMPT_PREFIXES = (
    "/api/v1/media",
    "/health",
    "/metrics",
    "/api/v1/ws",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
)


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Baseline per-subject throttle across ALL API routes.

    This is a coarse safety net (generous limit) so every endpoint has abuse
    protection; hot routes still layer stricter `rate_limit(...)` deps on top.
    Only applies to `/api/v1/*`; static media, health, metrics and websockets
    are exempt so dashboards and asset loading are never throttled.
    """

    async def dispatch(self, request: Request, call_next):
        if not getattr(settings, "RATE_LIMIT_ENABLED", True) or request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if not path.startswith("/api/v1") or any(path.startswith(p) for p in _GLOBAL_EXEMPT_PREFIXES):
            return await call_next(request)
        subject = rate_limit_subject(request)
        rpm = getattr(settings, "RATE_LIMIT_GLOBAL_RPM", 180)
        rph = getattr(settings, "RATE_LIMIT_GLOBAL_RPH", 3000)
        res = rate_limiter.is_rate_limited(f"global:{subject}", rpm, rph)
        if not res.get("allowed", True):
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试"},
                headers={"Retry-After": str(res.get("retry_after", 60))},
            )
        return await call_next(request)
