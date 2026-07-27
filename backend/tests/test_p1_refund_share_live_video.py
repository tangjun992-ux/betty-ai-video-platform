"""P1: failure refund, share publish gate, live_video weekly smoke (verified)."""
import json
import os
import sys
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_billing_db(tmp_path):
    db_path = tmp_path / "p1.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as s:
        s.execute(text(
            "CREATE TABLE user_balance ("
            "id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, credits INTEGER, "
            "daily_credits INTEGER DEFAULT 0, plan_credits INTEGER DEFAULT 0, "
            "total_spent INTEGER DEFAULT 0, total_tasks INTEGER DEFAULT 0, "
            "created_at DATETIME, updated_at DATETIME)"
        ))
        s.execute(text(
            "CREATE TABLE transactions ("
            "id INTEGER PRIMARY KEY, user_id INTEGER, task_id TEXT, team_id TEXT, "
            "type TEXT, amount INTEGER, balance_before INTEGER, balance_after INTEGER, "
            "description TEXT, model_used TEXT, amount_usd REAL, payment_method TEXT, "
            "payment_id TEXT, created_at DATETIME, updated_at DATETIME)"
        ))
        s.execute(text(
            "CREATE TABLE tasks ("
            "id INTEGER PRIMARY KEY, task_id TEXT UNIQUE, user_id INTEGER, "
            "prompt TEXT, media_type TEXT, status TEXT, parameters TEXT, "
            "created_at DATETIME, updated_at DATETIME)"
        ))
        s.execute(text(
            "INSERT INTO user_balance (user_id, credits, daily_credits, plan_credits, total_spent, total_tasks) "
            "VALUES (1, 40, 0, 0, 10, 1)"
        ))
        s.execute(text(
            "INSERT INTO transactions "
            "(user_id, task_id, team_id, type, amount, balance_before, balance_after, "
            "description, model_used, created_at, updated_at) "
            "VALUES (1, 'task-fail-001', NULL, 'consumption', -10, 50, 40, "
            "'gen', 'nano-banana', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ))
        s.execute(text(
            "INSERT INTO tasks (task_id, user_id, prompt, media_type, status, parameters) "
            "VALUES ('task-fail-001', 1, 'p', 'image', 'failed', '{}')"
        ))
        s.commit()
    return f"sqlite:///{db_path}"


def test_refund_task_credits_sync_idempotent(tmp_path, monkeypatch):
    from app.services.credits import refund_task_credits_sync

    url = _make_billing_db(tmp_path)
    monkeypatch.setenv("DATABASE_URL", url)

    first = refund_task_credits_sync("task-fail-001", reason="task_failed")
    assert first["refunded"] is True
    assert first["amount"] == 10

    second = refund_task_credits_sync("task-fail-001", reason="task_failed")
    assert second["refunded"] is False
    assert second["reason"] == "already_refunded"

    engine = create_engine(url)
    with Session(engine) as s:
        bal = s.execute(text("SELECT credits, total_spent FROM user_balance WHERE user_id=1")).first()
        assert bal[0] == 50  # 40 + 10
        assert bal[1] == 0
        refunds = s.execute(
            text("SELECT COUNT(*) FROM transactions WHERE task_id='task-fail-001' AND type='refund'")
        ).scalar()
        assert refunds == 1
        params = s.execute(
            text("SELECT parameters FROM tasks WHERE task_id='task-fail-001'")
        ).scalar()
        assert json.loads(params).get("credits_refunded") is True


def test_on_task_terminal_refunds_failed(monkeypatch):
    from app.services import task_hooks

    monkeypatch.setattr(
        task_hooks,
        "_load_task_row",
        lambda tid: {
            "task_id": tid,
            "user_id": 1,
            "status": "queued",
            "webhook_url": "",
            "results": "[]",
            "prompt": "p",
            "media_type": "image",
            "selected_model": "m",
            "error_message": "boom",
            "actual_cost": 0,
            "estimated_cost": 5,
        },
    )
    monkeypatch.setattr(task_hooks, "deliver_webhook", lambda *a, **k: {"delivered": False})
    monkeypatch.setattr(task_hooks, "notify_task_email", lambda *a, **k: {"sent": False})

    called = {}

    def fake_refund(tid, *, reason="task_failed"):
        called["tid"] = tid
        called["reason"] = reason
        return {"refunded": True, "amount": 5, "reason": reason}

    monkeypatch.setattr(
        "app.services.credits.refund_task_credits_sync", fake_refund,
    )
    out = task_hooks.on_task_terminal("tid-fail", status="failed")
    assert out["ok"] is True
    assert out["refund"]["refunded"] is True
    assert called["tid"] == "tid-fail"
    assert "failed" in called["reason"]

    # completed must not refund
    called.clear()
    out2 = task_hooks.on_task_terminal("tid-ok", status="completed")
    assert out2["refund"]["reason"] == "not_applicable"
    assert "tid" not in called


def test_share_requires_publish_gate():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.gallery import _is_share_public

    assert _is_share_public({"share_public": True}) is True
    assert _is_share_public({}) is False
    assert _is_share_public({"share_public": False}) is False

    c = TestClient(app)
    # unpublished completed task must 404 on public share
    # Insert via ORM if possible — use API generate is heavy; unit-level share helper
    r = c.get("/api/v1/gallery/share/unpublished-task-zzzzzzzz")
    assert r.status_code in (404, 400)


def test_publish_and_share_roundtrip():
    """Owner publish → public share works; before publish → 404."""
    import asyncio
    from fastapi.testclient import TestClient
    from sqlalchemy import select
    from app.main import app
    from app.db import async_session
    from app.models.task import Task
    from app.services.guest import get_or_create_guest_user

    c = TestClient(app)
    guest_token = "p1-share-owner-guest"
    headers = {"X-Guest-Id": guest_token}
    task_id = "p1share00000001"

    async def seed_task():
        async with async_session() as db:
            uid = await get_or_create_guest_user(db, guest_token)
            await db.commit()
            existing = await db.execute(select(Task).where(Task.task_id == task_id))
            t = existing.scalar_one_or_none()
            payload = {"resolution": "1080x1080", "share_public": False}
            results = [{"type": "image", "url": "https://example.com/p1.png", "model": "nano-banana"}]
            if t is None:
                db.add(Task(
                    task_id=task_id,
                    user_id=int(uid),
                    prompt="safe landscape photo of mountains",
                    media_type="image",
                    status="completed",
                    parameters=payload,
                    results=results,
                    completed_at=datetime.now(timezone.utc),
                ))
            else:
                t.user_id = int(uid)
                t.status = "completed"
                t.prompt = "safe landscape photo of mountains"
                t.parameters = payload
                t.results = results
                t.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return uid

    asyncio.run(seed_task())

    before = c.get(f"/api/v1/gallery/share/{task_id}")
    assert before.status_code == 404, before.text

    pub = c.post(f"/api/v1/gallery/share/{task_id}/publish", headers=headers)
    assert pub.status_code == 200, pub.text
    assert pub.json()["share_public"] is True

    after = c.get(f"/api/v1/gallery/share/{task_id}")
    assert after.status_code == 200, after.text
    assert after.json()["task_id"] == task_id

    un = c.post(f"/api/v1/gallery/share/{task_id}/unpublish", headers=headers)
    assert un.status_code == 200, un.text
    gone = c.get(f"/api/v1/gallery/share/{task_id}")
    assert gone.status_code == 404


def test_live_video_weekly_gated_and_registered(monkeypatch):
    from celery_app import app
    from app.tasks.health_tasks import smoke_live_video_weekly

    app.loader.import_default_modules()
    assert "app.tasks.health_tasks.smoke_live_video_weekly" in app.tasks

    beat = app.conf.beat_schedule or {}
    assert "model-health-live-video-weekly" in beat
    assert beat["model-health-live-video-weekly"]["schedule"] == 604800.0

    monkeypatch.delenv("MODEL_SMOKE_LIVE_VIDEO_WEEKLY", raising=False)
    monkeypatch.delenv("MODEL_SMOKE_LIVE_VIDEO", raising=False)
    report = smoke_live_video_weekly()
    assert report.get("skipped") is True
    assert report.get("outframe_ok", 0) == 0
    assert report.get("probed", 0) == 0


def test_capabilities_advertise_p1_features():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/capabilities")
    assert r.status_code == 200
    feats = r.json()["features"]
    assert feats["share_permalink"]["requires_publish"] is True
    assert feats["failure_refund"]["available"] is True
    assert feats["live_video_weekly_smoke"]["available"] is True
