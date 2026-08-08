"""Phase 27 — staging acceptance scorecard, CLI --live/--strict, webhook deliver test."""
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_staging_acceptance_scorecard_shape():
    from app.services.go_live_ready import staging_acceptance_scorecard

    sc = staging_acceptance_scorecard()
    assert "acceptance_ok" in sc
    assert "score_pct" in sc
    assert "checks" in sc
    assert any(c["id"] == "revenue" for c in sc["checks"])
    assert any(c["id"] == "webhook_signature" for c in sc["checks"])


def test_staging_acceptance_strict_requires_live_kpi():
    from app.services.go_live_ready import staging_acceptance_scorecard

    sc = staging_acceptance_scorecard(last_smoke={
        "mode": "live_kpi_combined",
        "outframe_ok": 0,
        "details": [],
        "image_sample": {"outframe_ok": 0},
        "video_sample": {"outframe_ok": 0},
        "ts": "2026-01-01T00:00:00Z",
    }, strict=True)
    live = next(c for c in sc["checks"] if c["id"] == "live_kpi")
    assert live["status"] == "fail"
    assert sc["acceptance_ok"] is False


def test_staging_acceptance_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/staging-acceptance")
    assert r.status_code == 200
    assert r.json()["checks"]


def test_stripe_webhook_deliver_test_endpoint(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import settings

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_deliver_p27")

    c = TestClient(app)
    r = c.post("/api/v1/billing/stripe-webhook-deliver-test")
    assert r.status_code == 200
    body = r.json()
    assert body.get("delivery_ok") is True
    assert body.get("response", {}).get("received") is True


def test_stripe_webhook_ping_ignored_event(monkeypatch):
    from app.config import settings
    from app.services.stripe_ready import stripe_webhook_ping_payload, stripe_webhook_verify_payload

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_deliver_p27")
    payload, sig = stripe_webhook_ping_payload()
    assert payload and sig
    parsed = stripe_webhook_verify_payload(payload.encode("utf-8"), sig, "whsec_deliver_p27")
    assert parsed["type"] == "account.updated"


def test_staging_go_live_check_strict(monkeypatch):
    import importlib.util
    from pathlib import Path

    from app.config import settings

    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(settings, "STRIPE_API_KEY", "sk_test_p27")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_p27_strict")
    monkeypatch.setattr(settings, "STRIPE_PRICE_STARTER_MONTHLY", "price_p27")
    monkeypatch.setattr(settings, "STRIPE_SUCCESS_URL", "http://localhost:3000/billing/success")
    monkeypatch.setattr(settings, "STRIPE_CANCEL_URL", "http://localhost:3000/pricing")

    script = Path(__file__).resolve().parents[1] / "scripts" / "staging_go_live_check.py"
    spec = importlib.util.spec_from_file_location("staging_go_live_check_p27", script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    monkeypatch.setattr(sys, "argv", ["staging_go_live_check.py", "--strict", "--soft", "--json-only"])
    assert mod.main() == 0


def test_staging_go_live_check_live_skipped(monkeypatch, capsys):
    import importlib.util
    from pathlib import Path

    monkeypatch.delenv("MODEL_SMOKE_LIVE", raising=False)
    monkeypatch.delenv("MODEL_SMOKE_LIVE_VIDEO", raising=False)

    script = Path(__file__).resolve().parents[1] / "scripts" / "staging_go_live_check.py"
    spec = importlib.util.spec_from_file_location("staging_go_live_check_p27_live", script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with patch("app.services.model_smoke.run_live_kpi_smoke") as mock_live:
        spec.loader.exec_module(mod)
        monkeypatch.setattr(sys, "argv", ["staging_go_live_check.py", "--live", "--json-only"])
        mod.main()
    mock_live.assert_not_called()
    assert "skipped" in capsys.readouterr().err


def test_staging_go_live_check_live_runs(monkeypatch):
    import importlib.util
    from pathlib import Path

    monkeypatch.setenv("MODEL_SMOKE_LIVE", "1")

    script = Path(__file__).resolve().parents[1] / "scripts" / "staging_go_live_check.py"
    spec = importlib.util.spec_from_file_location("staging_go_live_check_p27_live2", script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with patch("app.services.model_smoke.run_live_kpi_smoke", return_value={"mode": "live_kpi_combined", "outframe_ok": 3, "details": []}) as mock_live:
        spec.loader.exec_module(mod)
        monkeypatch.setattr(sys, "argv", ["staging_go_live_check.py", "--live", "--json-only"])
        mod.main()
    mock_live.assert_called_once()


def test_staging_acceptance_e2e_spec_exists():
    from pathlib import Path
    assert (Path(__file__).resolve().parents[2] / "frontend" / "e2e" / "staging-go-live.spec.ts").is_file()
