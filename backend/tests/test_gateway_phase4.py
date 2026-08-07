"""Phase 4 gateway hardening — budget wiring, tools routing, idempotency, audit."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.adapters.base import GenerationResult
from app.gateway.config import find_route, get_routes
from app.gateway.executor import execute_route
from app.gateway.idempotency import GatewayIdempotency, gateway_idempotency
from app.gateway.types import Capability
from app.metrics import GATEWAY_REQUESTS, record_gateway_request
from app.tasks.gateway_context import gateway_call_kwargs
from app.tasks.task_db import get_task_gateway_context


@pytest.fixture(autouse=True)
def reset_idempotency():
    gateway_idempotency._memory_locks.clear()
    yield
    gateway_idempotency._memory_locks.clear()


def test_tool_routes_exist():
    get_routes(reload=True)
    assert find_route(Capability.IMAGE_FACE_SWAP, "face-swap") is not None
    assert find_route(Capability.IMAGE_UPSCALE, "image-upscale") is not None
    assert find_route(Capability.IMAGE_REMOVE_BG, "remove-background") is not None
    assert find_route(Capability.IMAGE_EXTEND, "image-extend") is not None


def test_gateway_call_kwargs_from_task_db(monkeypatch):
    monkeypatch.setattr(
        "app.tasks.gateway_context.get_task_gateway_context",
        lambda tid: {
            "user_id": 42,
            "team_id": "team-abc",
            "estimated_cost": 8.0,
        },
    )
    kw = gateway_call_kwargs("task-1")
    assert kw["user_id"] == 42
    assert kw["team_id"] == "team-abc"
    assert kw["estimated_cost"] == 8.0
    assert kw["trace_id"] == "task-1"

    kw2 = gateway_call_kwargs("task-1", include_cost=False)
    assert kw2["estimated_cost"] == 0.0


def test_idempotency_lock_acquire_release():
    idem = GatewayIdempotency()
    assert idem.acquire_lock("task-lock-1")
    assert not idem.acquire_lock("task-lock-1")
    idem.release_lock("task-lock-1")
    assert idem.acquire_lock("task-lock-1")


@pytest.mark.asyncio
async def test_execute_route_passes_budget_to_check():
    fake_result = GenerationResult(media_url="https://example.com/x.png", model="face-swap")

    async def fake_execute(*args, **kwargs):
        return fake_result

    mock_backend = MagicMock()
    mock_backend.is_configured.return_value = True
    mock_backend.execute = fake_execute

    with patch("app.gateway.executor.get_backend", return_value=mock_backend), \
         patch("app.gateway.providers.get_backend", return_value=mock_backend), \
         patch("app.gateway.health.provider_health.is_available", return_value=True), \
         patch("app.gateway.budget.gateway_budget.check") as mock_check, \
         patch("app.gateway.budget.gateway_budget.record") as mock_record, \
         patch("app.gateway.idempotency.gateway_idempotency.acquire_lock", return_value=True), \
         patch("app.gateway.idempotency.gateway_idempotency.mark_done"), \
         patch("app.gateway.idempotency.gateway_idempotency.release_lock"):
        mock_check.return_value = MagicMock(allowed=True)
        await execute_route(
            Capability.IMAGE_FACE_SWAP,
            "face-swap",
            face_url="https://a.com/f.png",
            target_url="https://a.com/t.png",
            trace_id="budget-task-1",
            user_id=7,
            team_id="team-x",
            estimated_cost=5.0,
        )
        mock_check.assert_called_once_with(user_id=7, team_id="team-x", estimated_cost=5.0)
        mock_record.assert_called_once()


def test_prometheus_gateway_counter():
    before = GATEWAY_REQUESTS.labels(
        capability="image.upscale", provider="kie", status="ok",
    )._value.get()
    record_gateway_request(provider="kie", capability="image.upscale", success=True)
    after = GATEWAY_REQUESTS.labels(
        capability="image.upscale", provider="kie", status="ok",
    )._value.get()
    assert after == before + 1


def test_public_health_minimal_in_production(monkeypatch):
    monkeypatch.setattr("app.api.gateway_admin.settings.ENV", "production")
    monkeypatch.setattr("app.api.gateway_admin.settings.GATEWAY_HEALTH_PUBLIC_MINIMAL", "")
    from app.api.gateway_admin import _public_health_minimal
    assert _public_health_minimal() is True


@pytest.mark.asyncio
async def test_facade_face_swap_routes_through_executor():
    from app.gateway.facade import GatewayFacade

    fake_gw = MagicMock()
    fake_gw.result = GenerationResult(media_url="https://example.com/swap.png", model="face-swap")

    facade = GatewayFacade()
    with patch("app.gateway.facade.publicize_url", new_callable=AsyncMock) as pub, \
         patch("app.gateway.facade.execute_route", new_callable=AsyncMock) as ex:
        pub.side_effect = lambda u, **k: u
        ex.return_value = fake_gw
        gw = await facade.face_swap(
            face_url="https://a.com/f.png",
            target_url="https://a.com/t.png",
            user_id=1,
            team_id="t1",
            estimated_cost=3.0,
        )
        assert gw is fake_gw
        ex.assert_called_once()
        call_kw = ex.call_args.kwargs
        assert call_kw["user_id"] == 1
        assert call_kw["team_id"] == "t1"
        assert call_kw["estimated_cost"] == 3.0
