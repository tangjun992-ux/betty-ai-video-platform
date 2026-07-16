"""Yapper parity hardening: smoke honesty, minimal director, fixtures, motion SKU map."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def test_health_unproven_not_perfect():
    from app.services.model_health import HealthSnapshot

    snap = HealthSnapshot(model_id="x")
    assert snap.total == 0
    assert snap.success_rate == 0.85
    assert snap.score <= 85.0


def test_run_active_smoke_mapping_does_not_record_success():
    from app.services import model_smoke

    fake_probe = {
        "ok": True,
        "latency_ms": 10,
        "error": "",
        "mode": "mapping",
        "evidence": {"path": "mapping_only", "kie_id": "x"},
    }
    recorded = []

    class FakeHealth:
        def record_success(self, *a, **k):
            recorded.append(("success", a, k))

        def clear_quarantine(self, *a, **k):
            recorded.append(("clear", a))

        def record_failure(self, *a, **k):
            recorded.append(("fail", a))

        def set_quarantine(self, *a, **k):
            recorded.append(("quarantine", a))

    class FakeModel:
        def __init__(self, mid):
            self.id = mid
            self.status = "active"
            self.capabilities = type("C", (), {"media_types": ["image"]})()

    with patch.object(model_smoke, "probe_model", return_value=fake_probe), \
         patch("app.api.models_info.MODELS", [FakeModel("gpt-image-2")]), \
         patch("app.services.model_health.model_health", FakeHealth()), \
         patch.object(model_smoke, "save_last_smoke"):
        report = model_smoke.run_active_smoke(mode="mapping")

    assert report["ok"] == 1
    assert report["outframe_ok"] == 0
    assert not any(r[0] == "success" for r in recorded)
    assert any(r[0] == "clear" for r in recorded)


def test_motion_control_mapped_in_kie():
    from app.adapters.kie_adapter import KIE_MODEL_IDS, _resolve_kie_model_id

    assert "motion-control" in KIE_MODEL_IDS
    assert _resolve_kie_model_id("motion-control").startswith("bytedance/")


def test_director_minimal_skips_post_ladder():
    from app.director import DirectorPlanner

    plan = DirectorPlanner().plan("做一条产品宣传视频", duration=5, minimal=True)
    actions = [s.action for s in plan.steps]
    assert "image" in actions
    assert "video" in actions
    assert "audio" not in actions
    assert "compose" not in actions
    assert "subtitle" not in actions


def test_director_plan_api_minimal():
    from app.main import app

    c = TestClient(app)
    r = c.post(
        "/api/v1/director/plan",
        json={"brief": "做一条短视频广告", "duration": 5, "minimal": True},
    )
    assert r.status_code == 200, r.text
    steps = r.json().get("steps") or []
    actions = [s.get("action") for s in steps]
    assert "video" in actions
    assert "compose" not in actions


def test_lipsync_and_motion_fixtures_exist_or_generatable():
    root = Path(__file__).resolve().parents[1]
    # Generate if missing
    import subprocess, sys
    subprocess.check_call([sys.executable, str(root / "scripts" / "generate_lipsync_fixtures.py")])
    assert (root / "fixtures" / "lipsync" / "portrait.png").is_file()
    assert (root / "fixtures" / "lipsync" / "line.wav").is_file()
    assert (root / "fixtures" / "motion" / "still.png").is_file()


def test_fixture_harness_includes_lipsync_library():
    import importlib.util
    import sys

    path = Path(__file__).resolve().parents[1] / "scripts" / "fixture_derivative_harness.py"
    spec = importlib.util.spec_from_file_location("fix_harness", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Ensure lipsync fixtures
    import subprocess
    subprocess.check_call([sys.executable, str(path.parents[0] / "generate_lipsync_fixtures.py")])
    lib = mod.check_lipsync_library()
    assert lib["passed"] is True
