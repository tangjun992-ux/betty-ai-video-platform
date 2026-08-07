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


def _persist_gateway_meta(trace_id: str, result: GatewayExecutionResult) -> None:
    """Write gateway routing metadata into task.parameters for webhooks/ops."""
    if not trace_id or len(trace_id) < 8:
        return
    try:
        from app.tasks.task_db import update_task_parameters_gateway_meta
        update_task_parameters_gateway_meta(trace_id, result.to_meta())
    except Exception as e:
        logger.debug("[gateway] meta persist skipped: %s", e)


async def execute_route(
    capability: Capability,
    model: str,
    *,
    trace_id: str = "",
    allow_fallback: bool = True,
    user_id: int | None = None,
    team_id: str | None = None,
    estimated_cost: float = 0.0,
    **kwargs: Any,
) -> GatewayExecutionResult:
    """
    Execute a configured provider chain for capability + Betty model SKU.

    Raises RuntimeError when all hops fail or no route/targets exist.
    """
    from app.gateway.budget import gateway_budget
    from app.gateway.idempotency import gateway_idempotency

    if trace_id:
        cached = gateway_idempotency.load_completed(trace_id)
        if cached:
            logger.info("[gateway] idempotent skip — task %s already completed", trace_id[:8])
            return cached
        if not gateway_idempotency.acquire_lock(trace_id):
            raise RuntimeError(
                f"Gateway execution already in progress for task {trace_id[:8]}"
            )

    try:
        budget = gateway_budget.check(
            user_id=user_id, team_id=team_id, estimated_cost=estimated_cost,
        )
        if not budget.allowed:
            raise RuntimeError(budget.reason)

        route = resolve_route(capability, model)
        if not route:
            raise RuntimeError(f"No gateway route for {capability.value}/{model}")

        result = await _execute_chain(
            route, model, trace_id=trace_id, allow_fallback=allow_fallback, **kwargs,
        )
        gateway_budget.record(result.cost, user_id=user_id, team_id=team_id)
        _persist_gateway_meta(trace_id, result)
        if trace_id:
            gateway_idempotency.mark_done(trace_id)
        return result
    except Exception:
        if trace_id:
            gateway_idempotency.release_lock(trace_id)
        raise


async def _execute_chain(
    route: RouteDefinition,
    model_requested: str,
    *,
    trace_id: str = "",
    allow_fallback: bool = True,
    **kwargs: Any,
) -> GatewayExecutionResult:
    # Explicit remote SKU override (director/lipsync pass kling/… or infinitalk/…)
    remote_override = kwargs.pop("remote_model_override", None)
    if remote_override:
        backend = get_backend("kie")
        if not backend or not backend.is_configured():
            raise RuntimeError("KIE_API_KEY not configured for remote_model_override")
        hop_started = time.monotonic()
        started = time.monotonic()
        try:
            result = await backend.execute(
                route.capability,
                remote_override,
                trace_id=trace_id,
                **kwargs,
            )
            provider_health.record_success("kie", remote_override)
            cost = float(getattr(result, "cost", 0) or 0)
            return GatewayExecutionResult(
                result=result,
                capability=route.capability,
                model_requested=model_requested,
                model_used=model_requested,
                provider_used="kie",
                remote_model_used=remote_override,
                fallback_used=False,
                attempts=[{"provider": "kie", "remote_model": remote_override, "success": True,
                           "latency_ms": int((time.monotonic() - hop_started) * 1000)}],
                latency_ms=int((time.monotonic() - started) * 1000),
                cost=cost,
                trace_id=trace_id,
            )
        except Exception as e:
            provider_health.record_failure("kie", remote_override, str(e))
            raise

    targets = select_targets(route, allow_fallback=allow_fallback, trace_id=trace_id)
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

        from app.gateway.provider_limit import gateway_provider_limit
        limit = gateway_provider_limit.check_and_acquire(target.provider)
        if not limit.allowed:
            attempts.append({
                "provider": target.provider,
                "remote_model": target.remote_model,
                "fallback_only": target.fallback_only,
                "success": False,
                "error": limit.reason[:300],
                "retryable": True,
                "rate_limited": True,
            })
            logger.warning("[gateway] provider limit %s: %s", target.provider, limit.reason)
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

            from app.gateway.metrics import gateway_metrics
            gateway_metrics.record_request(
                provider=target.provider,
                capability=route.capability.value,
                success=True,
                fallback=used_fallback and target.fallback_only,
            )

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
            from app.gateway.metrics import gateway_metrics
            gateway_metrics.record_request(
                provider=target.provider,
                capability=route.capability.value,
                success=False,
            )
            if not is_retryable_error(err):
                break
            continue
        finally:
            gateway_provider_limit.release_inflight(target.provider)

    raise RuntimeError(
        last_error or f"All gateway hops failed for {route.capability.value}/{model_requested}"
    )
