"""P0 Yapper dashboard parity — quote, concurrency 4/6/10/40, omni lipsync_text."""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient):
    email = f"p0_{uuid.uuid4().hex[:8]}@test.local"
    username = f"p0{uuid.uuid4().hex[:6]}"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "username": username},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Plan caps ──────────────────────────────────────────────

def test_plan_concurrency_caps():
    from app.services.concurrency import concurrency_limit, PLAN_CONCURRENCY, _reset_local_slots

    _reset_local_slots()
    assert concurrency_limit("guest") == 2
    assert concurrency_limit("free") == 4
    assert concurrency_limit("starter") == 4
    assert concurrency_limit("personal") == 6
    assert concurrency_limit("creator") == 10
    assert concurrency_limit("pro") == 40
    assert concurrency_limit("max") == 40
    assert concurrency_limit("admin") == 40
    assert PLAN_CONCURRENCY["guest"] == 2


def test_plan_shot_concurrency_mins_with_env():
    from app.services.concurrency import plan_shot_concurrency

    assert plan_shot_concurrency("guest", 8) == 2
    assert plan_shot_concurrency("free", 8) == 4
    assert plan_shot_concurrency("personal", 8) == 6
    assert plan_shot_concurrency("creator", 2) == 2
    assert plan_shot_concurrency("pro", 8) == 8  # env cap 8, plan 40


@pytest.mark.asyncio
async def test_acquire_rejects_when_full():
    from app.services.concurrency import (
        acquire_slot, ConcurrencyLimitError, _reset_local_slots, release_slot,
    )

    _reset_local_slots()

    async def _zero(_db, _uid):
        return 0

    with patch("app.services.concurrency.count_active_db", _zero):
        await acquire_slot(None, user_id=42, slot_id="a", role="guest")
        await acquire_slot(None, user_id=42, slot_id="b", role="guest")
        with pytest.raises(ConcurrencyLimitError) as ei:
            await acquire_slot(None, user_id=42, slot_id="c", role="guest")
        err = ei.value
        assert err.limit == 2
        assert err.used >= 2
        assert err.upgrade_plan == "starter"
        body = err.args[0]
        assert "并发已满" in body
        release_slot(42, "a")
        release_slot(42, "b")


def test_concurrency_http_shape():
    from app.services.concurrency import ConcurrencyLimitError, concurrency_http_exception

    err = ConcurrencyLimitError(
        used=4, limit=4, role="free", retry_after=30,
        upgrade_plan="personal", upgrade_hint="升级 Personal 可同时跑 6 个任务",
    )
    http = concurrency_http_exception(err)
    assert http.status_code == 429
    assert http.headers["Retry-After"] == "30"
    detail = http.detail
    assert detail["error"] == "concurrency_limit"
    assert detail["concurrent_limit"] == 4
    assert detail["upgrade_url"] == "/pricing"
    assert "6" in detail["upgrade_hint"]


# ── Quote API ──────────────────────────────────────────────

