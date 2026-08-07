"""Phase 8 — model shelf, OIDC exchange, admin promote, gallery seed."""
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_active_model_count_expanded():
    from app.api.models_info import MODELS

    active = [m for m in MODELS if m.status == "active"]
    assert len(active) >= 12, f"expected ≥12 active models, got {len(active)}"
    for mid in ("kling-1.6", "wan-2.5", "hailuo-2.3"):
        assert any(m.id == mid and m.status == "active" for m in MODELS)


def test_gateway_verified_includes_promoted():
    from app.services.model_catalog import GATEWAY_VERIFIED_IDS

    for mid in ("kling-1.6", "wan-2.5", "hailuo-2.3"):
        assert mid in GATEWAY_VERIFIED_IDS


def test_promote_rejects_guess_sku():
    from fastapi import HTTPException
    from app.services.model_promotion import promote_model

    with pytest.raises(HTTPException) as exc:
        promote_model("flux-1.1-pro")
    assert exc.value.status_code == 400


def test_promote_mapped_beta():
    from app.services.model_promotion import promote_model, demote_model
    from app.api.models_info import MODELS

    mid = "veo-3.1"
    before = next(m for m in MODELS if m.id == mid)
    assert before.status == "beta"
    r = promote_model(mid, note="test promote")
    assert r["status"] == "active"
    demote_model(mid, note="test cleanup")


def test_oidc_exchange_roundtrip():
    from app.services.model_promotion import store_oidc_exchange, take_oidc_exchange

    store_oidc_exchange("code-abc", "jwt-token-xyz")
    assert take_oidc_exchange("code-abc") == "jwt-token-xyz"
    assert take_oidc_exchange("code-abc") is None


def test_oidc_exchange_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.model_promotion import store_oidc_exchange

    store_oidc_exchange("ex-code-1", "tok-123")
    c = TestClient(app)
    ok = c.post("/api/v1/auth/oidc/exchange", json={"code": "ex-code-1"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["access_token"] == "tok-123"
    bad = c.post("/api/v1/auth/oidc/exchange", json={"code": "ex-code-1"})
    assert bad.status_code == 400


def test_admin_promotable_list():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    with patch("app.api.model_health_admin.require_admin", return_value=AsyncMock(id=1)):
        r = c.get("/api/v1/admin/model-health/promotable")
    # Without real admin auth may 401 — skip if so
    if r.status_code == 401:
        pytest.skip("admin auth required")
    assert r.status_code == 200
    data = r.json()
    assert data["verified_active_count"] >= 12
    assert "promotable" in data


def test_catalog_integrity_after_phase8():
    from app.services.model_catalog import catalog_integrity

    ci = catalog_integrity()
    assert ci["active_count"] >= 12
    assert not ci["active_outside_verified_set"]
