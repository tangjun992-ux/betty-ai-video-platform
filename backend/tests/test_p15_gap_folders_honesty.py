"""P1.5 gap closure — folders CRUD, explore honesty, face-swap templates, stripe honesty."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth(client: TestClient):
    email = f"p15_{uuid.uuid4().hex[:8]}@test.local"
    username = f"p15{uuid.uuid4().hex[:6]}"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "username": username},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    return {
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "user_id": int(body["user"]["id"]),
    }


def _sync_session():
    from app.config import settings
    url = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
    return Session(create_engine(url))


def test_gallery_stats_honesty_not_millions(client: TestClient):
    r = client.get("/api/v1/gallery/stats")
    assert r.status_code == 200, r.text
    d = r.json()
    assert "honesty" in d
    assert "百万" in d["honesty"] or "completed" in d["honesty"]
    assert "seed_items" in d and "community_items" in d
    listing = client.get("/api/v1/gallery/?include_seed=true&limit=8")
    assert listing.status_code == 200
    body = listing.json()
    assert body.get("honesty")
    assert "seed_total" in body


def test_library_folder_crud_and_batch_move(client: TestClient, auth):
    headers = auth["headers"]
    uid = auth["user_id"]
    created = client.post("/api/v1/library/folders", json={"name": "Campaign A"}, headers=headers)
    assert created.status_code == 200, created.text
    assert created.json()["created"] is True

    listing = client.get("/api/v1/library/", headers=headers)
    assert listing.status_code == 200
    names = [f["name"] if isinstance(f, dict) else f for f in (listing.json().get("folder_catalog") or listing.json().get("folders") or [])]
    assert "Campaign A" in names
    catalog = client.get("/api/v1/library/folders", headers=headers)
    assert catalog.status_code == 200, catalog.text
    assert "Campaign A" in [f["name"] for f in catalog.json()["folders"]]

    with _sync_session() as s:
        from app.models.task import Task
        tid = uuid.uuid4().hex
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        s.add(Task(
            task_id=tid, user_id=uid, prompt="folder fixture", media_type="image",
            quality="high", requested_model="auto", selected_model="nano-banana",
            parameters={"share_public": False}, status="completed", progress=100,
            results=[{"type": "image", "url": "https://cdn.example.com/f.png", "model": "nano-banana"}],
            estimated_cost=2, created_at=now, completed_at=now,
        ))
        s.commit()

    items = client.get("/api/v1/library/?limit=96", headers=headers).json()["items"]
    gen = next(i for i in items if i.get("task_id") == tid)

    moved = client.post(
        "/api/v1/library/batch-folder",
        json={"ids": [gen["id"]], "folder": "Campaign A"},
        headers=headers,
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["ok"] == 1

    filtered = client.get("/api/v1/library/?folder=Campaign%20A", headers=headers)
    assert filtered.status_code == 200
    assert any(i["id"] == gen["id"] for i in filtered.json()["items"])

    renamed = client.patch(
        "/api/v1/library/folders",
        json={"name": "Campaign A", "rename": "Campaign B"},
        headers=headers,
    )
    assert renamed.status_code == 200, renamed.text
    b_items = client.get("/api/v1/library/?folder=Campaign%20B", headers=headers).json()["items"]
    assert any(i["id"] == gen["id"] for i in b_items)

    deleted = client.delete("/api/v1/library/folders?name=Campaign%20B", headers=headers)
    assert deleted.status_code == 200, deleted.text
    after = client.get("/api/v1/library/?folder=Campaign%20B", headers=headers).json()["items"]
    assert after == []
    still = client.get("/api/v1/library/?limit=96", headers=headers).json()["items"]
    leftover = next(i for i in still if i["id"] == gen["id"])
    assert not leftover.get("folder")


def test_face_swap_templates_contract(client: TestClient):
    r = client.get("/api/v1/face-swap/templates")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["mode"] == "i2i_edit"
    assert "nano-banana" in d["sku"]
    assert "InsightFace" in d["honesty"]
    ids = {t["id"] for t in d["templates"]}
    assert {"poster", "cyber", "shortcover", "holiday"}.issubset(ids)
    assert len(d["templates"]) >= 8


def test_stripe_status_honesty_without_keys(client: TestClient):
    r = client.get("/api/v1/billing/stripe-status")
    assert r.status_code == 200, r.text
    d = r.json()
    assert "honesty" in d
    assert d["subscription_ready"] is False or d["api_key_configured"] is True
    if not d.get("api_key_configured"):
        assert "Stripe" in d["honesty"] or "收款" in d["honesty"]
