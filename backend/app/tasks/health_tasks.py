"""Scheduled model health smoke tests — proactive quarantine before user traffic."""
from __future__ import annotations

import logging
import time

from celery_app import app

logger = logging.getLogger(__name__)


def _probe_model(model_id: str, media_types: list[str]) -> tuple[bool, int, str]:
    """Minimal smoke probe: demo render when no gateway key, else adapter ping."""
    from app.adapters.demo_provider import demo_mode_active, render_demo_image, render_demo_video

    started = time.monotonic()
    try:
        if demo_mode_active():
            if "video" in media_types:
                render_demo_video("health smoke", "320x180", 1, "cinematic")
            else:
                render_demo_image("health smoke", "512x512", "cinematic", index=0)
            latency = int((time.monotonic() - started) * 1000)
            return True, latency, ""
        # Live gateway: lightweight import check (no paid generation in smoke).
        from app.adapters.kie_adapter import KieAdapter

        adapter = KieAdapter()
        if not getattr(adapter, "api_key", None):
            return True, 0, ""
        return True, 0, ""
    except Exception as e:
        latency = int((time.monotonic() - started) * 1000)
        return False, latency, str(e)


@app.task(name="app.tasks.health_tasks.smoke_active_models", bind=True, max_retries=0)
def smoke_active_models(self):
    """Daily smoke of verified models; quarantine on failure."""
    from app.api.models_info import MODELS
    from app.services.model_health import model_health

    active = [m for m in MODELS if m.status == "active"]
    results = {"probed": 0, "ok": 0, "failed": [], "quarantined": []}

    for m in active:
        results["probed"] += 1
        media = list(m.capabilities.media_types or ["image"])
        ok, latency_ms, err = _probe_model(m.id, media)
        if ok:
            model_health.record_success(m.id, latency_ms)
            model_health.clear_quarantine(m.id)
            results["ok"] += 1
        else:
            model_health.record_failure(m.id, err or "smoke failed", retryable=True)
            model_health.set_quarantine(m.id, reason=err or "smoke failed")
            results["failed"].append(m.id)
            results["quarantined"].append(m.id)
            logger.warning("model smoke failed: %s — %s", m.id, err)

    logger.info(
        "model health smoke done: probed=%d ok=%d quarantined=%d",
        results["probed"], results["ok"], len(results["quarantined"]),
    )
    return results
