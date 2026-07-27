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
    from app.services.model_smoke import run_live_video_sample

    report = run_live_video_sample()
    logger.info(
        "live_video weekly smoke: probed=%s outframe_ok=%s skipped=%s failed=%s",
        report["probed"], report["outframe_ok"], report.get("outframe_skipped"), report["failed"],
    )
    return report


@app.task(name="app.tasks.health_tasks.smoke_live_image_weekly", bind=True, max_retries=0)
def smoke_live_image_weekly(self):
    """Weekly paid image out-frame sample — gated by MODEL_SMOKE_LIVE_IMAGE_WEEKLY or MODEL_SMOKE_LIVE."""
    weekly = os.getenv("MODEL_SMOKE_LIVE_IMAGE_WEEKLY", "").strip().lower() in (
        "1", "true", "yes", "on",
    )
    live = os.getenv("MODEL_SMOKE_LIVE", "").strip().lower() in ("1", "true", "yes", "on")
    if not (weekly or live):
        return {
            "mode": "live_image_sample",
            "skipped": True,
            "reason": "MODEL_SMOKE_LIVE_IMAGE_WEEKLY not enabled",
            "probed": 0,
            "outframe_ok": 0,
        }
    os.environ.setdefault("MODEL_SMOKE_LIVE", "1")
    from app.services.model_smoke import run_live_image_sample

    report = run_live_image_sample()
    logger.info(
        "live_image weekly smoke: probed=%s outframe_ok=%s failed=%s",
        report["probed"], report["outframe_ok"], report["failed"],
    )
    return report
