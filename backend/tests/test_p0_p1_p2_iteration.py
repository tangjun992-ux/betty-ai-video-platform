"""P0/P1/P2: router pool, quarantine TTL, lab fold, fixture harness."""
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_auto_router_covers_all_active():
    from app.router import MODEL_STYLE_PREFS, PromptRouter, PromptAnalysis, MediaType, QualityTier
    from app.services.model_catalog import GATEWAY_VERIFIED_IDS

    pooled = set(MODEL_STYLE_PREFS["image"]) | set(MODEL_STYLE_PREFS["video"])
    assert GATEWAY_VERIFIED_IDS <= pooled

    router = PromptRouter()
    analysis = PromptAnalysis(
        media_type=MediaType.IMAGE,
        quality=QualityTier.BALANCED,
        styles=["realistic"],
        complexity="simple",
    )
    with patch("app.router.model_health.is_circuit_open", return_value=False), \
         patch("app.router.model_health.is_quarantined", return_value=False), \
         patch("app.router.model_health.score", return_value=100.0):
        best = router.select_model(analysis, user_model="auto")
    assert best.model_id in MODEL_STYLE_PREFS["image"]


def test_router_skips_quarantined():
    from app.router import PromptRouter, PromptAnalysis, MediaType, QualityTier, MODEL_STYLE_PREFS

    router = PromptRouter()
    analysis = PromptAnalysis(
        media_type=MediaType.IMAGE,
        quality=QualityTier.BALANCED,
        styles=["realistic"],
        complexity="simple",
    )

    def q(mid):
        return mid == "gpt-image-2"

    with patch("app.router.model_health.is_circuit_open", return_value=False), \
         patch("app.router.model_health.is_quarantined", side_effect=q), \
         patch("app.router.model_health.score", return_value=100.0):
        best = router.select_model(analysis, user_model="auto")
    assert best.model_id != "gpt-image-2"
    assert best.model_id in MODEL_STYLE_PREFS["image"]


def test_quarantine_ttl_soft_vs_hard():
    from app.services.model_health import quarantine_ttl_for_reason, QUARANTINE_SOFT_TTL_SECONDS, QUARANTINE_TTL_SECONDS
    assert quarantine_ttl_for_reason("KIE queue timeout after 160s") == QUARANTINE_SOFT_TTL_SECONDS
    assert quarantine_ttl_for_reason("missing KIE map for x") == QUARANTINE_TTL_SECONDS


def test_guess_skus_are_lab_not_default():
    from app.api.models_info import MODELS
    from app.services.model_catalog import GATEWAY_GUESS_IDS, catalog_integrity
    labs = {m.id for m in MODELS if m.status == "lab"}
    assert GATEWAY_GUESS_IDS <= labs
    c = catalog_integrity()
    assert c["lab_count"] >= 15
    assert c.get("guess_still_beta") == []


def test_list_models_hides_lab_by_default():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/v1/models/")
    assert r.status_code == 200
    data = r.json()
    assert data["lab_count"] >= 1
    ids = {m["id"] for m in data["models"]}
    assert "sora-2" not in ids
    assert "runway-gen4" not in ids


def test_fixture_harness_dry():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "scripts" / "fixture_derivative_harness.py"
    spec = importlib.util.spec_from_file_location("fixture_derivative_harness", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    report = mod.check_dry()
    assert report["passed"] is True
