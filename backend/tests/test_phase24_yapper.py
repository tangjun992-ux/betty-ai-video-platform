"""Phase 24 — Stripe webhook check, CI staging gate."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_stripe_webhook_staging_check_shape():
    from app.services.stripe_ready import stripe_webhook_staging_check

    wh = stripe_webhook_staging_check()
    assert wh["endpoint_path"] == "/api/v1/billing/stripe/webhook"
    assert "checkout.session.completed" in wh["required_events"]
    assert "invoice.paid" in wh["required_events"]
    assert "dashboard_steps" in wh


def test_stripe_webhook_secret_format(monkeypatch):
    from app.config import settings
    from app.services.stripe_ready import stripe_webhook_staging_check

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_phase24")
    monkeypatch.setattr(settings, "STRIPE_API_KEY", "sk_test_phase24")
    wh = stripe_webhook_staging_check()
    assert wh["setup_ok"] is True
    assert wh["webhook_secret_format_ok"] is True
    assert wh["test_mode_api_key"] is True


def test_stripe_staging_includes_webhook_config():
    from app.services.stripe_ready import stripe_staging_readiness

    st = stripe_staging_readiness()
    assert "webhook_config" in st
    assert st["webhook_endpoint"] == "/api/v1/billing/stripe/webhook"


def test_billing_stripe_webhook_check_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/billing/stripe-webhook-check")
    assert r.status_code == 200
    assert r.json()["endpoint_path"] == "/api/v1/billing/stripe/webhook"


def test_staging_report_includes_webhook_config():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/staging-report")
    assert r.status_code == 200
    wh = r.json().get("stripe", {}).get("webhook_config")
    assert wh is not None
    assert wh.get("endpoint_path")


def test_ci_staging_script_json_structure():
    import json
    import subprocess
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / "scripts" / "staging_go_live_check.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--json-only"],
        capture_output=True,
        text=True,
        cwd=str(script.parents[1]),
        env={**os.environ, "ENV": "test"},
    )
    assert proc.returncode in (0, 1)
    data = json.loads(proc.stdout)
    assert data["stripe"]["webhook_config"]["endpoint_path"] == "/api/v1/billing/stripe/webhook"
