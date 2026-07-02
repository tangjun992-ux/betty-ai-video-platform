"""
Rate limiter — sliding window rate limiting for API endpoints.
"""
import time
import redis
from typing import Optional
from functools import wraps
from fastapi import Request, HTTPException

from app.config import settings

# Default limits
DEFAULT_LIMITS = {
    "submit_generation": {"rpm": 10, "rph": 50},   # 10/min, 50/hour
    "upload": {"rpm": 5, "rph": 30},
    "default": {"rpm": 60, "rph": 500},
}


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

        except Exception as e:
            # If Redis fails, don't block
            return {"allowed": True, "error": str(e)}


rate_limiter = RateLimiter()
