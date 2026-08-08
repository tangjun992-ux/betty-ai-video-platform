"""Phase 21 — storage staging, live KPI, go-live readiness."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_storage_staging_readiness_shape():
    from app.services.storage_ready import storage_staging_readiness

    st = storage_staging_readiness()
    assert "staging_ready" in st
    assert len(st["checklist"]) >= 3
    assert "public_media_base" in st


def test_live_smoke_kpi_no_report():
    from app.services.go_live_ready import live_smoke_kpi

    kpi = live_smoke_kpi(last_smoke=None)
    assert kpi["available"] is False
    assert kpi["kpi_met"] is False
    assert kpi["targets"]["video_outframe_min"] == 2


def test_live_smoke_kpi_met():
    from app.services.go_live_ready import live_smoke_kpi

    kpi = live_smoke_kpi(last_smoke={
        "mode": "live_video_sample",
        "outframe_ok": 2,
        "ts": "2026-01-01",
        "details": [
            {"ok": True, "path": "live_video", "model_id": "seedance-2.0-fast"},
            {"ok": True, "path": "live_video", "model_id": "seedance-2.0"},
            {"ok": True, "path": "live_image", "model_id": "gpt-image-2"},
        ],
    })
    assert kpi["kpi_met"] is True
    assert kpi["video_outframe_ok"] >= 2
    assert kpi["image_outframe_ok"] >= 1


def test_go_live_readiness_aggregate():
    from app.services.go_live_ready import go_live_readiness

    gl = go_live_readiness(last_smoke={
        "mode": "live_video_sample",
        "outframe_ok": 2,
        "details": [
            {"ok": True, "path": "live_video", "model_id": "a"},
            {"ok": True, "path": "live_video", "model_id": "b"},
            {"ok": True, "path": "live_image", "model_id": "c"},
        ],
    })
    assert "go_live_ok" in gl
    assert "stripe" in gl
    assert "storage" in gl
    assert "live_kpi" in gl


def test_go_live_readiness_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/go-live-readiness")
    assert r.status_code == 200
    body = r.json()
    assert "go_live_ok" in body
    assert "revenue_ready" in body


def test_readiness_includes_go_live_and_storage_staging():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/readiness")
    assert r.status_code == 200
    data = r.json()
    assert "go_live" in data
    assert "live_kpi" in data
    assert "staging" in data["storage"]
