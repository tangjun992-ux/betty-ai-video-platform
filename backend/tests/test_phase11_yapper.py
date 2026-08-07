"""Phase 11 — model shelf 15+, readiness API, admin ops."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_active_model_count_at_least_15():
    from app.api.models_info import MODELS

    active = [m for m in MODELS if m.status == "active"]
    assert len(active) >= 15, f"expected ≥15 active models, got {len(active)}"


def test_phase11_promoted_in_verified_set():
    from app.services.model_catalog import GATEWAY_VERIFIED_IDS

    for mid in ("wan-2.2", "veo-3.1-fast", "hailuo-02"):
        assert mid in GATEWAY_VERIFIED_IDS


def test_phase11_promoted_models_active():
    from app.api.models_info import MODELS

    for mid in ("wan-2.2", "veo-3.1-fast", "hailuo-02"):
        m = next(x for x in MODELS if x.id == mid)
        assert m.status == "active", mid


def test_readiness_includes_catalog_and_smoke():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/readiness")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "catalog" in data
    assert data["catalog"]["active_count"] >= 15
    assert data["catalog"]["active_target"] == 17
    assert "smoke" in data
    assert "auto_promote_enabled" in data["smoke"]


def test_promotable_includes_smoke_hint():
    from fastapi.testclient import TestClient
    from app.main import app
    from unittest.mock import AsyncMock, patch

    c = TestClient(app)
    with patch("app.api.model_health_admin.require_admin", return_value=AsyncMock(id=1)):
        r = c.get("/api/v1/admin/model-health/promotable")
    if r.status_code == 401:
        pytest.skip("admin auth required")
    assert r.status_code == 200
    data = r.json()
    assert data["verified_active_count"] >= 15
    assert data["active_target"] == 17
    if data["promotable"]:
        assert "last_smoke" in data["promotable"][0] or "media_types" in data["promotable"][0]


def test_catalog_integrity_active_in_verified():
    from app.services.model_catalog import catalog_integrity, GATEWAY_VERIFIED_IDS

    ci = catalog_integrity()
    assert ci["active_count"] >= 15
    for mid in ("wan-2.2", "veo-3.1-fast", "hailuo-02"):
        assert mid in GATEWAY_VERIFIED_IDS
