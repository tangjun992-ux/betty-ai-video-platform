"""Rate limiter tests — in-process window and FastAPI dependency behaviour."""
import asyncio
import os
import sys
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rate_limiter import (
    DEFAULT_LIMITS,
    RateLimiter,
    _MemoryWindow,
    _client_ip,
    rate_limit,
)


def _request(ip="1.2.3.4", headers=None):
    return SimpleNamespace(headers=headers or {}, client=SimpleNamespace(host=ip))


class _UnreachableRedis:
    def pipeline(self):
        raise ConnectionError("redis down")


def offline_limiter() -> RateLimiter:
    """A limiter whose Redis backend is unreachable → in-process fallback."""
    limiter = RateLimiter()
    limiter._client = _UnreachableRedis()
    return limiter


def test_memory_window_allows_within_limits():
    w = _MemoryWindow()
    for _ in range(3):
        assert w.check("k", rpm=3, rph=10)["allowed"]


def test_memory_window_blocks_on_rpm():
    w = _MemoryWindow()
    for _ in range(2):
        w.check("k", rpm=2, rph=10)
    res = w.check("k", rpm=2, rph=10)
    assert res == {"allowed": False, "retry_after": 60, "limit_key": "rpm"}


def test_memory_window_blocks_on_rph():
    w = _MemoryWindow()
    for _ in range(2):
        w.check("k", rpm=100, rph=2)
    res = w.check("k", rpm=100, rph=2)
    assert res == {"allowed": False, "retry_after": 3600, "limit_key": "rph"}


def test_memory_window_keys_are_independent():
    w = _MemoryWindow()
    assert w.check("a", rpm=1, rph=5)["allowed"]
    assert w.check("b", rpm=1, rph=5)["allowed"]
    assert not w.check("a", rpm=1, rph=5)["allowed"]


def test_memory_window_forgets_entries_older_than_an_hour(monkeypatch):
    w = _MemoryWindow()
    now = [1_000_000.0]
    monkeypatch.setattr("app.rate_limiter.time.time", lambda: now[0])
    assert w.check("k", rpm=1, rph=1)["allowed"]
    assert not w.check("k", rpm=1, rph=1)["allowed"]
    now[0] += 3601
    assert w.check("k", rpm=1, rph=1)["allowed"]


def test_limits_are_still_enforced_when_redis_is_down():
    limiter = offline_limiter()
    key = f"test:{uuid.uuid4().hex}"
    assert limiter.is_rate_limited(key, requests_per_minute=1, requests_per_hour=5)["allowed"]
    blocked = limiter.is_rate_limited(key, requests_per_minute=1, requests_per_hour=5)
    assert not blocked["allowed"] and blocked["limit_key"] == "rpm"


def test_client_ip_prefers_forwarded_header():
    assert _client_ip(_request(headers={"x-forwarded-for": "9.9.9.9, 10.0.0.1"})) == "9.9.9.9"
    assert _client_ip(_request(ip="8.8.8.8")) == "8.8.8.8"
    assert _client_ip(SimpleNamespace(headers={}, client=None)) == "unknown"


def test_dependency_allows_then_raises_429(monkeypatch):
    calls = []

    def fake_check(key, rpm, rph):
        calls.append((key, rpm, rph))
        return {"allowed": len(calls) == 1, "retry_after": 42}

    monkeypatch.setattr("app.rate_limiter.rate_limiter.is_rate_limited", fake_check)
    dep = rate_limit("upload", rpm=5, rph=30)

    asyncio.run(dep(_request(ip="7.7.7.7")))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(dep(_request(ip="7.7.7.7")))

    assert exc.value.status_code == 429
    assert exc.value.headers["Retry-After"] == "42"
    assert calls[0] == ("upload:7.7.7.7", 5, 30)


def test_dependency_buckets_per_bearer_token(monkeypatch):
    seen = []
    monkeypatch.setattr(
        "app.rate_limiter.rate_limiter.is_rate_limited",
        lambda key, rpm, rph: seen.append(key) or {"allowed": True},
    )
    dep = rate_limit("submit_generation")
    asyncio.run(dep(_request(headers={"authorization": "Bearer abc123"})))
    assert seen == ["submit_generation:u:abc123"]


def test_default_limits_are_ordered_by_cost():
    assert DEFAULT_LIMITS["submit_generation"]["rpm"] < DEFAULT_LIMITS["default"]["rpm"]
    for limits in DEFAULT_LIMITS.values():
        assert limits["rpm"] <= limits["rph"]
