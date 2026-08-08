"""Phase 25 — OIDC discovery probe, CI soft gate, require-webhook."""
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_oidc_discovery_probe_unconfigured():
    from app.services.oidc_ready import oidc_discovery_probe

    with patch.dict(os.environ, {}, clear=True):
        for k in ("OIDC_ISSUER", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET", "OIDC_REDIRECT_URI"):
            os.environ.pop(k, None)
        probe = oidc_discovery_probe()
    assert probe["configured"] is False
    assert probe["probe_ok"] is False
    assert "OIDC_ISSUER" in (probe.get("error") or "")


def test_oidc_discovery_probe_success(monkeypatch):
    from app.services.oidc_ready import oidc_discovery_probe

    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example.com")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "issuer": "https://idp.example.com",
        "authorization_endpoint": "https://idp.example.com/authorize",
        "token_endpoint": "https://idp.example.com/token",
        "userinfo_endpoint": "https://idp.example.com/userinfo",
        "jwks_uri": "https://idp.example.com/jwks",
    }
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp
    with patch("app.services.oidc_ready.httpx.Client", return_value=mock_client):
        probe = oidc_discovery_probe()
    assert probe["probe_ok"] is True
    assert probe["discovery_ok"] is True
    assert probe["endpoints"]["token_endpoint"] == "https://idp.example.com/token"


def test_oidc_discovery_check_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/auth/oidc/discovery-check")
    assert r.status_code == 200
    body = r.json()
    assert "probe_ok" in body
    assert "staging" in body
    assert "checklist" in body["staging"]


def test_staging_go_live_soft_gate(monkeypatch):
    import importlib.util
    from pathlib import Path

    from app.config import settings

    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(settings, "STRIPE_API_KEY", "sk_test_p25")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_p25_soft")
    monkeypatch.setattr(settings, "STRIPE_PRICE_STARTER_MONTHLY", "price_p25")
    monkeypatch.setattr(settings, "STRIPE_SUCCESS_URL", "http://localhost:3000/billing/success")
    monkeypatch.setattr(settings, "STRIPE_CANCEL_URL", "http://localhost:3000/pricing")

    script = Path(__file__).resolve().parents[1] / "scripts" / "staging_go_live_check.py"
    spec = importlib.util.spec_from_file_location("staging_go_live_check_p25", script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    monkeypatch.setattr(sys, "argv", ["staging_go_live_check.py", "--soft", "--json-only"])
    assert mod.main() == 0


def test_staging_require_webhook_fails(monkeypatch):
    import importlib.util
    from pathlib import Path

    from app.config import settings

    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setenv("STRIPE_API_KEY", "sk_test_p25")
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)

    script = Path(__file__).resolve().parents[1] / "scripts" / "staging_go_live_check.py"
    spec = importlib.util.spec_from_file_location("staging_go_live_check_p25_wh", script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with patch("app.services.go_live_ready.staging_go_live_report") as mock_report:
        mock_report.return_value = {
            "go_live_ok": True,
            "revenue_ready": True,
            "media_ready": True,
            "stripe": {"webhook_config": {"setup_ok": False, "blockers": ["missing"]}},
            "env": "development",
            "summary": {"blocker_count": 0},
            "next_steps": [],
        }
        spec.loader.exec_module(mod)
        monkeypatch.setattr(sys, "argv", ["staging_go_live_check.py", "--require-webhook"])
        assert mod.main() == 1


def test_staging_report_oidc_discovery_hint(monkeypatch):
    from app.services.go_live_ready import staging_go_live_report

    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example.com")
    monkeypatch.setenv("OIDC_CLIENT_ID", "cid")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "sec")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "http://localhost:3000/auth/callback")
    r = staging_go_live_report()
    steps = r.get("next_steps") or []
    assert any("Discovery" in s or "discovery" in s.lower() for s in steps)
