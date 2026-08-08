"""Phase 28 — staging runbook, Stripe CLI guide."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_stripe_cli_webhook_guide_shape():
    from app.services.stripe_ready import stripe_cli_webhook_guide

    g = stripe_cli_webhook_guide()
    assert "/api/v1/billing/stripe/webhook" in g["forward_url"]
    assert "stripe listen" in g["listen_command"]
    assert "checkout.session.completed" in g["listen_command"]
    assert len(g["local_dev_steps"]) >= 4


def test_stripe_cli_guide_https():
    from app.services.stripe_ready import stripe_cli_webhook_guide

    g = stripe_cli_webhook_guide(host="staging.example.com", use_https=True)
    assert g["forward_url"].startswith("https://staging.example.com")


def test_staging_runbook_shape():
    from app.services.go_live_ready import staging_runbook

    rb = staging_runbook()
    assert "steps" in rb
    assert rb["steps_total"] >= 6
    ids = {s["id"] for s in rb["steps"]}
    assert "stripe_bootstrap" in ids
    assert "final_acceptance" in ids
    assert "stripe_cli" in rb


def test_staging_runbook_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/staging-runbook")
    assert r.status_code == 200
    assert r.json()["steps"]


def test_billing_stripe_cli_guide_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/billing/stripe-cli-guide")
    assert r.status_code == 200
    assert r.json()["listen_command"]


def test_staging_runbook_script_json():
    import subprocess

    script = Path(__file__).resolve().parents[1] / "scripts" / "staging_runbook.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--json-only"],
        capture_output=True,
        text=True,
        cwd=str(script.parents[1]),
    )
    assert proc.returncode in (0, 1)
    data = json.loads(proc.stdout)
    assert data["steps_total"] >= 6
    assert data["stripe_cli"]["forward_url"]


def test_staging_report_includes_runbook_command():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/staging-report")
    assert r.status_code == 200
    assert "staging_runbook" in (r.json().get("commands") or {})

def test_runbook_step_statuses_valid():
    from app.services.go_live_ready import staging_runbook

    rb = staging_runbook()
    valid = {"done", "pending", "skipped"}
    for step in rb["steps"]:
        assert step["status"] in valid
        assert step.get("commands")
