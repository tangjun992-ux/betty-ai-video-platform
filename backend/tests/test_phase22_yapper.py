"""Phase 22 — OIDC staging, admin live smoke triggers, live KPI merge."""
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_oidc_staging_readiness_shape():
    from app.services.oidc_ready import oidc_staging_readiness

    st = oidc_staging_readiness()
    assert "staging_ready" in st
    assert len(st["checklist"]) >= 4
    assert st["callback_path"] == "/auth/callback"


def test_run_live_kpi_smoke_merges(monkeypatch):
    from app.services import model_smoke

    img = {"mode": "live_image_sample", "probed": 1, "ok": 1, "outframe_ok": 1, "failed": [], "details": [
        {"model_id": "gpt-image-2", "ok": True, "evidence": {"path": "live_image_gateway"}},
    ]}
    vid = {"mode": "live_video_sample", "probed": 2, "ok": 2, "outframe_ok": 2, "failed": [], "details": [
        {"model_id": "seedance-2.0-fast", "ok": True, "evidence": {"path": "live_video_gateway"}},
        {"model_id": "seedance-2.0", "ok": True, "evidence": {"path": "live_video_gateway"}},
    ]}
    saved = []

    monkeypatch.setattr(model_smoke, "run_live_image_sample", lambda **k: img)
    monkeypatch.setattr(model_smoke, "run_live_video_sample", lambda **k: vid)
    monkeypatch.setattr(model_smoke, "save_last_smoke", lambda r: saved.append(r))

    merged = model_smoke.run_live_kpi_smoke()
    assert merged["mode"] == "live_kpi_combined"
    assert merged["outframe_ok"] == 3
    assert len(saved) == 1


def test_live_kpi_from_combined_report():
    from app.services.go_live_ready import live_smoke_kpi

    kpi = live_smoke_kpi(last_smoke={
        "mode": "live_kpi_combined",
        "outframe_ok": 3,
        "image_sample": {"outframe_ok": 1},
        "video_sample": {"outframe_ok": 2},
        "details": [],
    })
    assert kpi["kpi_met"] is True
    assert kpi["video_outframe_ok"] >= 2
    assert kpi["image_outframe_ok"] >= 1


def test_readiness_includes_sso_staging():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/readiness")
    assert r.status_code == 200
    assert "staging" in r.json()["sso"]


def test_admin_live_kpi_smoke_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import require_admin

    fake_report = {
        "mode": "live_kpi_combined", "outframe_ok": 3, "probed": 3, "ok": 3, "failed": [],
        "image_sample": {"outframe_ok": 1}, "video_sample": {"outframe_ok": 2}, "details": [],
    }
    c = TestClient(app)
    app.dependency_overrides[require_admin] = lambda: AsyncMock(id=1)
    try:
        with patch("app.services.model_smoke.run_live_kpi_smoke", return_value=fake_report):
            r = c.post("/api/v1/admin/model-health/smoke/live-kpi")
        assert r.status_code == 200
        body = r.json()
        assert body["live_kpi"]["kpi_met"] is True
    finally:
        app.dependency_overrides.pop(require_admin, None)


def test_go_live_includes_sso_ready():
    from app.services.go_live_ready import go_live_readiness

    gl = go_live_readiness()
    assert "sso_ready" in gl
    assert "oidc" in gl
    assert "checklist" in gl["oidc"]
