"""Gateway unit tests — routing, failover, circuit breaker (no live API calls)."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.adapters.base import GenerationResult
from app.gateway.config import find_route, get_routes
from app.gateway.executor import execute_route
from app.gateway.health import provider_health
from app.gateway.router import infer_capability, select_targets
from app.gateway.types import Capability


@pytest.fixture(autouse=True)
def reset_provider_health():
    provider_health._memory.clear()
    provider_health._circuits.clear()
    yield
    provider_health._memory.clear()
    provider_health._circuits.clear()


def test_routes_yaml_loads():
    routes = get_routes(reload=True)
    assert len(routes) >= 8
    seedance = find_route(Capability.VIDEO_GENERATE, "seedance-2.0")
    assert seedance is not None
    assert len(seedance.chain) >= 1
    assert seedance.chain[0].provider == "kie"


def test_infer_capability_image_vs_video():
    assert infer_capability("gpt-image-2") == Capability.IMAGE_GENERATE
    assert infer_capability("seedance-2.0") == Capability.VIDEO_GENERATE
    assert infer_capability("nano-banana", has_refs=True) == Capability.IMAGE_EDIT


def test_select_targets_skips_unconfigured_provider(monkeypatch):
    route = find_route(Capability.IMAGE_GENERATE, "gpt-image-2")
    assert route is not None

    mock_kie = MagicMock()
    mock_kie.is_configured.return_value = True
    mock_repl = MagicMock()
    mock_repl.is_configured.return_value = False

    with patch("app.gateway.providers.get_backend") as gb:
        gb.side_effect = lambda p: mock_kie if p == "kie" else mock_repl
        targets = select_targets(route)
    providers = [t.provider for t in targets]
    assert "kie" in providers
    assert "replicate" not in providers


@pytest.mark.asyncio
async def test_execute_route_primary_success(monkeypatch):
    fake_result = GenerationResult(media_url="https://example.com/img.png", model="gpt-image-2")

    async def fake_execute(*args, **kwargs):
        return fake_result

    mock_backend = MagicMock()
    mock_backend.is_configured.return_value = True
    mock_backend.execute = fake_execute

    with patch("app.gateway.executor.get_backend", return_value=mock_backend), \
         patch("app.gateway.providers.get_backend", return_value=mock_backend), \
         patch.object(provider_health, "is_available", return_value=True):
        gw = await execute_route(
            Capability.IMAGE_GENERATE,
            "gpt-image-2",
            prompt="a red apple",
            trace_id="test-1",
        )

    assert gw.provider_used == "kie"
    assert gw.fallback_used is False
    assert gw.result.media_url == "https://example.com/img.png"


@pytest.mark.asyncio
async def test_execute_route_fallback_on_retryable_error(monkeypatch):
    fake_result = GenerationResult(media_url="https://example.com/fallback.png", model="flux")

    call_count = 0

    async def fake_execute(capability, remote_model, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("503 Service Unavailable")
        return fake_result

    mock_backend = MagicMock()
    mock_backend.is_configured.return_value = True
    mock_backend.execute = fake_execute

    with patch("app.gateway.executor.get_backend", return_value=mock_backend), \
         patch("app.gateway.providers.get_backend", return_value=mock_backend), \
         patch.object(provider_health, "is_available", return_value=True):
        gw = await execute_route(
            Capability.IMAGE_GENERATE,
            "gpt-image-2",
            prompt="test",
        )

    assert call_count == 2
    assert gw.fallback_used is True
    assert gw.result.media_url == "https://example.com/fallback.png"


@pytest.mark.asyncio
async def test_execute_route_stops_on_fatal_error(monkeypatch):
    call_count = 0

    async def fake_execute(capability, remote_model, **kwargs):
        nonlocal call_count
        call_count += 1
        raise RuntimeError("API key not configured")

    mock_backend = MagicMock()
    mock_backend.is_configured.return_value = True
    mock_backend.execute = fake_execute

    with patch("app.gateway.executor.get_backend", return_value=mock_backend), \
         patch("app.gateway.providers.get_backend", return_value=mock_backend), \
         patch.object(provider_health, "is_available", return_value=True):
        with pytest.raises(RuntimeError, match="API key"):
            await execute_route(Capability.IMAGE_GENERATE, "gpt-image-2", prompt="x")

    assert call_count == 1


def test_provider_circuit_opens_after_failures():
    for _ in range(3):
        provider_health.record_failure("kie", "gpt-image-2-text-to-image", "503 timeout")
    assert not provider_health.is_available("kie", "gpt-image-2-text-to-image")
