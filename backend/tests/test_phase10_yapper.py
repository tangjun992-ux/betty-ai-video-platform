"""Phase 10 — E2E alignment, smoke auto-promote, beta probe rotation."""
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_auto_promote_disabled_by_default():
    from app.services.model_promotion import auto_promote_enabled, maybe_auto_promote_from_smoke

    assert auto_promote_enabled() is False
    r = maybe_auto_promote_from_smoke({
        "details": [{"model_id": "wan-2.2", "ok": True, "path": "live_video_gateway"}],
    })
    assert r["skipped"] is True
    assert r["promoted"] == []


def test_auto_promote_promotes_mapped_beta_on_outframe():
    from app.api.models_info import MODELS
    from app.services.model_promotion import demote_model, maybe_auto_promote_from_smoke

    mid = "veo-3.1"
    demote_model(mid, note="phase15 test setup")
    assert next(x for x in MODELS if x.id == mid).status == "beta"

    with patch.dict(os.environ, {"MODEL_SMOKE_AUTO_PROMOTE": "1"}):
        report = {
            "probed": 1,
            "ok": 1,
            "outframe_ok": 1,
            "details": [
                {
                    "model_id": mid,
                    "ok": True,
                    "path": "live_video_gateway",
                    "evidence": {"path": "live_video_gateway"},
                },
            ],
        }
        r = maybe_auto_promote_from_smoke(report)
    assert r["skipped"] is False
    assert mid in r["promoted"]
    assert next(x for x in MODELS if x.id == mid).status == "active"
    # veo-3.1 remains active in catalog after promote (phase 14 shelf)


def test_auto_promote_ignores_non_outframe():
    from app.services.model_promotion import maybe_auto_promote_from_smoke

    with patch.dict(os.environ, {"MODEL_SMOKE_AUTO_PROMOTE": "1"}):
        r = maybe_auto_promote_from_smoke({
            "details": [{"model_id": "veo-3", "ok": True, "path": "mapping_only"}],
        })
    assert r["promoted"] == []


def test_beta_probe_rotation_picks_mapped_beta():
    from app.services.model_catalog import GATEWAY_MAPPED_BETA_IDS
    from app.services.model_smoke import beta_probe_rotation

    picks = beta_probe_rotation(media="video", n=2)
    assert len(picks) <= 2
    for mid in picks:
        assert mid in GATEWAY_MAPPED_BETA_IDS


def test_merge_smoke_reports_dedupes():
    from app.services.model_smoke import merge_smoke_reports

    merged = merge_smoke_reports(
        {"probed": 1, "ok": 1, "outframe_ok": 1, "failed": [], "details": [{"model_id": "a", "ok": True}]},
        {"probed": 1, "ok": 0, "outframe_ok": 0, "failed": ["b"], "details": [{"model_id": "b", "ok": False}]},
    )
    assert len(merged["details"]) == 2
    assert merged["probed"] == 2


def test_run_beta_video_probe_empty_when_no_candidates(monkeypatch):
    from app.services import model_smoke

    monkeypatch.setattr(model_smoke, "DEFAULT_BETA_VIDEO_PROBE", ())
    report = model_smoke.run_beta_video_probe(models=[])
    assert report.get("skipped") is True


def test_health_task_weekly_skipped_when_gated():
    from app.tasks.health_tasks import smoke_live_video_weekly

    with patch.dict(os.environ, {"MODEL_SMOKE_LIVE_VIDEO_WEEKLY": "", "MODEL_SMOKE_LIVE_VIDEO": ""}, clear=False):
        report = smoke_live_video_weekly()
    assert report.get("skipped") is True
