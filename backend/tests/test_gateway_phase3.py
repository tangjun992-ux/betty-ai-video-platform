"""Phase 3 gateway tests — registry, budget, canary, region, kill switch."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.adapters.base import GenerationResult
from app.gateway.budget import GatewayBudget, gateway_budget
from app.gateway.config import find_route, get_routes
from app.gateway.executor import execute_route
from app.gateway.health import provider_health
from app.gateway.metrics import GatewayMetrics, gateway_metrics
from app.gateway.registry import GatewayRegistry, gateway_registry
from app.gateway.router import (
    _order_with_canary,
    _stable_bucket,
    select_targets,
)
from app.gateway.types import Capability, ProviderTarget


@pytest.fixture(autouse=True)
def reset_gateway_runtime():
    """Isolate in-memory registry / budget / metrics between tests."""
    gateway_registry._memory_disabled.clear()
    gateway_registry._memory_kill = False
    gateway_budget._memory.clear()
    gateway_metrics._memory.clear()
    provider_health._memory.clear()
    provider_health._circuits.clear()
    yield
    gateway_registry._memory_disabled.clear()
    gateway_registry._memory_kill = False
    gateway_budget._memory.clear()
    gateway_metrics._memory.clear()
    provider_health._memory.clear()
    provider_health._circuits.clear()


def test_registry_disable_enable():
    reg = GatewayRegistry()
    assert not reg.is_disabled("kie", "gpt-image-2-text-to-image")
    reg.disable_provider("kie", "gpt-image-2-text-to-image", reason="test")
    assert reg.is_disabled("kie", "gpt-image-2-text-to-image")
    disabled = reg.list_disabled()
    assert any(d["key"] == "kie:gpt-image-2-text-to-image" for d in disabled)
    reg.enable_provider("kie", "gpt-image-2-text-to-image")
    assert not reg.is_disabled("kie", "gpt-image-2-text-to-image")


def test_registry_kill_switch():
    reg = GatewayRegistry()
    assert not reg.kill_switch_active()
    reg.set_kill_switch(True)
    assert reg.kill_switch_active()
    snap = reg.snapshot()
    assert snap["kill_switch"] is True
    reg.set_kill_switch(False)
    assert not reg.kill_switch_active()


def test_kill_switch_blocks_select_targets():
    get_routes(reload=True)
    route = find_route(Capability.IMAGE_GENERATE, "gpt-image-2")
    assert route is not None

    mock_kie = MagicMock()
    mock_kie.is_configured.return_value = True

    gateway_registry.set_kill_switch(True)
    with patch("app.gateway.providers.get_backend", return_value=mock_kie), \
         patch.object(provider_health, "is_available", return_value=True):
        assert select_targets(route) == []


def test_budget_user_cap_blocks():
    budget = GatewayBudget()
    with patch("app.gateway.budget.settings") as s:
        s.GATEWAY_USER_DAILY_CREDIT_CAP = 100.0
        s.GATEWAY_TEAM_DAILY_CREDIT_CAP = 0
        budget._memory["user:42"] = 95.0
        result = budget.check(user_id=42, estimated_cost=10.0)
    assert not result.allowed
    assert "额度已用尽" in result.reason


def test_budget_kill_switch_blocks():
    gateway_registry.set_kill_switch(True)
    with patch("app.gateway.budget.settings") as s:
        s.GATEWAY_USER_DAILY_CREDIT_CAP = 1000.0
        s.GATEWAY_TEAM_DAILY_CREDIT_CAP = 0
        result = gateway_budget.check(user_id=1, estimated_cost=1.0)
    assert not result.allowed
    assert "kill switch" in result.reason.lower()


def test_budget_record_and_status():
    budget = GatewayBudget()
    with patch("app.gateway.budget.settings") as s:
        s.GATEWAY_USER_DAILY_CREDIT_CAP = 500.0
        s.GATEWAY_TEAM_DAILY_CREDIT_CAP = 0
        budget.record(25.0, user_id=7)
        budget.record(10.0, user_id=7)
        status = budget.status(user_id=7)
    assert status["user_spent_today"] == 35.0
    assert status["user_remaining"] == 465.0


def test_stable_bucket_deterministic():
    a = _stable_bucket("trace-abc", "canary")
    b = _stable_bucket("trace-abc", "canary")
    c = _stable_bucket("trace-xyz", "canary")
    assert a == b
    assert 0 <= a < 100
    assert 0 <= c < 100


def test_canary_routing_five_percent_to_seedance():
    get_routes(reload=True)
    route = find_route(Capability.VIDEO_GENERATE, "seedance-2.0")
    assert route is not None

    mock_kie = MagicMock()
    mock_kie.is_configured.return_value = True
    mock_seedance = MagicMock()
    mock_seedance.is_configured.return_value = True

    def backend(name):
        return {"kie": mock_kie, "seedance": mock_seedance, "replicate": MagicMock(is_configured=lambda: False)}.get(name)

    chosen_seedance_trace = None
    for i in range(500):
        trace = f"canary-probe-{i}"
        with patch("app.gateway.providers.get_backend", side_effect=backend), \
             patch.object(provider_health, "is_available", return_value=True), \
             patch("app.gateway.router.settings") as rs:
            rs.GATEWAY_REGION = "cn"
            targets = select_targets(route, trace_id=trace)
        if targets and targets[0].provider == "seedance":
            chosen_seedance_trace = trace
            break

    assert chosen_seedance_trace is not None, "expected some trace_id to hit 5% seedance canary"


def test_region_filter_excludes_cn_only_target():
    get_routes(reload=True)
    route = find_route(Capability.VIDEO_GENERATE, "seedance-2.0")
    assert route is not None

    mock_kie = MagicMock()
    mock_kie.is_configured.return_value = True
    mock_seedance = MagicMock()
    mock_seedance.is_configured.return_value = True

    def backend(name):
        return {"kie": mock_kie, "seedance": mock_seedance}.get(name)

    with patch("app.gateway.providers.get_backend", side_effect=backend), \
         patch.object(provider_health, "is_available", return_value=True), \
         patch("app.gateway.router.settings") as rs:
        rs.GATEWAY_REGION = "us"
        targets = select_targets(route, trace_id="us-user")
    providers = [t.provider for t in targets if not t.fallback_only]
    assert "seedance" not in providers
    assert "kie" in providers


def test_order_with_canary_respects_weights():
    kie = ProviderTarget(provider="kie", remote_model="m1", weight=95)
    canary = ProviderTarget(provider="seedance", remote_model="m2", canary_percent=5)
    ordered = _order_with_canary([kie, canary], trace_id="stable-kie-bucket")
    assert ordered[0].provider in ("kie", "seedance")
    assert len(ordered) == 2


def test_select_targets_skips_admin_disabled():
    get_routes(reload=True)
    route = find_route(Capability.IMAGE_GENERATE, "gpt-image-2")
    assert route is not None

    mock_kie = MagicMock()
    mock_kie.is_configured.return_value = True
    mock_repl = MagicMock()
    mock_repl.is_configured.return_value = True

    gateway_registry.disable_provider("kie", "gpt-image-2-text-to-image")

    with patch("app.gateway.providers.get_backend") as gb:
        gb.side_effect = lambda p: mock_kie if p == "kie" else mock_repl
        with patch.object(provider_health, "is_available", return_value=True):
            targets = select_targets(route)
    providers = [t.provider for t in targets]
    assert "kie" not in providers
    assert "replicate" in providers


def test_metrics_record_request():
    metrics = GatewayMetrics()
    metrics.record_request(provider="kie", capability="image.generate", success=True)
    metrics.record_request(provider="kie", capability="image.generate", success=False, fallback=True)
    snap = metrics.snapshot()
    counters = snap["counters"]
    assert any("req:image.generate:kie" in k for k in counters)
    assert any("fallback:image.generate:kie" in k for k in counters)


@pytest.mark.asyncio
async def test_execute_route_budget_denied():
    with patch("app.gateway.budget.settings") as s:
        s.GATEWAY_USER_DAILY_CREDIT_CAP = 10.0
        s.GATEWAY_TEAM_DAILY_CREDIT_CAP = 0
        gateway_budget._memory["user:99"] = 10.0
        with pytest.raises(RuntimeError, match="额度"):
            await execute_route(
                Capability.IMAGE_GENERATE,
                "gpt-image-2",
                prompt="x",
                user_id=99,
                estimated_cost=1.0,
            )


@pytest.mark.asyncio
async def test_seedance_kling_backends_registered():
    from app.gateway.providers import get_backend, list_backends

    backends = list_backends()
    assert "seedance" in backends
    assert "kling" in backends
    assert get_backend("seedance") is not None
    assert get_backend("kling") is not None


@pytest.mark.asyncio
async def test_routes_yaml_seedance_canary_entry():
    get_routes(reload=True)
    route = find_route(Capability.VIDEO_GENERATE, "seedance-2.0")
    assert route is not None
    canary = [t for t in route.chain if t.provider == "seedance"]
    assert len(canary) == 1
    assert canary[0].canary_percent == 5
    assert canary[0].region == "cn"
