"""Phase 6 gateway tests — route validation, gateway fallback, inflight metrics."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.gateway.config import load_routes, validate_routes
from app.gateway.provider_limit import GatewayProviderLimit
from app.gateway.types import Capability, ProviderTarget, RouteDefinition
from app.metrics import GATEWAY_PROVIDER_INFLIGHT


def test_validate_routes_ok_on_default_config():
    routes = load_routes()
    assert routes
    assert validate_routes(routes) == []


def test_validate_routes_detects_duplicate():
    dup = RouteDefinition(
        capability=Capability.IMAGE_GENERATE,
        model="test-dup",
        chain=(ProviderTarget(provider="kie", remote_model="x"),),
    )
    routes = [dup, dup]
    errs = validate_routes(routes)
    assert any("Duplicate" in e for e in errs)


def test_validate_routes_detects_unknown_provider():
    bad = RouteDefinition(
        capability=Capability.IMAGE_GENERATE,
        model="bad-route",
        chain=(ProviderTarget(provider="unknown-vendor", remote_model="m"),),
    )
    errs = validate_routes([bad])
    assert any("Unknown provider" in e for e in errs)


def test_provider_inflight_snapshot_memory():
    lim = GatewayProviderLimit()
    with patch.object(lim, "_max_inflight", return_value=5):
        lim.acquire_inflight("kie")
        snap = lim.inflight_snapshot()
        assert snap.get("kie", 0) >= 1
        lim.release_inflight("kie")


def test_limits_status_shape():
    lim = GatewayProviderLimit()
    status = lim.limits_status()
    assert "max_inflight" in status
    assert "rpm_default" in status
    assert "inflight" in status


@pytest.mark.asyncio
async def test_image_retryable_uses_gateway_when_enabled():
    from app.tasks import image_tasks

    fake_result = MagicMock()
    fake_result.to_dict.return_value = {"media_url": "https://cdn/x.png", "cost": 1}
    gw_result = MagicMock(result=fake_result, fallback_used=True)

    mock_gw = MagicMock()
    mock_gw.generate_image = AsyncMock(return_value=gw_result)

    with patch("app.gateway.gateway_enabled", return_value=True), \
         patch("app.gateway.gateway", mock_gw), \
         patch("app.tasks.gateway_context.gateway_call_kwargs", return_value={}), \
         patch("app.tasks.image_tasks._run_async", return_value=gw_result), \
         patch("app.tasks.image_tasks._update_task"), \
         patch("app.tasks.image_tasks.persist_results", side_effect=lambda x: x), \
         patch("app.services.model_health.model_health.record_success"), \
         patch("app.fallback_handler.get_fallback", return_value="nano-banana"), \
         patch("app.fallback_handler.is_retryable_error", return_value=True):
        out = image_tasks._handle_retryable(
            MagicMock(update_state=MagicMock()),
            "task-1",
            "gpt-image-2",
            "timeout",
            "image",
            "a cat",
            {"size": "1024x1024", "style": "auto", "count": 1},
        )
    assert out["status"] == "completed_fallback"
    mock_gw.generate_image.assert_called_once()
    assert mock_gw.generate_image.call_args.kwargs["model"] == "nano-banana"


def test_prometheus_inflight_gauge_labels():
    # Ensure metric is registered with expected label names
    GATEWAY_PROVIDER_INFLIGHT.labels(provider="kie").set(0)
