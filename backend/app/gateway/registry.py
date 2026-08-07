"""Redis-backed gateway runtime registry — overrides, disable list, kill switch."""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

PREFIX = "gw-registry"
VERSION_KEY = f"{PREFIX}:version"


class GatewayRegistry:
    """Hot overrides without redeploy — admin API writes, router reads."""

    def __init__(self):
        self._redis = None
        self._memory_disabled: set[str] = set()
        self._memory_kill = False
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

    def _disabled_key(self, provider: str, remote_model: str) -> str:
        return f"{provider}:{remote_model}"

    def is_disabled(self, provider: str, remote_model: str) -> bool:
        key = self._disabled_key(provider, remote_model)
        client = self._client()
        if client:
            try:
                if client.sismember(f"{PREFIX}:disabled", key):
                    return True
            except Exception:
                pass
        with self._lock:
            return key in self._memory_disabled

    def disable_provider(self, provider: str, remote_model: str, *, reason: str = "") -> None:
        key = self._disabled_key(provider, remote_model)
        client = self._client()
        if client:
            try:
                client.sadd(f"{PREFIX}:disabled", key)
                client.hset(f"{PREFIX}:disabled_reasons", key, reason[:500])
                client.incr(VERSION_KEY)
            except Exception:
                pass
        with self._lock:
            self._memory_disabled.add(key)
        logger.warning("[gateway/registry] disabled %s (%s)", key, reason or "admin")

    def enable_provider(self, provider: str, remote_model: str) -> None:
        key = self._disabled_key(provider, remote_model)
        client = self._client()
        if client:
            try:
                client.srem(f"{PREFIX}:disabled", key)
                client.hdel(f"{PREFIX}:disabled_reasons", key)
                client.incr(VERSION_KEY)
            except Exception:
                pass
        with self._lock:
            self._memory_disabled.discard(key)

    def list_disabled(self) -> list[dict[str, str]]:
        client = self._client()
        keys: set[str] = set()
        reasons: dict[str, str] = {}
        if client:
            try:
                keys = set(client.smembers(f"{PREFIX}:disabled") or [])
                reasons = client.hgetall(f"{PREFIX}:disabled_reasons") or {}
            except Exception:
                pass
        with self._lock:
            keys |= self._memory_disabled
        out = []
        for k in sorted(keys):
            provider, _, remote = k.partition(":")
            out.append({
                "key": k,
                "provider": provider,
                "remote_model": remote,
                "reason": reasons.get(k, ""),
            })
        return out

    def kill_switch_active(self) -> bool:
        client = self._client()
        if client:
            try:
                return bool(client.get(f"{PREFIX}:kill_switch"))
            except Exception:
                pass
        with self._lock:
            return self._memory_kill

    def set_kill_switch(self, active: bool) -> None:
        client = self._client()
        if client:
            try:
                if active:
                    client.set(f"{PREFIX}:kill_switch", "1")
                else:
                    client.delete(f"{PREFIX}:kill_switch")
                client.incr(VERSION_KEY)
            except Exception:
                pass
        with self._lock:
            self._memory_kill = active
        logger.warning("[gateway/registry] kill_switch=%s", active)

    def version(self) -> int:
        client = self._client()
        if client:
            try:
                return int(client.get(VERSION_KEY) or 0)
            except Exception:
                pass
        return 0

    def snapshot(self) -> dict[str, Any]:
        return {
            "version": self.version(),
            "kill_switch": self.kill_switch_active(),
            "disabled": self.list_disabled(),
        }


gateway_registry = GatewayRegistry()
