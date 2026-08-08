"""Phase 29 — staging env audit, strict acceptance fix."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_staging_env_audit_shape():
    from app.services.staging_env import staging_env_audit

    audit = staging_env_audit()
    assert "missing_required" in audit
    assert "groups" in audit
    assert "stripe" in audit["groups"]


def test_staging_env_audit_detects_missing():
    from app.services.staging_env import staging_env_audit

    audit = staging_env_audit()
    # Without injected stripe env, should list stripe keys
    if not os.getenv("STRIPE_API_KEY"):
        assert "STRIPE_API_KEY" in audit["missing_required"]


def test_staging_env_audit_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/staging-env-audit")
    assert r.status_code == 200
    assert "items" in r.json()


def test_strict_acceptance_ok_without_live_kpi(monkeypatch):
    from app.config import settings
    from app.services.go_live_ready import staging_acceptance_scorecard

    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(settings, "STRIPE_API_KEY", "sk_test_p29")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_p29_strict")
    monkeypatch.setattr(settings, "STRIPE_PRICE_STARTER_MONTHLY", "price_p29")
    monkeypatch.setattr(settings, "STRIPE_SUCCESS_URL", "http://localhost:3000/billing/success")
    monkeypatch.setattr(settings, "STRIPE_CANCEL_URL", "http://localhost:3000/pricing")

    sc = staging_acceptance_scorecard(strict=True)
    live = next(c for c in sc["checks"] if c["id"] == "live_kpi")
    assert live["status"] == "skip"
    assert live["required"] is False
    assert sc["acceptance_ok"] is True


def test_runbook_includes_env_audit():
    from app.services.go_live_ready import staging_runbook

    rb = staging_runbook()
    assert "env_audit" in rb
    assert rb["env_audit"].get("groups")


def test_staging_env_audit_script():
    script = Path(__file__).resolve().parents[1] / "scripts" / "staging_env_audit.py"
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(script), "--json-only"],
        capture_output=True,
        text=True,
        cwd=str(script.parents[1]),
    )
    assert proc.returncode in (0, 1)
    data = json.loads(proc.stdout)
    assert "missing_required" in data


def test_env_staging_example_exists():
    assert (Path(__file__).resolve().parents[1] / ".env.staging.example").is_file()
