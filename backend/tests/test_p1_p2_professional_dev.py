"""P1/P2 professional dev — explore pagination, samples, pack batch, teams seats."""
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
def auth(client: TestClient):
    email = f"p12_{uuid.uuid4().hex[:8]}@test.local"
    username = f"p{uuid.uuid4().hex[:6]}"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "username": username},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}}


def test_gallery_pagination_has_more(client: TestClient):
    r = client.get("/api/v1/gallery/?limit=2&offset=0")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "has_more" in body
    assert body["limit"] == 2
    assert isinstance(body["items"], list)


def test_gallery_remix_create_query(client: TestClient):
    listing = client.get("/api/v1/gallery/?limit=5")
    assert listing.status_code == 200
    items = listing.json().get("items") or []
    if not items:
        pytest.skip("no gallery items")
    item_key = items[0]["id"]
    remix = client.post(f"/api/v1/gallery/{item_key}/remix")
    assert remix.status_code == 200, remix.text
    data = remix.json()
    assert data.get("create_query")
    assert "prompt" in data["create_query"]


def test_face_swap_templates_visual_fields(client: TestClient):
    r = client.get("/api/v1/face-swap/templates")
    assert r.status_code == 200
    templates = r.json()["templates"]
    assert len(templates) >= 8
    assert all(t.get("icon") and t.get("color") for t in templates)


def test_motion_samples_presets(client: TestClient):
    r = client.get("/api/v1/motion/samples")
    assert r.status_code == 200
    samples = r.json().get("samples") or []
    ids = {s["id"] for s in samples}
    if not samples:
        pytest.skip("motion fixtures missing")
    assert "canonical-v1" in ids
    assert len(samples) >= 4


def test_performance_samples(client: TestClient):
    r = client.get("/api/v1/performance/samples")
    assert r.status_code == 200
    body = r.json()
    assert "motion_plus_optional_lipsync" in body.get("mode", "")
    assert body.get("honesty")


def test_lipsync_samples_and_slo(client: TestClient):
    r = client.get("/api/v1/lipsync/samples")
    assert r.status_code == 200
    assert "weekly_beat" in r.json()
    slo = client.get("/api/v1/system/slo")
    assert slo.status_code == 200
    assert "lipsync_fixture" in slo.json()


def test_pack_batch_status_not_found(client: TestClient, auth):
    r = client.get("/api/v1/generate/pack/pack-deadbeef/status", headers=auth["headers"])
    assert r.status_code == 404


def test_teams_seat_accounting_fields(client: TestClient, auth):
    """Creator role gets included_seats on team dict when team exists."""
    me = client.get("/api/v1/auth/me", headers=auth["headers"])
    if me.status_code != 200:
        pytest.skip("auth/me unavailable")
    role = me.json().get("role") or "guest"
    if role not in ("creator", "pro", "admin"):
        pytest.skip("user role cannot create team in this fixture")
    created = client.post(
        "/api/v1/teams/",
        headers=auth["headers"],
        json={"name": f"SeatTest {uuid.uuid4().hex[:6]}"},
    )
    if created.status_code == 403:
        pytest.skip("role cannot create team")
    assert created.status_code == 200, created.text
    body = created.json()
    assert "included_seats" in body
    assert "purchased_seats" in body
    assert "members_count" in body


def test_lipsync_weekly_task_registered():
    import app.tasks.health_tasks  # noqa: F401 — ensure task registration
    from celery_app import app as celery_app

    assert "app.tasks.health_tasks.smoke_live_lipsync_weekly" in celery_app.tasks


def test_commercial_open_honest_not_public(client: TestClient):
    r = client.get("/api/v1/system/commercial-open")
    assert r.status_code == 200, r.text
    d = r.json()
    assert "open_to_public" in d
    assert "blockers" in d
    assert "verdict" in d
    assert d["verdict"] in (
        "commercially_open",
        "studio_ready_not_commercially_open",
        "not_ready",
    )
    # This environment has no Stripe Key — must not claim public billing.
    if not d.get("subscription_ready"):
        assert d["open_to_public"] is False
        assert any(b.get("id") == "stripe" for b in d["blockers"])
    assert "不虚标" in (d.get("honesty") or "") or "active" in (d.get("honesty") or "")
    vs = d.get("vs_yapper") or {}
    assert vs.get("yapper_video_hero") == "seedance_2.5"
    assert vs.get("betty_video_hero") == "seedance_2.0"
    assert vs.get("betty_mcp_auth") == "api_key_not_oauth"
