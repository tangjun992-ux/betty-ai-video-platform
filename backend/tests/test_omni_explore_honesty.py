"""Omni 一体 + Explore 飞轮 + 货架诚实 — contract tests."""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_upload_accepts_video_and_audio():
    from app.main import app

    c = TestClient(app)
    # tiny fake payloads — store_upload may write bytes as-is
    with patch("app.api.upload.store_upload") as su:
        class A:
            url = "/media/t.mp4"
            filename = "t.mp4"
            size_bytes = 12
            asset_id = "a1"

        async def _store(*_a, **_k):
            return A()

        su.side_effect = _store
        r = c.post(
            "/api/v1/upload",
            files={"file": ("clip.mp4", io.BytesIO(b"00fakevideo00"), "video/mp4")},
        )
    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "video"
    assert r.json()["url"]


def test_upload_rejects_exe():
    from app.main import app

    c = TestClient(app)
    r = c.post(
        "/api/v1/upload",
        files={"file": ("x.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )
    assert r.status_code == 400


def test_storyboard_plan_carries_omni_refs():
    from app.director import build_storyboard_plan

    plan = build_storyboard_plan(
        [
            {"prompt": "wide city dusk", "duration": 4},
            {"prompt": "close neon walk", "duration": 5},
        ],
        brief="夜景",
        reference_images=["https://cdn.example.com/a.png", "https://cdn.example.com/b.png"],
        reference_videos=["https://cdn.example.com/m.mp4"],
        reference_audios=["https://cdn.example.com/v.wav"],
        omni=True,
        generate_audio=True,
        with_compose=False,
    )
    videos = [s for s in plan.steps if s.action == "video"]
    assert len(videos) == 2
    assert videos[0].model_id == "seedance-2.0"
    p0 = videos[0].params
    assert p0.get("omni") is True
    assert p0.get("generate_audio") is True
    assert p0.get("reference_images") == [
        "https://cdn.example.com/a.png",
        "https://cdn.example.com/b.png",
    ]
    assert p0.get("reference_videos") == ["https://cdn.example.com/m.mp4"]
    assert p0.get("reference_audios") == ["https://cdn.example.com/v.wav"]
    assert p0.get("image_url") == "https://cdn.example.com/a.png"


def test_storyboard_api_accepts_omni_payload():
    from app.main import app

    c = TestClient(app)
    with patch("app.api.director._dry_run_default", return_value=True), \
         patch("app.tasks.director_tasks.run_director") as rd:
        rd.delay = MagicMock()
        r = c.post(
            "/api/v1/director/storyboard",
            headers={"X-Guest-Id": "omni-storyboard-guest"},
            json={
                "shots": [{"prompt": "shot one", "duration": 3}],
                "brief": "omni test",
                "reference_images": ["https://cdn.example.com/x.png"],
                "reference_videos": ["https://cdn.example.com/y.mp4"],
                "omni": True,
                "generate_audio": True,
                "dry_run": True,
                "async_mode": True,
                "with_compose": False,
            },
        )
    assert r.status_code == 200, r.text
    steps = r.json()["plan"]["steps"]
    vid = next(s for s in steps if s["action"] == "video")
    assert vid["params"].get("omni") is True
    assert "reference_videos" in vid["params"]


def test_seed_marker_v2_visible_in_gallery():
    from app.api.gallery import _is_seed_item

    assert _is_seed_item({"seed_marker": "demo_seed_v2"}) is True
    assert _is_seed_item({"seed_marker": "demo_seed_v1"}) is True
    assert _is_seed_item({"seed_marker": "other"}) is False


def test_gallery_item_key_stable_and_remix():
    from app.main import app
    from app.models.task import Task
    from app.config import settings
    import json
    import uuid
    from datetime import datetime, timezone
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    c = TestClient(app)
    tid = uuid.uuid4().hex
    url = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(url)
    with Session(engine) as session:
        t = Task(
            task_id=tid,
            user_id=0,
            prompt="explore remix fixture city neon",
            media_type="image",
            quality="high",
            requested_model="auto",
            selected_model="nano-banana",
            parameters={
                "seed_marker": "demo_seed_v2",
                "share_public": True,
                "routing_info": json.dumps({"detected_styles": ["cinematic"]}),
            },
            status="completed",
            progress=100,
            results=[{"type": "image", "url": "https://cdn.example.com/explore.png", "model": "nano-banana"}],
            estimated_cost=2,
            actual_cost=2,
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        session.add(t)
        session.commit()

    listing = c.get("/api/v1/gallery/?limit=80&include_seed=true")
    assert listing.status_code == 200
    items = listing.json().get("items") or []
    hit = next((i for i in items if i.get("task_id") == tid), None)
    assert hit is not None, "seed_v2 item must appear in explore"
    assert hit["id"] == f"{tid}_0"
    assert hit.get("is_seed") is True

    remix = c.post(f"/api/v1/gallery/{hit['id']}/remix")
    assert remix.status_code == 200, remix.text
    body = remix.json()
    assert body.get("prompt")
    assert body.get("media_url")
    assert body.get("create_path")


def test_capabilities_omni_storyboard_note():
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/capabilities")
    assert r.status_code == 200
    feats = r.json()["features"]
    assert "seedance_omni" in feats
    assert "storyboard_omni" in (feats["seedance_omni"].get("inputs") or [])


def test_dashboard_models_no_lab_brands():
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/dashboard/dashboard")
    assert r.status_code == 200, r.text
    names = " ".join(m["name"] for m in r.json().get("models") or [])
    assert "Veo" not in names
    assert "Sora" not in names
    assert "Seedance" in names
