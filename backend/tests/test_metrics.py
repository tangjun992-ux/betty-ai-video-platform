"""Metrics tests — label cardinality control and registry rendering."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.metrics import (
    CONTENT_TYPE_LATEST,
    HTTP_REQUESTS,
    normalize_path,
    render_metrics,
)


def test_normalize_path_collapses_ids():
    assert normalize_path("/api/v1/tasks/12345") == "/api/v1/tasks/:id"
    assert normalize_path("/api/v1/tasks/deadbeefcafe/results") == "/api/v1/tasks/:id/results"
    assert normalize_path("/api/v1/projects/7/assets/42") == "/api/v1/projects/:id/assets/:id"


def test_normalize_path_keeps_static_routes():
    assert normalize_path("/api/v1/gallery") == "/api/v1/gallery"
    assert normalize_path("/health") == "/health"


def test_media_paths_collapse_to_a_single_label():
    assert normalize_path("/api/v1/media/generated/abc123.mp4") == "/api/v1/media/*"


def test_render_metrics_exposes_counters(monkeypatch):
    async def noop():
        return None

    monkeypatch.setattr("app.metrics._refresh_runtime_gauges", noop)
    HTTP_REQUESTS.labels(method="GET", path="/api/v1/gallery", status="200").inc()

    body, content_type = asyncio.run(render_metrics())
    assert content_type == CONTENT_TYPE_LATEST
    assert b"betty_http_requests_total" in body
    assert b'path="/api/v1/gallery"' in body


def test_runtime_gauges_survive_missing_dependencies(monkeypatch):
    from app.metrics import UP, _refresh_runtime_gauges

    monkeypatch.setattr(
        "app.config.settings.CELERY_BROKER_URL", "redis://127.0.0.1:1/0")
    asyncio.run(_refresh_runtime_gauges())
    assert UP.labels(dependency="redis")._value.get() == 0
