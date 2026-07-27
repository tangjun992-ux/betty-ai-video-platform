"""P0/P1: last-smoke persist, webhook status, library favorites, project ACL."""
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_last_smoke_persist_and_read():
    from app.services import model_smoke
    from app.services.model_health import model_health

    # Force memory path
    with patch.object(model_health, "_client", side_effect=RuntimeError("no redis")):
        model_smoke.save_last_smoke({
            "mode": "mapping",
            "probed": 9,
            "ok": 9,
            "failed": [],
            "quarantined": [],
            "details": [{"model_id": "nano-banana", "ok": True, "latency_ms": 1, "error": "", "evidence": {"path": "mapping_only"}}],
            "ts": "2026-07-16T00:00:00Z",
        })
        report = model_smoke.get_last_smoke()
    assert report is not None
    assert report["mode"] == "mapping"
    assert report["probed"] == 9
    assert report["details"][0]["path"] == "mapping_only"


def test_run_active_smoke_persists(monkeypatch):
    from app.services import model_smoke

    saved = {}

    def fake_save(report):
        saved.update(report)

    monkeypatch.setattr(model_smoke, "save_last_smoke", fake_save)
    monkeypatch.setattr(model_smoke, "probe_model", lambda *a, **k: {
        "ok": True, "latency_ms": 1, "error": "", "mode": "mapping", "evidence": {"path": "mapping_only"},
    })
    with patch("app.services.model_health.model_health.record_success"), \
         patch("app.services.model_health.model_health.clear_quarantine"):
        result = model_smoke.run_active_smoke(mode="mapping")
    assert result["probed"] >= 1
    assert result["ok"] == result["probed"]
    assert saved.get("mode") == "mapping"
    assert "ts" in saved


def test_live_skipped_video_not_counted_as_ok(monkeypatch):
    from app.services import model_smoke

    def fake_probe(model_id, media, mode=None):
        if "video" in media or model_id.startswith("kling") or model_id.startswith("seedance"):
            return {
                "ok": True, "latency_ms": 1, "error": "", "mode": "live",
                "evidence": {"path": "live_skipped_video"},
            }
        return {
            "ok": True, "latency_ms": 1, "error": "", "mode": "live",
            "evidence": {"path": "live_image"},
        }

    monkeypatch.setattr(model_smoke, "probe_model", fake_probe)
    monkeypatch.setattr(model_smoke, "save_last_smoke", lambda r: None)
    with patch("app.services.model_health.model_health.record_success"), \
         patch("app.services.model_health.model_health.clear_quarantine"):
        r = model_smoke.run_active_smoke(mode="live")
    assert r["outframe_skipped"] >= 1
    assert r["ok"] == r["outframe_ok"]
    assert len(r["skipped"]) == r["outframe_skipped"]
    assert r["ok"] + r["outframe_skipped"] + len(r["failed"]) == r["probed"]


def test_persist_webhook_status(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    from app.services import task_hooks

    db = tmp_path / "w.db"
    engine = create_engine(f"sqlite:///{db}")
    with Session(engine) as s:
        s.execute(text(
            "CREATE TABLE tasks (task_id TEXT, parameters TEXT)"
        ))
        s.execute(text(
            "INSERT INTO tasks (task_id, parameters) VALUES ('tid-1', :p)"
        ), {"p": json.dumps({"resolution": "1080x1080"})})
        s.commit()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    task_hooks.persist_webhook_status("tid-1", {"delivered": True, "attempts": 1, "status_code": 200})
    with Session(engine) as s:
        raw = s.execute(text("SELECT parameters FROM tasks WHERE task_id='tid-1'")).scalar()
    params = json.loads(raw)
    assert params["resolution"] == "1080x1080"
    assert params["webhook"]["delivered"] is True
    assert params["webhook"]["status_code"] == 200


def test_project_visibility_can_view():
    import asyncio
    from unittest.mock import AsyncMock
    from app.api import projects
    from app.models.project import Project

    p = Project(project_id="p1", user_id=1, name="A", items=[], visibility="private", team_id=None)

    async def _run():
        db = AsyncMock()
        assert await projects._can_view(db, p, 1) is True
        assert await projects._can_view(db, p, 2) is False
        p.visibility = "public"
        assert await projects._can_view(db, p, 2) is True

    asyncio.run(_run())


def test_models_health_includes_last_smoke_key():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/v1/models/health")
    assert r.status_code == 200
    assert "last_smoke" in r.json()
