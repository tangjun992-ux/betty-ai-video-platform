"""P0/P1 hardening: Seedance Omni payload, Max pricing, social URL honesty."""
from __future__ import annotations

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers(client: TestClient):
    email = f"omni_{uuid.uuid4().hex[:8]}@test.local"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "username": f"o{uuid.uuid4().hex[:6]}"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_kie_seedance_omni_payload():
    from app.adapters.kie_adapter import KieAdapter

    adapter = KieAdapter.__new__(KieAdapter)
    captured = {}

    async def fake_submit(payload, media_type="video", timeout=900):
        captured.update(payload)
        return {"resultJson": '{"resultUrls":["https://cdn.example.com/o.mp4"]}', "taskId": "t-omni"}

    adapter._submit_and_poll = fake_submit  # type: ignore
    res = asyncio.run(adapter.generate_video(
        "fashion promo with @Image1",
        model_id="seedance-2.0",
        duration=5,
        resolution="720p",
        reference_images=["https://img/a.png", "https://img/b.png"],
        reference_videos=["https://vid/r.mp4"],
        omni=True,
        generate_audio=True,
    ))
    assert captured["model"] == "bytedance/seedance-2"
    assert captured["reference_image_urls"] == ["https://img/a.png", "https://img/b.png"]
    assert captured["reference_video_urls"] == ["https://vid/r.mp4"]
    assert captured.get("generate_audio") is True
    assert res.meta.get("omni") is True


def test_pricing_max_plan_and_pro_alias():
    from app.api.pricing import get_plan, normalize_plan_id, PLANS

    assert normalize_plan_id("pro") == "max"
    assert get_plan("pro") is not None
    assert get_plan("pro").id == "max"
    assert any(p.id == "max" for p in PLANS)
    assert not any(p.id == "pro" for p in PLANS)


def test_pricing_api_returns_max(client: TestClient):
    r = client.get("/api/v1/pricing/plans")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()["plans"]}
    assert "max" in ids
    assert "pro" not in ids
    max_plan = next(p for p in r.json()["plans"] if p["id"] == "max")
    assert "pro" in (max_plan.get("aliases") or [])


def test_extractor_tiktok_page_honest(client: TestClient, auth_headers):
    r = client.post(
        "/api/v1/generate/extract-prompt",
        headers=auth_headers,
        data={"media_url": "https://www.tiktok.com/@x/video/123", "media_kind": "video"},
    )
    # Best-effort: usually 400 when IP-blocked; never silent 500
    assert r.status_code in (200, 400)
    if r.status_code == 400:
        detail = r.json().get("detail") or ""
        assert detail


def test_capabilities_omni_and_face_swap(client: TestClient):
    r = client.get("/api/v1/system/capabilities")
    assert r.status_code == 200
    feats = r.json()["features"]
    assert "seedance_omni" in feats
    assert feats["face_swap"]["mode"] == "i2i_edit"
    assert feats["face_swap"]["sku"] == "google/nano-banana-edit"
    social = feats["prompt_extractor"].get("social_page_urls") or {}
    assert social.get("youtube") is True


def test_social_url_helper():
    from app.services.social_resolve import is_social_page_url, classify_social_platform

    assert is_social_page_url("https://www.instagram.com/reel/abc")
    assert classify_social_platform("https://youtu.be/xyz") == "youtube"
    assert not is_social_page_url("https://tempfile.aiquickdraw.com/x.png")
