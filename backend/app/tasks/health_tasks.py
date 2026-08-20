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


@app.task(name="app.tasks.health_tasks.smoke_live_lipsync_weekly", bind=True, max_retries=0)
def smoke_live_lipsync_weekly(self):
    """Weekly lipsync live probe — gated by LIPSYNC_FIXTURE_LIVE_WEEKLY=1.

    Uses fixture_derivative_harness optional live path; skipped when gate off.
    """
    weekly = os.getenv("LIPSYNC_FIXTURE_LIVE_WEEKLY", "").strip().lower() in (
        "1", "true", "yes", "on",
    )
    live = os.getenv("LIPSYNC_FIXTURE_LIVE", "").strip().lower() in ("1", "true", "yes", "on")
    if not (weekly or live):
        return {
            "mode": "live_lipsync_sample",
            "skipped": True,
            "reason": "LIPSYNC_FIXTURE_LIVE_WEEKLY not enabled",
            "ok": False,
        }
    os.environ.setdefault("LIPSYNC_FIXTURE_LIVE", "1")
    from pathlib import Path
    import json
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "fixture_derivative_harness.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=600,
            env={**os.environ, "LIPSYNC_FIXTURE_LIVE": "1"},
        )
        report = {"returncode": proc.returncode, "ok": proc.returncode == 0}
        for line in (proc.stderr or "").splitlines():
            if line.strip().startswith("{"):
                try:
                    payload = json.loads(line)
                    if "lipsync_live" in payload:
                        report.update(payload["lipsync_live"])
                except json.JSONDecodeError:
                    pass
        last_run = root / "fixtures" / "lipsync" / "last_run.json"
        if last_run.is_file():
            report["last_run"] = json.loads(last_run.read_text(encoding="utf-8"))
        logger.info("live_lipsync weekly smoke: ok=%s skipped=%s", report.get("ok"), report.get("skipped"))
        return report
    except Exception as exc:
        logger.exception("live_lipsync weekly smoke failed")
        return {"mode": "live_lipsync_sample", "ok": False, "error": str(exc)[:200]}
