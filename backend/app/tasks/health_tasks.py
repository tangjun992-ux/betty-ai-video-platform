"""Scheduled model health smoke tests — proactive quarantine before user traffic."""
from __future__ import annotations

import logging
import os

from celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="app.tasks.health_tasks.smoke_active_models", bind=True, max_retries=0)
def smoke_active_models(self, mode: str | None = None):
    """Daily smoke of verified models; optional live KIE when MODEL_SMOKE_LIVE=1."""
    from app.services.model_smoke import run_active_smoke

    return run_active_smoke(mode=mode)


@app.task(name="app.tasks.health_tasks.smoke_live_video_weekly", bind=True, max_retries=0)
def smoke_live_video_weekly(self):
    """Weekly paid video out-frame sample — gated; never runs unpaid by accident.

    Requires MODEL_SMOKE_LIVE_VIDEO_WEEKLY=1 (or MODEL_SMOKE_LIVE_VIDEO=1).
    KPI honesty: only ``live_video`` path counts as outframe_ok; skipped ≠ success.
    """
    weekly = os.getenv("MODEL_SMOKE_LIVE_VIDEO_WEEKLY", "").strip().lower() in (
        "1", "true", "yes", "on",
    )
    live_video = os.getenv("MODEL_SMOKE_LIVE_VIDEO", "").strip().lower() in (
        "1", "true", "yes", "on",
    )
    if not (weekly or live_video):
        report = {
            "mode": "live_video_sample",
            "skipped": True,
            "reason": "MODEL_SMOKE_LIVE_VIDEO_WEEKLY not enabled",
            "probed": 0,
            "ok": 0,
            "outframe_ok": 0,
            "outframe_skipped": 0,
            "failed": [],
        }
        logger.info("live_video weekly smoke skipped (env gate off)")
        return report

    os.environ.setdefault("MODEL_SMOKE_LIVE_VIDEO", "1")
    from app.services.model_smoke import probe_model, save_last_smoke
    from app.api.models_info import MODELS
    from app.services.model_health import model_health, quarantine_ttl_for_reason
    import time

    models = ("seedance-2.0-fast", "kling-2.5-turbo")
    by_id = {m.id: m for m in MODELS}
    report = {
        "mode": "live_video_sample",
        "probed": 0,
        "ok": 0,
        "outframe_ok": 0,
        "outframe_skipped": 0,
        "failed": [],
        "quarantined": [],
        "skipped": [],
        "details": [],
    }
    for mid in models:
        m = by_id.get(mid)
        if not m:
            report["failed"].append(mid)
            report["details"].append({"model_id": mid, "ok": False, "error": "not in catalog"})
            continue
        report["probed"] += 1
        media = list(m.capabilities.media_types or ["video"])
        probe = probe_model(mid, media, mode="live_video")
        report["details"].append({"model_id": mid, **probe})
        path = (probe.get("evidence") or {}).get("path") or ""
        if probe.get("ok") and path == "live_video":
            model_health.record_success(mid, probe.get("latency_ms") or 0)
            model_health.clear_quarantine(mid)
            report["ok"] += 1
            report["outframe_ok"] += 1
        elif probe.get("ok"):
            report["skipped"].append(mid)
            report["outframe_skipped"] += 1
        else:
            err = probe.get("error") or "live_video sample failed"
            model_health.record_failure(mid, err, retryable=True)
            model_health.set_quarantine(mid, reason=err, ttl=quarantine_ttl_for_reason(err))
            report["failed"].append(mid)
            report["quarantined"].append(mid)

    report["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_last_smoke(report)
    logger.info(
        "live_video weekly smoke: probed=%s outframe_ok=%s skipped=%s failed=%s",
        report["probed"], report["outframe_ok"], report["outframe_skipped"], report["failed"],
    )
    return report
