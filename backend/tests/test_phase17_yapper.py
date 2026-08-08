"""Phase 17 — alert dedupe, shelf 18, variant compare, pricing checkout E2E."""
import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_ops_alerts_dedupe_flag():
    from app.services.ops_alerts import ops_alerts_status

    st = ops_alerts_status()
    assert st["alert_dedupe"] is True


def test_webhook_alert_deduped_on_second_failure(tmp_path, monkeypatch):
    from app.services import task_hooks

    db_path = tmp_path / "dedup.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("OPS_ALERT_WEBHOOK_URL", "https://hooks.slack.test/ops")

    from sqlalchemy import create_engine, text

    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                task_id TEXT, user_id INTEGER, status TEXT, prompt TEXT, media_type TEXT,
                webhook_url TEXT, parameters TEXT, results TEXT, error_message TEXT,
                selected_model TEXT, actual_cost REAL, estimated_cost REAL,
                created_at TEXT, updated_at TEXT
            )
        """))
        conn.execute(text("""
            INSERT INTO tasks (task_id, user_id, status, prompt, media_type, webhook_url, parameters, created_at, updated_at)
            VALUES ('dedup-1', 1, 'completed', 'p', 'image', 'https://cb.test/h', '{}', datetime('now'), datetime('now'))
        """))

    alerts = []
    with patch.object(task_hooks, "_sync_engine", return_value=engine), \
         patch("app.services.ops_alerts.alert_webhook_failure", side_effect=lambda *a, **k: alerts.append(1) or {"sent": True}):
        task_hooks.persist_webhook_status("dedup-1", {"delivered": False, "reason": "500", "attempts": 3})
        task_hooks.persist_webhook_status("dedup-1", {"delivered": False, "reason": "500", "attempts": 4})
    assert len(alerts) == 1


def test_active_shelf_18_kling_26():
    from app.api.models_info import MODELS
    from app.services.model_catalog import GATEWAY_VERIFIED_IDS, catalog_integrity

    assert "kling-2.6" in GATEWAY_VERIFIED_IDS
    m = next(x for x in MODELS if x.id == "kling-2.6")
    assert m.status == "active"
    cat = catalog_integrity()
    assert cat["active_count"] >= 18


def test_readiness_active_target_18():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/readiness")
    assert r.status_code == 200
    assert r.json()["catalog"]["active_target"] == 18


def test_billing_dev_grant_pack_checkout():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    gid = f"p17-pack-{os.urandom(4).hex()}"
    r = c.post("/api/v1/billing/checkout", headers={"X-Guest-Id": gid}, json={
        "kind": "pack", "id": "pack_mini", "cycle": "monthly", "quantity": 1,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("mode") == "dev"
    assert body.get("success") is True
    assert body.get("credits_added", 0) > 0


def test_variant_compare_table_in_agent_page():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "app" / "agent" / "page.tsx").read_text(encoding="utf-8")
    assert "agent-variant-compare-table" in text
    assert "parseVariantAxes" in text


def test_pricing_e2e_spec_exists():
    from pathlib import Path
    assert (Path(__file__).resolve().parents[2] / "frontend" / "e2e" / "pricing.spec.ts").is_file()
