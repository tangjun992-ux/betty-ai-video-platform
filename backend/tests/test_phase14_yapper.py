"""Phase 14 — Stripe bootstrap validate, WS-ready task detail, webhook ops, shelf 17."""
import json
import os
import sys
import uuid
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_stripe_bootstrap_status_shape():
    from app.services.stripe_ready import stripe_bootstrap_status, validate_stripe_bootstrap

    bs = stripe_bootstrap_status()
    assert bs["price_envs_total"] >= 9
    assert "validate_cmd" in bs
    assert "dry_run_cmd" in bs

    v = validate_stripe_bootstrap()
    assert "ok" in v
    assert "bootstrap" in v
    assert "blockers" in v


def test_bootstrap_validate_cli():
    import subprocess
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap_stripe_prices.py"
    env = {**os.environ, "ENV": "test"}
    env.pop("STRIPE_API_KEY", None)
    out = subprocess.check_output(
        [sys.executable, str(script), "--validate", "--json-only"],
        env=env,
        cwd=str(script.parent.parent),
    )
    report = json.loads(out.decode())
    assert "bootstrap" in report
    assert report["ok"] is True  # dev/test without keys is ok


def test_readiness_includes_stripe_bootstrap():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/readiness")
    assert r.status_code == 200
    data = r.json()
    assert data["catalog"]["active_target"] == 18
    assert "bootstrap" in data["stripe"]
    assert data["stripe"]["bootstrap"]["price_envs_total"] >= 9


def test_active_shelf_17_veo_promoted():
    from app.api.models_info import MODELS
    from app.services.model_catalog import GATEWAY_VERIFIED_IDS, catalog_integrity

    for mid in ("veo-3.1", "veo-3"):
        assert mid in GATEWAY_VERIFIED_IDS
        assert next(m for m in MODELS if m.id == mid).status == "active"

    cat = catalog_integrity()
    assert cat["active_count"] >= 18


def test_list_failed_webhooks_empty():
    from app.services.task_hooks import list_failed_webhooks

    items = list_failed_webhooks(limit=5, scan=20)
    assert isinstance(items, list)


def test_list_failed_webhooks_finds_row(tmp_path, monkeypatch):
    from app.services import task_hooks

    db_path = tmp_path / "wh_fail.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    from sqlalchemy import create_engine, text

    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                task_id TEXT,
                user_id INTEGER,
                status TEXT,
                prompt TEXT,
                media_type TEXT,
                webhook_url TEXT,
                parameters TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """))
        conn.execute(
            text("""
                INSERT INTO tasks (task_id, user_id, status, prompt, media_type, webhook_url, parameters, created_at, updated_at)
                VALUES (:tid, 1, 'completed', 'p', 'image', 'https://hook.test/cb', :params, datetime('now'), datetime('now'))
            """),
            {
                "tid": "wh-fail-1",
                "params": json.dumps({
                    "webhook": {
                        "delivered": False,
                        "attempts": 3,
                        "status_code": 500,
                        "reason": "upstream error",
                        "at": "2026-08-07T00:00:00Z",
                    },
                }),
            },
        )

    with patch.object(task_hooks, "_sync_engine", return_value=engine):
        rows = task_hooks.list_failed_webhooks(limit=10, scan=50)
    assert len(rows) == 1
    assert rows[0]["task_id"] == "wh-fail-1"
    assert rows[0]["status_code"] == 500


def test_admin_webhook_failures_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import require_admin

    c = TestClient(app)
    app.dependency_overrides[require_admin] = lambda: AsyncMock(id=1)
    try:
        with patch("app.services.task_hooks.list_failed_webhooks", return_value=[]):
            r = c.get("/api/v1/admin/model-health/webhook-failures")
        assert r.status_code == 200
        assert r.json()["failures"] == []
    finally:
        app.dependency_overrides.pop(require_admin, None)


def test_task_detail_ws_route_exists():
    from app.api.websocket import router

    paths = [getattr(r, "path", "") for r in router.routes]
    assert any("/ws/tasks/" in p for p in paths)
