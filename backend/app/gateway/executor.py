"""Gateway executor — chain execution with retry/fallback semantics."""
from __future__ import annotations

import logging
import time
from typing import Any

from app.fallback_handler import is_retryable_error
from app.gateway.health import provider_health
from app.gateway.providers import get_backend
from app.gateway.router import resolve_route, select_targets
from app.gateway.types import Capability, GatewayExecutionResult, RouteDefinition

logger = logging.getLogger(__name__)


async def execute_route(
    capability: Capability,
    model: str,
    *,
    trace_id: str = "",
    allow_fallback: bool = True,
    **kwargs: Any,
) -> GatewayExecutionResult:
    """
    Execute a configured provider chain for capability + Betty model SKU.

    Raises RuntimeError when all hops fail or no route/targets exist.
    """
    route = resolve_route(capability, model)
    if not route:
        raise RuntimeError(f"No gateway route for {capability.value}/{model}")

    return await _execute_chain(
        route, model, trace_id=trace_id, allow_fallback=allow_fallback, **kwargs,
    )


async def _execute_chain(
    route: RouteDefinition,
    model_requested: str,
    *,
    trace_id: str = "",
    allow_fallback: bool = True,
    **kwargs: Any,
) -> GatewayExecutionResult:
    targets = select_targets(route, allow_fallback=allow_fallback)
    if not targets:
        raise RuntimeError(
            f"No available provider targets for {route.capability.value}/{model_requested}"
        )

    attempts: list[dict] = []
    started = time.monotonic()
    last_error = ""
    used_fallback = False

    for target in targets:
        if target.fallback_only:
            used_fallback = True
        backend = get_backend(target.provider)
        if not backend:
            continue

        hop_started = time.monotonic()
        try:
            result = await backend.execute(
                route.capability,
                target.remote_model,
                timeout_s=target.timeout_s,
                trace_id=trace_id,
                **kwargs,
            )
            latency = int((time.monotonic() - hop_started) * 1000)
            provider_health.record_success(target.provider, target.remote_model)

            cost = 0.0
            if hasattr(result, "cost"):
                cost = float(getattr(result, "cost", 0) or 0)
            elif isinstance(result, list) and result:
                cost = sum(float(getattr(r, "cost", 0) or 0) for r in result)

            attempts.append({
                "provider": target.provider,
                "remote_model": target.remote_model,
                "fallback_only": target.fallback_only,
                "success": True,
                "latency_ms": latency,
            })

            return GatewayExecutionResult(
                result=result,
                capability=route.capability,
                model_requested=model_requested,
                model_used=model_requested,
                provider_used=target.provider,
                remote_model_used=target.remote_model,
                fallback_used=used_fallback and target.fallback_only,
                attempts=attempts,
                latency_ms=int((time.monotonic() - started) * 1000),
                cost=cost,
                trace_id=trace_id,
            )
        except Exception as e:
            err = str(e)
            last_error = err
            latency = int((time.monotonic() - hop_started) * 1000)
            provider_health.record_failure(target.provider, target.remote_model, err)
            attempts.append({
                "provider": target.provider,
                "remote_model": target.remote_model,
                "fallback_only": target.fallback_only,
                "success": False,
                "error": err[:300],
                "latency_ms": latency,
                "retryable": is_retryable_error(err),
            })
            logger.warning(
                "[gateway] hop failed provider=%s model=%s err=%s",
                target.provider, target.remote_model, err[:200],
            )
            if not is_retryable_error(err):
                break
            continue

    raise RuntimeError(
        last_error or f"All gateway hops failed for {route.capability.value}/{model_requested}"
    )
