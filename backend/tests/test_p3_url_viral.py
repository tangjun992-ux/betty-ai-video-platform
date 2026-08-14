"""P3 — URL-to-Viral structure: TikTok oEmbed + placement beats (honest)."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers(client: TestClient):
    email = f"p3_{uuid.uuid4().hex[:8]}@test.local"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "username": f"p3{uuid.uuid4().hex[:6]}"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_viral_spec_tiktok(client: TestClient):
    r = client.get("/api/v1/generate/viral-spec?platform=tiktok")
    assert r.status_code == 200, r.text
    body = r.json()
    spec = body["spec"]
    assert spec["placement"] == "tiktok"
    assert spec["aspect"] == "9:16"
    assert len(spec["beats_template"]) == 3
    assert "不是原片" in (spec.get("honesty") or body.get("honesty") or "")
    plats = {p["platform"]: p["resolver"] for p in body["platforms"]}
    assert plats["tiktok"] == "oembed"
    assert plats["youtube"] == "oembed"
    assert plats["instagram"] == "best_effort"


def test_viral_structure_unit():
    from app.services.viral_structure import build_viral_structure, infer_placement

    assert infer_placement("youtube", "https://www.youtube.com/shorts/abc") == "youtube_shorts"
    assert infer_placement("youtube", "https://www.youtube.com/watch?v=x", duration=90) == "youtube_landscape"
    assert infer_placement("tiktok", "https://www.tiktok.com/@a/video/1") == "tiktok"
    viral = build_viral_structure(
        platform="tiktok",
        source_url="https://www.tiktok.com/@a/video/1",
        title="POV: morning coffee",
        author="demo",
        prompt="cinematic coffee pour, steam, close-up",
        duration=12,
        style_tags=["cinematic"],
        camera="handheld",
        mood="warm",
        thumbnail_url="https://cdn.example.com/t.jpg",
        source="tiktok_oembed",
    )
    assert viral["placement"] == "tiktok"
    assert viral["aspect"] == "9:16"
    assert viral["duration_sec"] == 12
    assert len(viral["beats"]) == 3
    assert viral["beats"][0]["key"] == "hook"
    assert "不是原片" in viral["honesty"]
    q = viral["create_query"]["video"]
    assert "shot=" in q
    assert "aspect=9" in q or "aspect=9%3A16" in q
    assert "ref=" in q


def test_tiktok_oembed_builds_viral(client: TestClient, auth_headers, monkeypatch):
    async def fake_resolve(url: str):
        return {
            "ok": True,
            "platform": "tiktok",
            "media_url": "https://cdn.example.com/tt.jpg",
            "media_kind": "image",
            "title": "POV: morning coffee ritual",
            "author": "demo_creator",
            "source": "tiktok_oembed",
            "honesty": "TikTok 官方 oEmbed（标题+封面，非原片视频流）。",
        }

    async def fake_extract(media_url, **kwargs):
        return {
            "mode": "heuristic",
            "media_kind": "image",
            "media_url": media_url,
            "prompt": "cinematic coffee pour, steam rising, close-up",
            "style_tags": ["cinematic"],
            "subjects": ["coffee"],
            "camera": "close-up",
            "mood": "warm",
            "media_type_hint": "video",
            "meta": {},
            "honesty": "local heuristic fallback",
        }

    monkeypatch.setattr("app.services.social_resolve.resolve_social_page_to_media", fake_resolve)
    monkeypatch.setattr("app.services.prompt_extract.extract_prompt_from_media", fake_extract)

    r = client.post(
        "/api/v1/generate/extract-prompt",
        headers=auth_headers,
        data={"media_url": "https://www.tiktok.com/@demo/video/1234567890123456789", "media_kind": "auto"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] != "vision" or "tiktok" not in body["prompt"].lower()
    social = body.get("social") or {}
    assert social.get("platform") == "tiktok"
    assert social.get("source") == "tiktok_oembed"
    viral = body.get("viral") or {}
    assert viral.get("placement") == "tiktok"
    assert len(viral.get("beats") or []) == 3
    assert "不是原片" in (viral.get("honesty") or "")
    assert "shot=" in (body.get("create_links") or {}).get("video", "")


def test_tiktok_oembed_metadata_only(client: TestClient, auth_headers, monkeypatch):
    async def fake_resolve(url: str):
        return {
            "ok": True,
            "platform": "tiktok",
            "media_url": "",
            "title": "Day 7 of building in public",
            "author": "indie",
            "source": "tiktok_oembed",
            "honesty": "TikTok 官方 oEmbed（标题+封面，非原片视频流）。",
        }

    monkeypatch.setattr("app.services.social_resolve.resolve_social_page_to_media", fake_resolve)
    r = client.post(
        "/api/v1/generate/extract-prompt",
        headers=auth_headers,
        data={"media_url": "https://www.tiktok.com/@indie/video/1", "media_kind": "video"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "metadata"
    assert "Day 7" in body["prompt"]
    assert body["viral"]["beats"]
    assert "未下载原片" in (body.get("honesty") or "")


def test_tiktok_unresolved_still_honest(client: TestClient, auth_headers, monkeypatch):
    async def fake_resolve(url: str):
        return {
            "ok": False,
            "platform": "tiktok",
            "honesty": "TikTok 官方 oEmbed 未返回标题/封面，yt-dlp 回落也失败。请上传文件。",
        }

    monkeypatch.setattr("app.services.social_resolve.resolve_social_page_to_media", fake_resolve)
    r = client.post(
        "/api/v1/generate/extract-prompt",
        headers=auth_headers,
        data={"media_url": "https://www.tiktok.com/@x/video/123", "media_kind": "video"},
    )
    assert r.status_code == 400
    assert r.json().get("detail")


def test_capabilities_url_to_viral(client: TestClient):
    r = client.get("/api/v1/system/capabilities")
    assert r.status_code == 200
    feats = r.json()["features"]
    pe = feats["prompt_extractor"]["social_page_urls"]
    assert pe["youtube"] is True
    assert pe["tiktok"] == "oembed"
    assert pe["instagram"] == "best_effort"
    u2v = feats["url_to_viral"]
    assert u2v["mode"] == "oembed_plus_placement_beats"
    assert "/generate/viral-spec" in u2v["api"]
    assert "不是原片" in (u2v.get("note") or "")


def test_file_extract_still_has_viral(client: TestClient, auth_headers):
    from pathlib import Path

    still = Path(__file__).resolve().parents[1] / "fixtures" / "motion" / "still.png"
    if not still.is_file():
        pytest.skip("still.png fixture missing")
    r = client.post(
        "/api/v1/generate/extract-prompt",
        headers=auth_headers,
        files={"media_file": ("still.png", still.read_bytes(), "image/png")},
        data={"media_kind": "image", "target_platform": "tiktok"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("prompt")
    assert body["viral"]["placement"] == "tiktok"
    assert len(body["viral"]["beats"]) == 3
