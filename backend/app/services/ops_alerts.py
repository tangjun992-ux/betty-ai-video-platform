"""Ops alerting — Slack/generic webhook for webhook delivery failures."""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def alert_webhook_url() -> str:
    return (
        os.getenv("OPS_ALERT_WEBHOOK_URL", "").strip()
        or os.getenv("SLACK_WEBHOOK_URL", "").strip()
    )


def alert_webhook_failure(
    task_id: str,
    delivery: dict[str, Any],
    *,
    task: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Post webhook delivery failure to ops channel (best-effort)."""
    url = alert_webhook_url()
    if not url:
        return {"sent": False, "reason": "no_alert_url"}
    task = task or {}
    wh_url = (task.get("webhook_url") or "")[:120]
    reason = (delivery.get("reason") or "unknown")[:200]
    text = (
        ":warning: *Betty webhook 投递失败*\n"
        f"• task: `{task_id}`\n"
        f"• status: {task.get('status') or '—'}\n"
        f"• callback: {wh_url or '—'}\n"
        f"• attempts: {delivery.get('attempts') or '—'}\n"
        f"• reason: {reason}"
    )
    try:
        with httpx.Client(timeout=8.0, follow_redirects=False) as client:
            resp = client.post(url, json={"text": text})
        ok = 200 <= resp.status_code < 300
        if not ok:
            logger.warning("ops alert non-2xx task=%s status=%s", task_id, resp.status_code)
        return {"sent": ok, "status_code": resp.status_code}
    except Exception as e:
        logger.warning("ops alert failed task=%s: %s", task_id, e)
        return {"sent": False, "reason": str(e)}


def ops_alerts_status() -> dict[str, Any]:
    configured = bool(alert_webhook_url())
    return {
        "webhook_failure_alerts": configured,
        "env": "OPS_ALERT_WEBHOOK_URL or SLACK_WEBHOOK_URL",
    }
