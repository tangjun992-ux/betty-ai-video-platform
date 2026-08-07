"""Phase 15 — webhook retry, Stripe checkout readiness, task detail E2E."""
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_stripe_checkout_readiness_dev_grant():
    from app.services.stripe_ready import stripe_checkout_readiness

    ck = stripe_checkout_readiness()
    assert ck["checkout_ready"] is True
    assert ck["mode"] in ("dev_grant", "stripe", "blocked")


def test_readiness_includes_stripe_checkout():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/readiness")
    assert r.status_code == 200
    assert "checkout" in r.json()["stripe"]
    assert r.json()["stripe"]["checkout"]["checkout_ready"] is True


def test_retry_webhook_delivery_success(monkeypatch):
    from app.services import task_hooks

    task = {
        "task_id": "wh-retry-1",
        "status": "completed",
        "webhook_url": "https://hooks.example.com/cb",
        "media_type": "image",
        "selected_model": "nano-banana",
        "prompt": "p",
        "results": [],
        "error_message": None,
        "actual_cost": 1,
        "estimated_cost": 1,
        "user_id": 1,
    }
    monkeypatch.setattr(task_hooks, "_load_task_row", lambda tid: task if tid == "wh-retry-1" else None)
    monkeypatch.setattr(task_hooks, "deliver_webhook", lambda tid, task=None: {
        "delivered": True, "status_code": 200, "attempts": 1,
    })
    persisted = []
    monkeypatch.setattr(task_hooks, "persist_webhook_status", lambda tid, d: persisted.append((tid, d)))

    r = task_hooks.retry_webhook_delivery("wh-retry-1")
    assert r["ok"] is True
    assert r["delivered"] is True
    assert persisted[0][0] == "wh-retry-1"


def test_retry_webhook_rejects_non_terminal():
    from app.services import task_hooks

    with patch.object(task_hooks, "_load_task_row", return_value={
        "task_id": "x", "status": "generating", "webhook_url": "https://h.test/c",
    }):
        r = task_hooks.retry_webhook_delivery("x")
    assert r["ok"] is False
    assert r["reason"] == "task_not_terminal"


def test_retry_failed_webhooks_batch(monkeypatch):
    from app.services import task_hooks

    monkeypatch.setattr(task_hooks, "list_failed_webhooks", lambda **kw: [
        {"task_id": "a"}, {"task_id": "b"},
    ])
    calls = []
    monkeypatch.setattr(task_hooks, "retry_webhook_delivery", lambda tid: calls.append(tid) or {
        "ok": tid == "a", "delivered": tid == "a", "task_id": tid,
    })
    r = task_hooks.retry_failed_webhooks(limit=5)
    assert r["attempted"] == 2
    assert r["delivered"] == 1
    assert calls == ["a", "b"]


def test_admin_webhook_retry_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import require_admin

    c = TestClient(app)
    app.dependency_overrides[require_admin] = lambda: AsyncMock(id=1)
    try:
        with patch("app.services.task_hooks.retry_webhook_delivery", return_value={
            "ok": True, "delivered": True, "task_id": "t1", "attempts": 1,
        }), patch("app.services.audit.record_audit", new_callable=AsyncMock):
            r = c.post("/api/v1/admin/model-health/webhook-failures/t1/retry")
        assert r.status_code == 200
        assert r.json()["delivered"] is True
    finally:
        app.dependency_overrides.pop(require_admin, None)


def test_stripe_checkout_readiness_no_api_key(monkeypatch):
    from app.services import stripe_ready

    monkeypatch.delenv("STRIPE_API_KEY", raising=False)
    monkeypatch.setenv("ENV", "development")
    ck = stripe_ready.stripe_checkout_readiness()
    assert ck["mode"] == "dev_grant"
    assert ck["dev_grant"] is True
    assert ck["checkout_ready"] is True


def test_e2e_helpers_typescript_exists():
    from pathlib import Path
    assert (Path(__file__).resolve().parents[2] / "frontend" / "e2e" / "tasks.spec.ts").is_file()
