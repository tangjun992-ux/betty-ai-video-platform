"""Phase 16 — ops webhook alerts, auto-promote readiness, Celery E2E chain."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_ops_alerts_status_unconfigured():
    from app.services.ops_alerts import alert_webhook_url, ops_alerts_status

    assert alert_webhook_url() == "" or isinstance(alert_webhook_url(), str)
    st = ops_alerts_status()
    assert st["webhook_failure_alerts"] is False or st["webhook_failure_alerts"] is True


def test_alert_webhook_failure_posts(monkeypatch):
    from app.services import ops_alerts

    monkeypatch.setenv("OPS_ALERT_WEBHOOK_URL", "https://hooks.slack.test/ops")
    posted = {}

    class FakeResp:
        status_code = 200

    class FakeClient:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def post(self, url, json=None):
            posted["url"] = url
            posted["json"] = json
            return FakeResp()

    monkeypatch.setattr(ops_alerts.httpx, "Client", FakeClient)
    r = ops_alerts.alert_webhook_failure("tid-1", {"delivered": False, "reason": "HTTP 500", "attempts": 3}, task={
        "task_id": "tid-1", "status": "completed", "webhook_url": "https://cb.test/h",
    })
    assert r["sent"] is True
    assert "tid-1" in posted["json"]["text"]


def test_persist_webhook_triggers_alert_on_failure(monkeypatch, tmp_path):
    from app.services import task_hooks

    db_path = tmp_path / "alert.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("OPS_ALERT_WEBHOOK_URL", "https://hooks.slack.test/ops")

    from sqlalchemy import create_engine, text

    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                task_id TEXT, user_id INTEGER, status TEXT, prompt TEXT, media_type TEXT,
                webhook_url TEXT, parameters TEXT, results TEXT, error_message TEXT,
                selected_model TEXT, actual_cost REAL, estimated_cost REAL,
                created_at TEXT, updated_at TEXT
            )
        """))
        conn.execute(text("""
            INSERT INTO tasks (task_id, user_id, status, prompt, media_type, webhook_url, parameters, created_at, updated_at)
            VALUES ('alert-t1', 1, 'completed', 'p', 'image', 'https://cb.test/h', '{}', datetime('now'), datetime('now'))
        """))

    alerts = []
    with patch.object(task_hooks, "_sync_engine", return_value=engine), \
         patch("app.services.ops_alerts.alert_webhook_failure", side_effect=lambda *a, **k: alerts.append(1) or {"sent": True}):
        task_hooks.persist_webhook_status("alert-t1", {"delivered": False, "reason": "timeout", "attempts": 3})
    assert len(alerts) == 1


def test_readiness_includes_ops_alerts_and_auto_promote():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/readiness")
    assert r.status_code == 200
    data = r.json()
    assert "ops_alerts" in data
    assert "last_auto_promote" in data["smoke"]
    assert "promoted" in data["smoke"]["last_auto_promote"]


def test_last_auto_promote_summary_from_smoke():
    from app.api.system import _last_auto_promote_summary

    s = _last_auto_promote_summary({
        "auto_promote": {"promoted": ["veo-3.1"], "count": 1, "skipped": False},
    })
    assert s["count"] == 1
    assert s["promoted"] == ["veo-3.1"]


def test_e2e_tasks_spec_has_celery_chain():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[2] / "frontend" / "e2e" / "tasks.spec.ts").read_text(encoding="utf-8")
    assert "Celery 全链路" in text
    assert "pollTaskUntilDone" in text
