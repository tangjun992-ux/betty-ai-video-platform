"""
Task terminal hooks — webhook delivery + user notifications.

Called after a task reaches completed / failed / cancelled.
Matches Runway/Kling/Luma-style partner callbacks and Yapper-style email alerts.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_BACKOFF_S = (0.5, 1.5, 3.0)


def _sync_engine():
    from app.tasks.task_db import get_db_url_sync
    return create_engine(get_db_url_sync())


def _signing_secret() -> str:
    return (
        os.getenv("WEBHOOK_SIGNING_SECRET", "").strip()
        or os.getenv("JWT_SECRET", "").strip()
        or "dev-webhook-secret"
    )


def _load_task_row(db_task_id: str) -> Optional[dict[str, Any]]:
    engine = _sync_engine()
    with Session(engine) as session:
        row = session.execute(
            text(
                "SELECT task_id, user_id, status, prompt, media_type, selected_model, "
                "results, error_message, webhook_url, actual_cost, estimated_cost, parameters "
                "FROM tasks WHERE task_id = :tid"
            ),
            {"tid": db_task_id},
        ).mappings().first()
        return dict(row) if row else None


def _parse_parameters(raw) -> dict:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def persist_webhook_status(db_task_id: str, delivery: dict[str, Any]) -> None:
    """Write webhook delivery outcome into tasks.parameters.webhook (no migration)."""
    from datetime import datetime, timezone

    engine = _sync_engine()
    with Session(engine) as session:
        row = session.execute(
            text("SELECT parameters FROM tasks WHERE task_id = :tid"),
            {"tid": db_task_id},
        ).first()
        if not row:
            return
        params = _parse_parameters(row[0])
        params["webhook"] = {
            "delivered": bool(delivery.get("delivered")),
            "attempts": delivery.get("attempts"),
            "status_code": delivery.get("status_code"),
            "reason": delivery.get("reason"),
            "at": datetime.now(timezone.utc).isoformat(),
        }
        session.execute(
            text("UPDATE tasks SET parameters = :p WHERE task_id = :tid"),
            {"p": json.dumps(params, ensure_ascii=False), "tid": db_task_id},
        )
        session.commit()


def _parse_results(raw) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _safe_webhook_url(url: str) -> bool:
    """Block SSRF to loopback / private hosts in production-ish envs."""
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return False
        host = (p.hostname or "").lower()
        if not host:
            return False
        if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            env = (os.getenv("ENV") or "").lower()
            if env in ("production", "prod"):
                return False
        if host.startswith("10.") or host.startswith("192.168.") or host.startswith("169.254."):
            if (os.getenv("ENV") or "").lower() in ("production", "prod"):
                return False
        return True
    except Exception:
        return False


def build_webhook_payload(task: dict[str, Any]) -> dict[str, Any]:
    results = _parse_results(task.get("results"))
    media_urls = []
    for r in results:
        if isinstance(r, dict):
            u = r.get("url") or r.get("media_url") or ""
            if u:
                media_urls.append(u)
    return {
        "event": f"task.{task.get('status')}",
        "task_id": task.get("task_id"),
        "status": task.get("status"),
        "media_type": task.get("media_type"),
        "model": task.get("selected_model"),
        "prompt": (task.get("prompt") or "")[:500],
        "results": results,
        "media_urls": media_urls,
        "error": task.get("error_message") or "",
        "cost": task.get("actual_cost") or task.get("estimated_cost") or 0,
        "ts": int(time.time()),
    }


def sign_payload(body: bytes, *, secret: str | None = None, timestamp: int | None = None) -> dict[str, str]:
    ts = str(timestamp or int(time.time()))
    sec = (secret or _signing_secret()).encode()
    digest = hmac.new(sec, f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return {
        "X-Betty-Timestamp": ts,
        "X-Betty-Signature": f"sha256={digest}",
        "Content-Type": "application/json",
        "User-Agent": "betty-webhook/1.0",
    }


def deliver_webhook(db_task_id: str, *, task: dict | None = None) -> dict[str, Any]:
    """POST task payload to webhook_url with HMAC signature and retries."""
    task = task or _load_task_row(db_task_id)
    if not task:
        return {"delivered": False, "reason": "task_not_found"}
    url = (task.get("webhook_url") or "").strip()
    if not url:
        return {"delivered": False, "reason": "no_webhook"}
    if not _safe_webhook_url(url):
        logger.warning("webhook blocked unsafe url for task=%s", db_task_id)
        return {"delivered": False, "reason": "unsafe_url"}

    payload = build_webhook_payload(task)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = sign_payload(body)
    last_err = ""
    for attempt, delay in enumerate(_BACKOFF_S[:_MAX_ATTEMPTS]):
        try:
            with httpx.Client(timeout=12.0, follow_redirects=False) as client:
                resp = client.post(url, content=body, headers=headers)
            if 200 <= resp.status_code < 300:
                logger.info("webhook delivered task=%s attempt=%s status=%s", db_task_id, attempt + 1, resp.status_code)
                return {"delivered": True, "status_code": resp.status_code, "attempts": attempt + 1}
            last_err = f"HTTP {resp.status_code}"
            logger.warning("webhook non-2xx task=%s: %s", db_task_id, last_err)
        except Exception as e:
            last_err = str(e)
            logger.warning("webhook attempt %s failed task=%s: %s", attempt + 1, db_task_id, e)
        if attempt < _MAX_ATTEMPTS - 1:
            time.sleep(delay)
    return {"delivered": False, "reason": last_err or "exhausted", "attempts": _MAX_ATTEMPTS}


def _user_wants_email(user_id: int) -> tuple[bool, str]:
    engine = _sync_engine()
    with Session(engine) as session:
        row = session.execute(
            text("SELECT email, metadata_json FROM users WHERE id = :id"),
            {"id": user_id},
        ).first()
        if not row:
            return False, ""
        email, meta_raw = row[0] or "", row[1] or ""
        want = True
        try:
            meta = json.loads(meta_raw) if meta_raw else {}
            notif = meta.get("notifications") or {}
            if "email_task_complete" in notif:
                want = bool(notif["email_task_complete"])
        except Exception:
            pass
        return want, (email or "").strip()


def notify_task_email(db_task_id: str, *, task: dict | None = None) -> dict[str, Any]:
    """Send task-complete email when user prefs allow and SMTP is configured."""
    task = task or _load_task_row(db_task_id)
    if not task:
        return {"sent": False, "reason": "task_not_found"}
    user_id = task.get("user_id")
    if not user_id:
        return {"sent": False, "reason": "no_user"}
    want, email = _user_wants_email(int(user_id))
    if not want:
        return {"sent": False, "reason": "prefs_off"}
    if not email:
        return {"sent": False, "reason": "no_email"}

    status = task.get("status") or ""
    subject = f"betty 任务{'完成' if status == 'completed' else '失败'} · {db_task_id[:8]}"
    results = _parse_results(task.get("results"))
    urls = []
    for r in results:
        if isinstance(r, dict):
            u = r.get("url") or r.get("media_url")
            if u:
                urls.append(u)
    body = (
        f"任务 ID: {db_task_id}\n"
        f"状态: {status}\n"
        f"类型: {task.get('media_type') or ''}\n"
        f"模型: {task.get('selected_model') or ''}\n"
        f"提示词: {(task.get('prompt') or '')[:200]}\n"
    )
    if urls:
        body += "结果:\n" + "\n".join(urls[:5]) + "\n"
    if task.get("error_message"):
        body += f"错误: {task.get('error_message')}\n"

    logger.info("task_notify email stub: to=%s task=%s status=%s", email, db_task_id, status)

    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_from = os.getenv("SMTP_FROM", "").strip()
    if not smtp_host or not smtp_from:
        return {"sent": False, "reason": "smtp_missing", "logged": True, "to": email}

    try:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = email
        msg.set_content(body)
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")
        use_tls = os.getenv("SMTP_TLS", "true").lower() == "true"
        with smtplib.SMTP(smtp_host, port, timeout=10) as smtp:
            if use_tls:
                smtp.starttls()
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
        return {"sent": True, "to": email}
    except Exception as e:
        logger.warning("task email failed task=%s: %s", db_task_id, e)
        return {"sent": False, "reason": str(e), "logged": True}


def on_task_terminal(db_task_id: str, *, status: str) -> dict[str, Any]:
    """Entry point after terminal status write."""
    task = _load_task_row(db_task_id)
    if not task:
        return {"ok": False, "reason": "missing"}
    # Prefer the status just written (row may lag in rare races).
    task["status"] = status or task.get("status")
    wh = deliver_webhook(db_task_id, task=task)
    if task.get("webhook_url"):
        try:
            persist_webhook_status(db_task_id, wh)
        except Exception as e:
            logger.warning("persist webhook status failed task=%s: %s", db_task_id, e)
    em = notify_task_email(db_task_id, task=task)
    return {"ok": True, "webhook": wh, "email": em}