def test_quote_shape(client: TestClient, auth_headers):
    r = client.post(
        "/api/v1/generate/quote",
        json={"prompt": "赛博朋克夜景电影感视频", "media_type": "video", "duration": 5, "model": "seedance-2.0"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    for key in (
        "estimated_cost_credits", "estimated_time_seconds", "queue_ahead",
        "concurrent_used", "concurrent_limit", "refund_on_failure",
        "eta_source", "recommended_model", "honesty",
    ):
        assert key in d, key
    assert d["eta_source"] == "catalog"
    assert d["refund_on_failure"] is True
    assert d["estimated_cost_credits"] >= 1
    assert d["estimated_time_seconds"] >= 1
    assert d["concurrent_limit"] in (2, 4, 6, 10, 40)
    assert "SLA" in d["honesty"] or "均时" in d["honesty"]


def test_quote_active_model_ids(client: TestClient, auth_headers):
    r = client.post(
        "/api/v1/generate/quote",
        json={"prompt": "产品海报", "media_type": "image", "model": "nano-banana-pro"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["recommended_model"] == "nano-banana-pro"
    assert d["estimated_cost_credits"] >= 1

    r2 = client.post(
        "/api/v1/generate/quote",
        json={"prompt": "cinematic drone", "media_type": "video", "model": "kling-2.5-turbo", "duration": 5},
        headers=auth_headers,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["recommended_model"] == "kling-2.5-turbo"
    assert r2.json()["estimated_time_seconds"] >= 30


def test_quote_lipsync_adds_cost(client: TestClient, auth_headers):
    base = client.post(
        "/api/v1/generate/quote",
        json={"prompt": "口播数字人", "media_type": "video", "model": "seedance-2.0", "duration": 5},
        headers=auth_headers,
    ).json()
    with_ls = client.post(
        "/api/v1/generate/quote",
        json={
            "prompt": "口播数字人", "media_type": "video", "model": "seedance-2.0",
            "duration": 5, "lipsync_text": "大家好，欢迎来到 Betty。",
        },
        headers=auth_headers,
    ).json()
    assert with_ls["lipsync_included"] is True
    assert with_ls["estimated_cost_credits"] > base["estimated_cost_credits"]
    assert with_ls["estimated_time_seconds"] > base["estimated_time_seconds"]


def test_analyze_still_works(client: TestClient, auth_headers):
    r = client.post(
        "/api/v1/generate/analyze",
        json={"prompt": "neon city night", "media_type": "image"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    assert "recommended_model" in r.json()


def test_generate_429_concurrency(client: TestClient, auth_headers):
    from app.services.concurrency import ConcurrencyLimitError

    async def boom(*_a, **_k):
        raise ConcurrencyLimitError(
            used=4, limit=4, role="free", retry_after=30,
            upgrade_plan="personal", upgrade_hint="升级 Personal 可同时跑 6 个任务",
        )

    with patch("app.services.concurrency.acquire_slot", boom):
        r = client.post(
            "/api/v1/generate/",
            json={"prompt": "a cat walking", "media_type": "image"},
            headers=auth_headers,
        )
    assert r.status_code == 429, r.text
    d = r.json()["detail"]
    assert d["error"] == "concurrency_limit"
    assert d["retry_after"] == 30
    assert d["concurrent_limit"] == 4
    assert r.headers.get("retry-after") == "30"


def test_lipsync_text_accepted_on_generate_request():
    from app.api.generate import GenerateRequest

    req = GenerateRequest(
        prompt="talking avatar",
        media_type="video",
        lipsync_text="Hello from the omni pipeline",
        reference_images=["https://example.com/face.png"],
        omni=True,
    )
    assert req.lipsync_text.startswith("Hello")
    assert req.omni is True


def test_estimate_catalog_models():
    from app.api.generate import _estimate_time_and_cost

    t, c, ls = _estimate_time_and_cost("image", "nano-banana-pro", 5)
    assert ls is False
    assert c >= 1 and t >= 1
    t2, c2, ls2 = _estimate_time_and_cost("video", "kling-2.5-turbo", 10, lipsync_text="hi")
    assert ls2 is True
    assert c2 > c
    t3, c3, _ = _estimate_time_and_cost("image", "imagen-4", 5)
    assert c3 >= 1


def test_omni_lipsync_chain_demo(monkeypatch):
    from app.tasks.video_tasks import _maybe_chain_lipsync

    monkeypatch.setattr("app.tasks.video_tasks._update_task", lambda *a, **k: None)
    monkeypatch.setattr("app.tasks.video_tasks._broadcast_progress", lambda *a, **k: None)
    out = [{"type": "video", "url": "/v.mp4"}]
    assert _maybe_chain_lipsync("t1", {}, out) == out
    skipped = _maybe_chain_lipsync("t1", {"lipsync_text": "hello"}, [{"type": "video", "url": "/v.mp4"}])
    assert skipped[0].get("lipsync_skipped") == "no_reference_image"
    chained = _maybe_chain_lipsync(
        "t1",
        {"lipsync_text": "大家好", "image_url": "/api/v1/media/face.png"},
        [{"type": "video", "url": "/v.mp4"}],
    )
    assert len(chained) >= 1
    assert chained[0].get("url")
