"""
Prometheus application metrics.

HTTP counters/histograms are updated by the request middleware. Runtime gauges
(Celery queue depth, task counts, balances) are refreshed lazily at scrape time
so /metrics reflects live state without a background collector.
"""
from __future__ import annotations

import logging
import re

from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

from app.config import settings

logger = logging.getLogger(__name__)

REGISTRY = CollectorRegistry()

HTTP_REQUESTS = Counter(
    "betty_http_requests_total", "HTTP requests", ["method", "path", "status"], registry=REGISTRY,
)
HTTP_LATENCY = Histogram(
    "betty_http_request_duration_seconds", "HTTP request latency", ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30), registry=REGISTRY,
)
HTTP_IN_FLIGHT = Gauge("betty_http_in_flight", "In-flight HTTP requests", registry=REGISTRY)
HTTP_EXCEPTIONS = Counter("betty_http_exceptions_total", "Unhandled exceptions", registry=REGISTRY)

QUEUE_DEPTH = Gauge("betty_celery_queue_depth", "Pending tasks per Celery queue", ["queue"], registry=REGISTRY)
TASKS_TOTAL = Gauge("betty_tasks_total", "Tasks by status", ["status"], registry=REGISTRY)
UP = Gauge("betty_up", "Service up (1) — dependency health", ["dependency"], registry=REGISTRY)

_ID_RE = re.compile(r"/(?:[0-9a-f]{8,}|\d+)(?=/|$)", re.IGNORECASE)
_CELERY_QUEUES = ["celery", "image_q", "video_q", "director_q", "collector_q"]


def normalize_path(path: str) -> str:
    """Collapse ids to :id to keep label cardinality bounded."""
    if path.startswith("/api/v1/media"):
        return "/api/v1/media/*"
    return _ID_RE.sub("/:id", path)


async def _refresh_runtime_gauges() -> None:
    # Celery queue depth (Redis list length per queue on the broker db)
    try:
        import redis as _redis
        c = _redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=2)
        for q in _CELERY_QUEUES:
            try:
                QUEUE_DEPTH.labels(queue=q).set(c.llen(q))
            except Exception:
                pass
        c.ping()
        UP.labels(dependency="redis").set(1)
    except Exception:
        UP.labels(dependency="redis").set(0)

    # Task counts by status
    try:
        from sqlalchemy import select, func
        from app.db import async_session
        from app.models.task import Task
        async with async_session() as db:
            rows = await db.execute(select(Task.status, func.count()).group_by(Task.status))
            counts = {s or "unknown": n for s, n in rows.all()}
            for status in ("queued", "generating", "completed", "failed"):
                TASKS_TOTAL.labels(status=status).set(counts.get(status, 0))
        UP.labels(dependency="database").set(1)
    except Exception:
        UP.labels(dependency="database").set(0)


async def render_metrics() -> tuple[bytes, str]:
    await _refresh_runtime_gauges()
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
