"""Gateway execution idempotency — prevent duplicate paid provider calls."""
from __future__ import annotations

import json
import logging
import threading
from typing import Any, Optional

from app.config import settings
from app.gateway.types import Capability, GatewayExecutionResult

logger = logging.getLogger(__name__)

PREFIX = "gw-idem"
_LOCK_TTL = 900


class GatewayIdempotency:
    def __init__(self):
        self._redis = None
        self._memory_locks: set[str] = set()
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

    def _lock_key(self, trace_id: str) -> str:
        return f"{PREFIX}:lock:{trace_id}"

    def _done_key(self, trace_id: str) -> str:
        return f"{PREFIX}:done:{trace_id}"

    def acquire_lock(self, trace_id: str) -> bool:
        if not trace_id or len(trace_id) < 8:
            return True
        client = self._client()
        if client:
            try:
                if client.get(self._done_key(trace_id)):
                    return False
                return bool(client.set(self._lock_key(trace_id), "1", nx=True, ex=_LOCK_TTL))
            except Exception:
                pass
        with self._lock:
            if trace_id in self._memory_locks:
                return False
            self._memory_locks.add(trace_id)
            return True

    def release_lock(self, trace_id: str) -> None:
        if not trace_id:
            return
        client = self._client()
        if client:
            try:
                client.delete(self._lock_key(trace_id))
            except Exception:
                pass
        with self._lock:
            self._memory_locks.discard(trace_id)

    def mark_done(self, trace_id: str) -> None:
        if not trace_id:
            return
        client = self._client()
        if client:
            try:
                client.set(self._done_key(trace_id), "1", ex=86400 * 7)
                client.delete(self._lock_key(trace_id))
            except Exception:
                pass
        with self._lock:
            self._memory_locks.discard(trace_id)

    def load_completed(self, trace_id: str) -> Optional[GatewayExecutionResult]:
        """If task already completed in DB, reconstruct result without re-calling provider."""
        if not trace_id or len(trace_id) < 8:
            return None
        try:
            from app.tasks.task_db import get_task_gateway_context
            ctx = get_task_gateway_context(trace_id)
        except Exception:
            return None
        if ctx.get("status") != "completed":
            return None
        params = ctx.get("parameters") or {}
        gateway_meta = params.get("gateway") if isinstance(params.get("gateway"), dict) else None
        if not gateway_meta:
            return None

        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import Session
        from app.tasks.task_db import get_db_url_sync

        engine = create_engine(get_db_url_sync())
        with Session(engine) as session:
            row = session.execute(
                text("SELECT results, selected_model FROM tasks WHERE task_id = :tid"),
                {"tid": trace_id},
            ).mappings().first()
        if not row:
            return None
        results_raw = row.get("results")
        if isinstance(results_raw, str) and results_raw:
            try:
                results = json.loads(results_raw)
            except Exception:
                results = []
        elif isinstance(results_raw, list):
            results = results_raw
        else:
            results = []
        if not results:
            return None

        first = results[0] if results else {}
        from app.adapters.base import GenerationResult
        gen = GenerationResult(
            media_url=first.get("url") or first.get("media_url") or "",
            media_type=first.get("type") or "image",
            model=first.get("model") or row.get("selected_model") or "",
            cost=float(first.get("cost") or 0),
            meta=first if isinstance(first, dict) else {},
        )
        cap_raw = gateway_meta.get("capability") or Capability.IMAGE_GENERATE.value
        try:
            cap = Capability(cap_raw)
        except ValueError:
            cap = Capability.IMAGE_GENERATE

        return GatewayExecutionResult(
            result=gen,
            capability=cap,
            model_requested=gateway_meta.get("model_requested") or "",
            model_used=gateway_meta.get("model_used") or gen.model,
            provider_used=gateway_meta.get("provider_used") or "",
            remote_model_used=gateway_meta.get("remote_model_used") or "",
            fallback_used=bool(gateway_meta.get("fallback_used")),
            attempts=gateway_meta.get("attempts") or [],
            latency_ms=int(gateway_meta.get("latency_ms") or 0),
            cost=float(gen.cost or 0),
            trace_id=trace_id,
        )


gateway_idempotency = GatewayIdempotency()
