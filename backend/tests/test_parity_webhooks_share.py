"""Parity iteration: webhooks, rate limit Redis, share, notifications."""
import hashlib
import hmac
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_webhook_sign_and_deliver(monkeypatch):
    from app.services import task_hooks

    body = b'{"event":"task.completed"}'
    headers = task_hooks.sign_payload(body, secret="sekrit", timestamp=1700000000)
    assert headers["X-Betty-Timestamp"] == "1700000000"
    assert headers["X-Betty-Signature"].startswith("sha256=")
    expected = hmac.new(
        b"sekrit", b"1700000000." + body, hashlib.sha256
    ).hexdigest()
    assert headers["X-Betty-Signature"] == f"sha256={expected}"

    task = {
        "task_id": "abc-123",
        "status": "completed",
        "media_type": "image",
        "selected_model": "nano-banana",
        "prompt": "hello",
        "results": [{"url": "https://cdn.example.com/a.png", "type": "image"}],
        "error_message": None,
        "webhook_url": "https://hooks.example.com/betty",
        "actual_cost": 1,
        "estimated_cost": 1,
        "user_id": 1,
    }

    class FakeResp:
        status_code = 200

    class FakeClient:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def post(self, url, content=None, headers=None):
            assert url == task["webhook_url"]
            assert headers["X-Betty-Signature"].startswith("sha256=")
            return FakeResp()

    monkeypatch.setattr(task_hooks.httpx, "Client", FakeClient)
    monkeypatch.setattr(task_hooks, "_BACKOFF_S", (0, 0, 0))
    res = task_hooks.deliver_webhook("abc-123", task=task)
    assert res["delivered"] is True


def test_webhook_skips_when_missing():
    from app.services.task_hooks import deliver_webhook
    r = deliver_webhook("x", task={"task_id": "x", "webhook_url": "", "status": "completed", "results": []})
    assert r["delivered"] is False
    assert r["reason"] == "no_webhook"


def test_rate_limiter_uses_redis_url(monkeypatch):
    from app import rate_limiter as rl

    monkeypatch.setattr(rl.settings, "REDIS_URL", "redis://redis.internal:6379/1")
    rl.rate_limiter._client = None
    captured = {}

    def fake_from_url(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return MagicMock()

    monkeypatch.setattr(rl.redis.Redis, "from_url", staticmethod(fake_from_url))
    _ = rl.rate_limiter.client
    assert captured["url"] == "redis://redis.internal:6379/1"
    assert captured["kwargs"].get("db") == 3


def test_capabilities_include_motion_honesty():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/v1/system/capabilities")
    assert r.status_code == 200
    data = r.json()
    assert "features" in data
    assert data["features"]["motion_transfer"]["mode"] == "native"
    assert data["features"]["motion_transfer"]["sku"] == "kling-3.0/motion-control"
    assert data["features"]["task_webhooks"]["available"] is True


def test_share_endpoint_rejects_short_id():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/v1/gallery/share/short")
    assert r.status_code == 400


def test_share_item_helper_missing(monkeypatch):
    """Unit-level: missing task yields 404 without depending on lifespan DDL."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from fastapi import HTTPException
    from app.api import gallery

    class FakeResult:
        def first(self):
            return None

    db = AsyncMock()
    db.execute = AsyncMock(return_value=FakeResult())

    async def _run():
        with pytest.raises(HTTPException) as ei:
            await gallery.share_item("does-not-exist-zzzz", db=db)
        assert ei.value.status_code == 404

    asyncio.run(_run())


def test_notify_email_prefs_off(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    from app.services import task_hooks

    db_path = tmp_path / "n.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as s:
        s.execute(text(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, metadata_json TEXT)"
        ))
        s.execute(text(
            "INSERT INTO users (id, email, metadata_json) VALUES (1, 'a@b.com', :m)"
        ), {"m": json.dumps({"notifications": {"email_task_complete": False}})})
        s.commit()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    task = {
        "task_id": "t1",
        "user_id": 1,
        "status": "completed",
        "results": [],
        "prompt": "x",
    }
    r = task_hooks.notify_task_email("t1", task=task)
    assert r["sent"] is False
    assert r["reason"] == "prefs_off"


def test_on_task_terminal_wires_hooks(monkeypatch):
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
            "error_message": None,
            "actual_cost": 0,
            "estimated_cost": 0,
        },
    )
    monkeypatch.setattr(task_hooks, "deliver_webhook", lambda *a, **k: {"delivered": False, "reason": "no_webhook"})
    monkeypatch.setattr(task_hooks, "notify_task_email", lambda *a, **k: {"sent": False, "reason": "smtp_missing"})
    out = task_hooks.on_task_terminal("tid-1", status="completed")
    assert out["ok"] is True
    assert "webhook" in out and "email" in out
