"""Phase 7 Yapper parity — estimate, concurrent caps, oneclick, post_lipsync."""
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_estimate_endpoint_video_with_lipsync_addon():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    base = c.post("/api/v1/generate/estimate", json={
        "media_type": "video", "model": "seedance-2.0", "duration": 5, "count": 1,
    })
    assert base.status_code == 200, base.text
    b = base.json()
    assert b["estimated_cost_credits"] >= 1
    assert b["estimated_time_seconds"] >= 1

    with_ls = c.post("/api/v1/generate/estimate", json={
        "media_type": "video", "model": "seedance-2.0", "duration": 5, "count": 1,
        "post_lipsync": True,
    })
    assert with_ls.status_code == 200
    w = with_ls.json()
    assert w["estimated_cost_credits"] == b["estimated_cost_credits"] + 4
    assert w["breakdown"].get("lipsync_addon") == 4


def test_estimate_endpoint_image():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.cost_estimate import estimate_generation

    seconds, credits = estimate_generation(media_type="image", model="nano-banana-2", count=2)
    assert credits >= 2
    assert seconds >= 1

    c = TestClient(app)
    r = c.post("/api/v1/generate/estimate", json={
        "media_type": "image", "model": "nano-banana-2", "count": 2,
    })
    assert r.status_code == 200
    assert r.json()["estimated_cost_credits"] == credits


def test_concurrent_cap_by_role():
    from app.services.generation_limits import concurrent_cap_for_role, PLAN_CONCURRENT

    assert concurrent_cap_for_role("guest") == PLAN_CONCURRENT["guest"]
    assert concurrent_cap_for_role("free") == PLAN_CONCURRENT["free"]
    assert concurrent_cap_for_role("creator") == 10
    assert concurrent_cap_for_role("pro") == 15
    assert concurrent_cap_for_role(None) == PLAN_CONCURRENT["guest"]


@pytest.mark.asyncio
async def test_enforce_concurrent_limit_raises_429():
    from fastapi import HTTPException
    from app.services.generation_limits import enforce_concurrent_limit

    db = AsyncMock()
    db.execute = AsyncMock(return_value=type("R", (), {"scalar": lambda self: 10})())
    with pytest.raises(HTTPException) as exc:
        await enforce_concurrent_limit(db, user_id=1, role="creator")
    assert exc.value.status_code == 429


def test_oneclick_endpoint_returns_job():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    headers = {"X-Guest-Id": "phase7-oneclick-guest-01"}
    with patch("app.tasks.director_tasks.run_director.delay") as delay, \
         patch("app.api.director._charge_director_plan", new_callable=AsyncMock) as charge:
        charge.return_value = None
        r = c.post("/api/v1/director/run/oneclick", headers=headers, json={
            "brief": "30秒咖啡产品宣传片，电影感",
            "duration": 5,
            "minimal": True,
            "scenario": "product_ad",
        })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("oneclick") is True
    assert body.get("job_id")
    assert body.get("poll_url", "").endswith(body["job_id"])
    assert body.get("total_credits", 0) >= 0
    delay.assert_called_once()


def test_generate_accepts_post_lipsync_fields():
    from app.api.generate import GenerateRequest

    req = GenerateRequest(
        prompt="talking head promo",
        media_type="video",
        post_lipsync=True,
        lipsync_text="Hello world",
        image_url="https://cdn.example.com/face.png",
    )
    assert req.post_lipsync is True
    assert req.lipsync_text == "Hello world"


def test_gallery_seed_threshold():
    import inspect
    from app.services import gallery_seed as gs

    src = inspect.getsource(gs.maybe_seed_gallery_dev)
    assert ">= 50" in src


def test_maybe_chain_lipsync_skips_without_portrait():
    from app.tasks.video_tasks import _maybe_chain_lipsync

    assert _maybe_chain_lipsync("tid", {"post_lipsync": True}, "hello", "https://v.mp4") is None


def test_maybe_chain_lipsync_requires_text():
    from app.tasks.video_tasks import _maybe_chain_lipsync

    assert _maybe_chain_lipsync(
        "tid",
        {"post_lipsync": True, "image_url": "https://cdn.example.com/p.png"},
        "",
        "https://v.mp4",
    ) is None
