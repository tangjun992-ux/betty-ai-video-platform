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


def send_webhook_failure_digest(*, limit: int = 50) -> dict[str, Any]:
    """Post aggregated webhook failure digest to ops channel (best-effort)."""
    from app.services.task_hooks import webhook_failures_digest

    digest = webhook_failures_digest(limit=limit)
    if digest["total"] == 0:
        return {"sent": False, "reason": "no_failures", "digest": digest}
    url = alert_webhook_url()
    if not url:
        return {"sent": False, "reason": "no_alert_url", "digest": digest}
    reasons = digest.get("top_reasons") or []
    reason_lines = "\n".join(
        f"• {r['reason']} ×{r['count']}" for r in reasons[:5]
    ) or "• —"
    text = (
        ":bar_chart: *Betty Webhook 失败 Digest*\n"
        f"• 总计: {digest['total']}\n"
        f"• 已告警: {digest['alert_sent_count']} · 待告警: {digest['pending_alert']}\n"
        f"*主因:*\n{reason_lines}"
    )
    try:
        with httpx.Client(timeout=8.0, follow_redirects=False) as client:
            resp = client.post(url, json={"text": text})
        ok = 200 <= resp.status_code < 300
        if not ok:
            logger.warning("ops digest non-2xx status=%s", resp.status_code)
        return {"sent": ok, "status_code": resp.status_code, "digest": digest}
    except Exception as e:
        logger.warning("ops digest failed: %s", e)
        return {"sent": False, "reason": str(e), "digest": digest}


def ops_alerts_status() -> dict[str, Any]:
    configured = bool(alert_webhook_url())
    digest_hourly = __import__("os").getenv("OPS_WEBHOOK_DIGEST_HOURLY", "").strip().lower() in (
        "1", "true", "yes", "on",
    )
    return {
        "webhook_failure_alerts": configured,
        "alert_dedupe": True,
        "digest_enabled": True,
        "digest_beat_hourly": digest_hourly or configured,
        "env": "OPS_ALERT_WEBHOOK_URL or SLACK_WEBHOOK_URL",
    }
