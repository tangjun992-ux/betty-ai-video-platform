"""Phase 5 gateway tests — provider limits, motion gateway-only."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.gateway.executor import execute_route
from app.gateway.health import provider_health
from app.gateway.provider_limit import GatewayProviderLimit
from app.gateway.types import Capability


@pytest.fixture(autouse=True)
def reset_health():
    provider_health._memory.clear()
    provider_health._circuits.clear()
    yield
    provider_health._memory.clear()
    provider_health._circuits.clear()


def test_provider_limit_rpm_blocks():
    lim = GatewayProviderLimit()
    with patch.object(lim, "_rpm_cap", return_value=2):
        assert lim.check_rpm("kie").allowed
        assert lim.check_rpm("kie").allowed
        third = lim.check_rpm("kie")
        assert not third.allowed


def test_provider_inflight_acquire_release():
    lim = GatewayProviderLimit()
    with patch.object(lim, "_max_inflight", return_value=1):
        assert lim.acquire_inflight("kie").allowed
        assert not lim.acquire_inflight("kie").allowed
        lim.release_inflight("kie")
        assert lim.acquire_inflight("kie").allowed
        lim.release_inflight("kie")


@pytest.mark.asyncio
async def test_executor_skips_rate_limited_provider():
    fake_result = MagicMock()
    fake_result.cost = 1

    kie = MagicMock()
    kie.is_configured.return_value = True

    repl = MagicMock()
    repl.is_configured.return_value = True

    call_count = {"kie": 0, "replicate": 0}

    async def kie_execute(*args, **kwargs):
        call_count["kie"] += 1
        return fake_result

    async def repl_execute(*args, **kwargs):
        call_count["replicate"] += 1
        return fake_result

    kie.execute = kie_execute
    repl.execute = repl_execute

    def backend(name):
        return {"kie": kie, "replicate": repl}.get(name)

    with patch("app.gateway.providers.get_backend", side_effect=backend), \
         patch("app.gateway.executor.get_backend", side_effect=backend), \
         patch.object(provider_health, "is_available", return_value=True), \
         patch("app.gateway.budget.gateway_budget.check", return_value=MagicMock(allowed=True)), \
         patch("app.gateway.budget.gateway_budget.record"), \
         patch("app.gateway.idempotency.gateway_idempotency.acquire_lock", return_value=True), \
         patch("app.gateway.idempotency.gateway_idempotency.mark_done"), \
         patch("app.gateway.idempotency.gateway_idempotency.release_lock"), \
         patch("app.gateway.provider_limit.gateway_provider_limit.check_and_acquire") as mock_lim:
        mock_lim.side_effect = lambda p: MagicMock(
            allowed=(p == "replicate"),
            reason="RPM" if p == "kie" else "",
        )
        gw = await execute_route(
            Capability.IMAGE_GENERATE,
            "gpt-image-2",
            prompt="test",
        )
    assert gw.provider_used == "replicate"
    assert call_count["kie"] == 0
    assert call_count["replicate"] == 1
