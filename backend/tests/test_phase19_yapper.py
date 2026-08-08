"""Phase 19 — shelf 20, Stripe webhook, digest beat."""
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_active_shelf_20_imagen_4_ultra():
    from app.api.models_info import MODELS
    from app.services.model_catalog import GATEWAY_VERIFIED_IDS, catalog_integrity

    assert "imagen-4-ultra" in GATEWAY_VERIFIED_IDS
    m = next(x for x in MODELS if x.id == "imagen-4-ultra")
    assert m.status == "active"
    cat = catalog_integrity()
    assert cat["active_count"] >= 20


def test_readiness_active_target_20():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/readiness")
    assert r.status_code == 200
    assert r.json()["catalog"]["active_target"] == 20


def test_stripe_webhook_checkout_completed(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import settings

    monkeypatch.setattr(settings, "STRIPE_API_KEY", "sk_test_phase19")
    monkeypatch.setattr(settings, "STRIPE_PRICE_STARTER_MONTHLY", "price_starter_test")
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(settings, "STRIPE_SUCCESS_URL", "http://localhost:3000/billing/success")
    monkeypatch.setattr(settings, "STRIPE_CANCEL_URL", "http://localhost:3000/pricing")

    fake_session = SimpleNamespace(url="https://checkout.stripe.test/cs_test_p19")
    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.create.return_value = fake_session

    gid = f"p19-wh-{os.urandom(4).hex()}"
    with patch.dict(sys.modules, {"stripe": mock_stripe}):
        c = TestClient(app)
        ck = c.post("/api/v1/billing/checkout", headers={"X-Guest-Id": gid}, json={
            "kind": "pack", "id": "pack_mini", "cycle": "monthly", "quantity": 1,
        })
        assert ck.status_code == 200, ck.text
        order_no = ck.json()["order_no"]

        before = c.get("/api/v1/billing/summary", headers={"X-Guest-Id": gid}).json()

        wh = c.post(
            "/api/v1/billing/stripe/webhook",
            content=json.dumps({
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "metadata": {"order_no": order_no},
                        "customer_details": {"email": "p19@test.example"},
                    },
                },
            }),
            headers={"Content-Type": "application/json"},
        )
        assert wh.status_code == 200, wh.text
        body = wh.json()
        assert body.get("received") is True
        assert body.get("status") == "paid"
        assert body.get("order_no") == order_no

        after = c.get("/api/v1/billing/summary", headers={"X-Guest-Id": gid}).json()
        assert after.get("credits", 0) > before.get("credits", 0)


def test_send_webhook_failure_digest_no_failures():
    from app.services.ops_alerts import send_webhook_failure_digest

    with patch("app.services.task_hooks.webhook_failures_digest", return_value={
        "total": 0, "alert_sent_count": 0, "pending_alert": 0,
        "by_status": {}, "top_reasons": [], "sample_task_ids": [],
    }):
        r = send_webhook_failure_digest()
    assert r["sent"] is False
    assert r["reason"] == "no_failures"


def test_send_webhook_failure_digest_posts(monkeypatch):
    from app.services import ops_alerts

    monkeypatch.setenv("OPS_ALERT_WEBHOOK_URL", "https://hooks.slack.test/ops")
    digest = {
        "total": 2, "alert_sent_count": 1, "pending_alert": 1,
        "by_status": {"completed": 2}, "top_reasons": [{"reason": "HTTP 500", "count": 2}],
        "sample_task_ids": ["t1"],
    }
    calls = []

    class FakeResp:
        status_code = 200

    with patch("app.services.task_hooks.webhook_failures_digest", return_value=digest), \
         patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.side_effect = lambda *a, **k: calls.append(1) or FakeResp()
        r = ops_alerts.send_webhook_failure_digest()
    assert r["sent"] is True
    assert len(calls) == 1


def test_webhook_digest_beat_registered_and_gated(monkeypatch):
    from celery_app import app
    from app.tasks.health_tasks import webhook_failure_digest_hourly

    app.loader.import_default_modules()
    assert "app.tasks.health_tasks.webhook_failure_digest_hourly" in app.tasks
    beat = app.conf.beat_schedule or {}
    assert "ops-webhook-failure-digest-hourly" in beat
    assert beat["ops-webhook-failure-digest-hourly"]["schedule"] == 3600.0

    monkeypatch.delenv("OPS_WEBHOOK_DIGEST_HOURLY", raising=False)
    monkeypatch.delenv("OPS_ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    report = webhook_failure_digest_hourly()
    assert report.get("skipped") is True


def test_admin_digest_send_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import require_admin

    c = TestClient(app)
    app.dependency_overrides[require_admin] = lambda: AsyncMock(id=1)
    try:
        with patch("app.services.ops_alerts.send_webhook_failure_digest", return_value={
            "sent": False, "reason": "no_failures", "digest": {"total": 0},
        }):
            r = c.post("/api/v1/admin/model-health/webhook-failures/digest/send")
        assert r.status_code == 200
        assert r.json()["reason"] == "no_failures"
    finally:
        app.dependency_overrides.pop(require_admin, None)
