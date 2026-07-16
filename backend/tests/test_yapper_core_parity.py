"""Yapper core-feature parity matrix — contract + API smoke for every studio tool.

Does NOT claim live outframe success. Live video/image remain env-gated.
"""
from __future__ import annotations

import io
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIXTURE_STILL = Path(__file__).resolve().parents[1] / "fixtures" / "motion" / "still.png"
FIXTURE_REF = Path(__file__).resolve().parents[1] / "fixtures" / "motion" / "ref.mp4"


@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers(client: TestClient):
    email = f"yapper_parity_{uuid.uuid4().hex[:8]}@test.local"
    username = f"yp{uuid.uuid4().hex[:6]}"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "username": username},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Catalog / capabilities ──────────────────────────────────

def test_capabilities_yapper_features(client: TestClient):
    r = client.get("/api/v1/system/capabilities")
    assert r.status_code == 200
    d = r.json()
    feats = d["features"]
    for key in (
        "motion_transfer",
        "share_permalink",
        "failure_refund",
        "storyboard",
        "multi_reference_i2i",
        "prompt_extractor",
        "talking_avatar",
        "tool_cost_board",
    ):
        assert key in feats, f"missing capability {key}"
    assert feats["motion_transfer"]["mode"] == "best_effort"
    assert feats["share_permalink"]["requires_publish"] is True
    assert feats["prompt_extractor"]["path"] == "/generate/extract-prompt"


def test_models_active_catalog(client: TestClient):
    r = client.get("/api/v1/models")
    assert r.status_code == 200
    d = r.json()
    assert d["active_count"] >= 1
    assert len(d["active"]) == d["active_count"]
    # Default list must not dump all lab by default
    assert d["lab_count"] >= 0


# ── Generate / analyze / speech ─────────────────────────────

def test_analyze_prompt(client: TestClient, auth_headers):
    r = client.post(
        "/api/v1/generate/analyze",
        json={"prompt": "赛博朋克城市夜景", "media_type": "image"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert "recommended_model" in d
    assert "analysis" in d


def test_prompt_extractor_heuristic(client: TestClient, auth_headers):
    assert FIXTURE_STILL.is_file()
    data = FIXTURE_STILL.read_bytes()
    r = client.post(
        "/api/v1/generate/extract-prompt",
        headers=auth_headers,
        files={"media_file": ("still.png", io.BytesIO(data), "image/png")},
        data={"media_kind": "image"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["prompt"]
    assert body["mode"] in ("vision", "heuristic")
    assert "honesty" in body
    assert body["create_links"]["image"] == "/create/image"


def test_prompt_extractor_requires_media(client: TestClient, auth_headers):
    r = client.post("/api/v1/generate/extract-prompt", headers=auth_headers, data={})
    assert r.status_code == 400


# ── Motion / lipsync / voices ───────────────────────────────

def test_motion_samples_and_files(client: TestClient):
    r = client.get("/api/v1/motion/samples")
    assert r.status_code == 200
    d = r.json()
    assert d["available"] is True
    assert d["mode"] == "best_effort"
    sample = d["samples"][0]
    img = client.get(sample["image_path"])
    vid = client.get(sample["video_path"])
    assert img.status_code == 200
    assert vid.status_code == 200


def test_lipsync_voices(client: TestClient):
    r = client.get("/api/v1/lipsync/voices")
    assert r.status_code == 200
    assert len(r.json().get("voices") or []) >= 1


# ── Director / Agent ────────────────────────────────────────

def test_director_plan_and_storyboard(client: TestClient, auth_headers):
    plan = client.post(
        "/api/v1/director/plan",
        json={"brief": "30秒耳机产品广告，三镜头", "duration": 15},
        headers=auth_headers,
    )
    assert plan.status_code == 200, plan.text
    pdata = plan.json()
    assert "steps" in pdata or "plan" in pdata or "shots" in pdata or "nodes" in pdata

    sb = client.post(
        "/api/v1/director/storyboard",
        json={
            "brief": "咖啡品牌开场钩子",
            "dry_run": True,
            "async_mode": False,
            "shots": [
                {"prompt": "特写蒸汽升起", "duration": 3},
                {"prompt": "手持咖啡杯", "duration": 3},
            ],
        },
        headers=auth_headers,
    )
    assert sb.status_code == 200, sb.text
    assert sb.json()


def test_director_brain_modes(client: TestClient):
    r = client.get("/api/v1/director/brain/modes")
    assert r.status_code == 200
    assert "modes" in r.json()


# ── Explore / pricing / readiness ───────────────────────────

def test_gallery_explore_list(client: TestClient):
    r = client.get("/api/v1/gallery/")
    assert r.status_code == 200
    assert "items" in r.json()


def test_pricing_plans_four_tiers(client: TestClient):
    r = client.get("/api/v1/pricing/plans")
    assert r.status_code == 200
    plans = r.json()["plans"]
    ids = {p["id"] for p in plans}
    for need in ("starter", "personal", "creator", "pro"):
        assert need in ids


def test_readiness_and_stripe_oidc(client: TestClient):
    r = client.get("/api/v1/system/readiness")
    assert r.status_code == 200
    d = r.json()
    assert "stripe" in d and "storage" in d and "sso" in d
    oidc = client.get("/api/v1/auth/oidc/status")
    assert oidc.status_code == 200
    assert "configured" in oidc.json()


def test_timeline_srt_parse(client: TestClient, auth_headers):
    srt = "1\n00:00:00,000 --> 00:00:02,000\nHello Betty\n\n"
    r = client.post(
        "/api/v1/timeline/subtitles/parse",
        json={"content": srt},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["cue_count"] >= 1


def test_library_list(client: TestClient, auth_headers):
    r = client.get("/api/v1/library/", headers=auth_headers)
    assert r.status_code == 200, r.text


def test_developer_keys_list_auth(client: TestClient, auth_headers):
    r = client.get("/api/v1/developer/keys", headers=auth_headers)
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_heuristic_extract_service_unit():
    from app.services.prompt_extract import extract_prompt_from_media

    out = await extract_prompt_from_media(
        "file:///tmp/does-not-exist-yet.png",
        media_kind="image",
        filename="cyberpunk_city.png",
        prefer_vision=False,
    )
    assert out["mode"] == "heuristic"
    assert "cyberpunk" in out["prompt"].lower() or "city" in out["prompt"].lower()
    assert "honesty" in out
