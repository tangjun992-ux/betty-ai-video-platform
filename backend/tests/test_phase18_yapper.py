"""Phase 18 — shelf 19, Stripe test checkout, webhook digest, variants E2E."""
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_active_shelf_19_imagen_4_fast():
    from app.api.models_info import MODELS
    from app.services.model_catalog import GATEWAY_VERIFIED_IDS, catalog_integrity

    assert "imagen-4-fast" in GATEWAY_VERIFIED_IDS
    m = next(x for x in MODELS if x.id == "imagen-4-fast")
    assert m.status == "active"
    cat = catalog_integrity()
    assert cat["active_count"] >= 19


def test_readiness_active_target_19():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/readiness")
    assert r.status_code == 200
    assert r.json()["catalog"]["active_target"] == 19


def test_ops_alerts_digest_enabled():
    from app.services.ops_alerts import ops_alerts_status

    st = ops_alerts_status()
    assert st["digest_enabled"] is True


def test_webhook_failures_digest_shape(tmp_path, monkeypatch):
    from app.services import task_hooks
    from sqlalchemy import create_engine, text

    db_path = tmp_path / "digest.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
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
            VALUES ('d1', 1, 'completed', 'p', 'image', 'https://cb.test/h', :p, datetime('now'), datetime('now'))
        """), {"p": '{"webhook": {"delivered": false, "reason": "HTTP 500", "attempts": 3, "alert_sent": true}}'})

    with patch.object(task_hooks, "_sync_engine", return_value=engine):
        digest = task_hooks.webhook_failures_digest(limit=10)
    assert digest["total"] == 1
    assert digest["alert_sent_count"] == 1
    assert digest["pending_alert"] == 0
    assert digest["top_reasons"][0]["reason"] == "HTTP 500"


def test_stripe_test_mode_checkout(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import settings

    monkeypatch.setattr(settings, "STRIPE_API_KEY", "sk_test_phase18")
    monkeypatch.setattr(settings, "STRIPE_PRICE_STARTER_MONTHLY", "price_starter_test")
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(settings, "STRIPE_SUCCESS_URL", "http://localhost:3000/billing/success")
    monkeypatch.setattr(settings, "STRIPE_CANCEL_URL", "http://localhost:3000/pricing")

    fake_session = SimpleNamespace(url="https://checkout.stripe.test/cs_test_abc")
    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.create.return_value = fake_session

    with patch.dict(sys.modules, {"stripe": mock_stripe}):
        c = TestClient(app)
        gid = f"p18-stripe-{os.urandom(4).hex()}"
        r = c.post("/api/v1/billing/checkout", headers={"X-Guest-Id": gid}, json={
            "kind": "plan", "id": "starter", "cycle": "monthly", "quantity": 1,
        })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("mode") == "stripe"
    assert body.get("checkout_url") == "https://checkout.stripe.test/cs_test_abc"
    assert body.get("checkout_mode") == "subscription"
    mock_stripe.checkout.Session.create.assert_called_once()


def test_admin_webhook_digest_endpoint():
    from unittest.mock import AsyncMock

    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import require_admin

    c = TestClient(app)
    app.dependency_overrides[require_admin] = lambda: AsyncMock(id=1)
    try:
        with patch("app.services.task_hooks.webhook_failures_digest", return_value={
            "total": 0, "alert_sent_count": 0, "pending_alert": 0,
            "by_status": {}, "top_reasons": [], "sample_task_ids": [],
        }):
            r = c.get("/api/v1/admin/model-health/webhook-failures/digest")
        assert r.status_code == 200
        assert r.json()["total"] == 0
    finally:
        app.dependency_overrides.pop(require_admin, None)


def test_agent_variants_e2e_spec_exists():
    from pathlib import Path
    assert (Path(__file__).resolve().parents[2] / "frontend" / "e2e" / "agent-variants.spec.ts").is_file()
