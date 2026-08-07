"""Phase 12 — URL-to-Viral structure, extract deep links, explore E2E."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_infer_viral_structure_from_social():
    from app.services.viral_structure import infer_viral_structure

    vs = infer_viral_structure(
        prompt="A cinematic coffee ad with warm lighting",
        social={"platform": "youtube", "title": "Amazing Coffee Routine"},
        style_tags=["cinematic", "landscape"],
        media_kind="video",
    )
    assert vs["hook"] == "Amazing Coffee Routine"
    assert vs["cta"]
    assert vs["banner_hint"]
    assert "coffee" in vs["agent_brief"].lower() or "Coffee" in vs["agent_brief"]


def test_infer_viral_structure_portrait_banner():
    from app.services.viral_structure import infer_viral_structure

    vs = infer_viral_structure(
        prompt="vertical short",
        style_tags=["portrait"],
        media_kind="image",
    )
    assert "9:16" in vs["banner_hint"] or "竖屏" in vs["banner_hint"]


def test_extract_prompt_includes_viral_structure():
    from fastapi.testclient import TestClient
    from app.main import app
    import uuid

    c = TestClient(app)
    email = f"phase12_{uuid.uuid4().hex[:8]}@test.local"
    reg = c.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "username": f"p12{uuid.uuid4().hex[:6]}"},
    )
    assert reg.status_code == 200, reg.text
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    r = c.post(
        "/api/v1/generate/extract-prompt",
        headers=headers,
        data={
            "media_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "media_kind": "auto",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("prompt")
    assert body.get("viral_structure")
    assert body["viral_structure"].get("hook")
    assert body["viral_structure"].get("cta")
    assert body.get("resolved_media_url")


def test_extract_resolved_media_url_top_level():
    from fastapi.testclient import TestClient
    from app.main import app
    import uuid

    c = TestClient(app)
    email = f"phase12b_{uuid.uuid4().hex[:8]}@test.local"
    reg = c.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "username": f"p12b{uuid.uuid4().hex[:6]}"},
    )
    assert reg.status_code == 200
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    r = c.post(
        "/api/v1/generate/extract-prompt",
        headers=headers,
        data={
            "media_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "media_kind": "auto",
        },
    )
    assert r.status_code == 200
    url = r.json().get("resolved_media_url") or ""
    assert url.startswith("http")


def test_readiness_smoke_section_unchanged():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/readiness")
    assert r.status_code == 200
    assert "smoke" in r.json()
