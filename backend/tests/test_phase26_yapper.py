"""Phase 26 — Stripe webhook signature verify, self-test, signed E2E."""
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_stripe_webhook_sign_and_verify_roundtrip():
    from app.services.stripe_ready import stripe_webhook_sign_payload, stripe_webhook_verify_payload

    secret = "whsec_test_phase26_roundtrip"
    payload = json.dumps({"type": "checkout.session.completed", "data": {"object": {}}})
    sig = stripe_webhook_sign_payload(payload, secret)
    parsed = stripe_webhook_verify_payload(payload.encode("utf-8"), sig, secret)
    assert parsed["type"] == "checkout.session.completed"


def test_stripe_webhook_verify_rejects_bad_signature():
    from app.services.stripe_ready import stripe_webhook_verify_payload
    import time

    secret = "whsec_test_phase26_bad"
    payload = b'{"type":"checkout.session.completed"}'
    ts = int(time.time())
    with pytest.raises(ValueError, match="signature mismatch"):
        stripe_webhook_verify_payload(payload, f"t={ts},v1=deadbeef", secret)


def test_stripe_webhook_signature_self_test_ok(monkeypatch):
    from app.config import settings
    from app.services.stripe_ready import stripe_webhook_signature_self_test

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_self_test_ok")
    r = stripe_webhook_signature_self_test()
    assert r["configured"] is True
    assert r["self_test_ok"] is True


def test_stripe_webhook_self_test_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/billing/stripe-webhook-self-test")
    assert r.status_code == 200
    assert "self_test_ok" in r.json()


def test_stripe_webhook_signed_checkout_completed(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import settings
    from app.services.stripe_ready import stripe_webhook_sign_payload

    monkeypatch.setattr(settings, "STRIPE_API_KEY", "sk_test_phase26")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_phase26_signed")
    monkeypatch.setattr(settings, "STRIPE_PRICE_STARTER_MONTHLY", "price_starter_test")
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(settings, "STRIPE_SUCCESS_URL", "http://localhost:3000/billing/success")
    monkeypatch.setattr(settings, "STRIPE_CANCEL_URL", "http://localhost:3000/pricing")

    fake_session = SimpleNamespace(url="https://checkout.stripe.test/cs_test_p26")
    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.create.return_value = fake_session

    gid = f"p26-wh-{os.urandom(4).hex()}"
    with patch.dict(sys.modules, {"stripe": mock_stripe}):
        c = TestClient(app)
        ck = c.post("/api/v1/billing/checkout", headers={"X-Guest-Id": gid}, json={
            "kind": "pack", "id": "pack_mini", "cycle": "monthly", "quantity": 1,
        })
        assert ck.status_code == 200, ck.text
        order_no = ck.json()["order_no"]
        before = c.get("/api/v1/billing/summary", headers={"X-Guest-Id": gid}).json()

        body = json.dumps({
            "id": "evt_p26_checkout",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"order_no": order_no},
                    "customer_details": {"email": "p26@test.example"},
                },
            },
        })
        sig = stripe_webhook_sign_payload(body, "whsec_phase26_signed")
        wh = c.post(
            "/api/v1/billing/stripe/webhook",
            content=body,
            headers={"Content-Type": "application/json", "Stripe-Signature": sig},
        )
        assert wh.status_code == 200, wh.text
        assert wh.json().get("status") == "paid"

        after = c.get("/api/v1/billing/summary", headers={"X-Guest-Id": gid}).json()
        assert after.get("credits", 0) > before.get("credits", 0)


def test_stripe_webhook_rejects_unsigned_when_secret_set(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import settings

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_phase26_reject")
    monkeypatch.setattr(settings, "ENV", "development")

    c = TestClient(app)
    r = c.post(
        "/api/v1/billing/stripe/webhook",
        content=json.dumps({"type": "checkout.session.completed", "data": {"object": {}}}),
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 400


def test_staging_includes_signature_self_test(monkeypatch):
    from app.config import settings
    from app.services.stripe_ready import stripe_staging_readiness

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_staging_p26")
    st = stripe_staging_readiness()
    assert "webhook_signature_self_test" in st
    assert st["webhook_signature_self_test"]["self_test_ok"] is True


def test_ci_require_webhook_script(monkeypatch):
    import importlib.util
    from pathlib import Path

    from app.config import settings

    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(settings, "STRIPE_API_KEY", "sk_test_p26")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_p26_require")
    monkeypatch.setattr(settings, "STRIPE_PRICE_STARTER_MONTHLY", "price_p26")
    monkeypatch.setattr(settings, "STRIPE_SUCCESS_URL", "http://localhost:3000/billing/success")
    monkeypatch.setattr(settings, "STRIPE_CANCEL_URL", "http://localhost:3000/pricing")

    script = Path(__file__).resolve().parents[1] / "scripts" / "staging_go_live_check.py"
    spec = importlib.util.spec_from_file_location("staging_go_live_check_p26", script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    monkeypatch.setattr(sys, "argv", ["staging_go_live_check.py", "--require-webhook", "--soft"])
    assert mod.main() == 0
