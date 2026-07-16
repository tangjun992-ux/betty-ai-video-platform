"""Gap closure: Face Swap (i2i), social resolve, Performance Drive honesty."""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest


@pytest.fixture
def auth_headers(client):
    email = f"gap_{uuid.uuid4().hex[:8]}@test.local"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "username": f"g{uuid.uuid4().hex[:6]}"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_capabilities_face_swap_and_performance(client):
    r = client.get("/api/v1/system/capabilities")
    assert r.status_code == 200
    feats = r.json()["features"]
    fs = feats["face_swap"]
    assert fs["mode"] == "i2i_edit"
    assert fs["sku"] == "google/nano-banana-edit"
    assert "face-swap" in (fs.get("api") or fs.get("path") or "")
    pe = feats["prompt_extractor"]["social_page_urls"]
    assert pe["youtube"] is True
    assert pe["tiktok"] == "best_effort"
    pd = feats["performance_drive"]
    assert pd["mode"] == "motion_plus_optional_lipsync"
    assert "Act-One" in (pd.get("note") or "")


def test_social_resolve_youtube_oembed():
    from app.services.social_resolve import resolve_social_page_to_media, classify_social_platform

    assert classify_social_platform("https://youtu.be/dQw4w9WgXcQ") == "youtube"
    out = asyncio.run(resolve_social_page_to_media("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
    assert out.get("ok") is True
    assert out.get("media_url", "").startswith("http")
    assert out.get("platform") == "youtube"


def test_extractor_youtube_page_resolves(client, auth_headers):
    r = client.post(
        "/api/v1/generate/extract-prompt",
        headers=auth_headers,
        data={
            "media_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "media_kind": "auto",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("prompt")
    assert (body.get("social") or {}).get("platform") == "youtube"


def test_extractor_tiktok_still_honest_on_block(client, auth_headers):
    r = client.post(
        "/api/v1/generate/extract-prompt",
        headers=auth_headers,
        data={"media_url": "https://www.tiktok.com/@x/video/123", "media_kind": "video"},
    )
    # May 400 (blocked/unresolved) — must not 500 or pretend success without media
    assert r.status_code in (200, 400)
    if r.status_code == 400:
        detail = str(r.json().get("detail") or "")
        assert detail  # honesty message present
    else:
        assert r.json().get("social")


def test_face_swap_api_contract(client, auth_headers):
    r = client.post(
        "/api/v1/face-swap",
        headers=auth_headers,
        json={
            "face_url": "https://example.com/face.png",
            "target_url": "https://example.com/target.png",
            "prompt": "seamless face swap",
        },
    )
    # 202 queued or 402 credits — not 404/500
    assert r.status_code in (202, 402), r.text
    if r.status_code == 202:
        body = r.json()
        assert body.get("task_id")
        assert body.get("mode") == "i2i_edit"
        assert "nano-banana" in (body.get("sku") or "")


def test_performance_api_contract(client, auth_headers):
    r = client.post(
        "/api/v1/performance",
        headers=auth_headers,
        json={
            "image_url": "https://example.com/a.png",
            "video_url": "https://example.com/b.mp4",
            "with_talk": True,
            "voice_text": "你好，欢迎来到 betty",
            "tier": "demo",
        },
    )
    assert r.status_code in (202, 402), r.text
    if r.status_code == 202:
        body = r.json()
        assert body.get("task_id")
        assert "Act-One" in (body.get("honesty") or "")
        assert body.get("estimated_cost_credits", 0) >= 10  # motion+lipsync


def test_kie_face_swap_method_exists():
    from app.adapters.kie_adapter import KieAdapter

    assert hasattr(KieAdapter(), "face_swap")


def test_face_swap_live_evidence_optional():
    """If a previous live probe wrote evidence, it must be ok."""
    p = Path(__file__).resolve().parents[1] / "fixtures" / "face_swap" / "last_run.json"
    if not p.is_file():
        return
    import json
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("ok") is True
    assert data.get("media_url")
