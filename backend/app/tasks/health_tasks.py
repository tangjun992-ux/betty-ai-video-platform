"""Scheduled model health smoke tests — proactive quarantine before user traffic."""
from __future__ import annotations

import logging

from celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="app.tasks.health_tasks.smoke_active_models", bind=True, max_retries=0)
def smoke_active_models(self, mode: str | None = None):
    """Daily smoke of verified models; optional live KIE when MODEL_SMOKE_LIVE=1."""
    from app.services.model_smoke import run_active_smoke

    return run_active_smoke(mode=mode)
