"""Gateway Admin API integration tests."""
from __future__ import annotations

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


@pytest.fixture(scope="module", autouse=True)
def _init_db():
    from app.db import init_db
    asyncio.run(init_db())


@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)


def _make_user(client: TestClient, *, admin: bool = False) -> dict:
    email = f"gw_{uuid.uuid4().hex[:8]}@test.local"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "username": f"g{uuid.uuid4().hex[:6]}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    user_id = body["user"]["id"]
    if admin:
        from app.tasks.task_db import get_db_url_sync
        engine = create_engine(get_db_url_sync())
        with Session(engine) as session:
            session.execute(
                text("UPDATE users SET is_admin = 1 WHERE id = :id"),
                {"id": user_id},
            )
            session.commit()
    return {"Authorization": f"Bearer {body['access_token']}"}


def test_gateway_health_public(client: TestClient):
    r = client.get("/api/v1/gateway/health")
    assert r.status_code == 200
    data = r.json()
    assert "enabled" in data
    assert "route_count" in data


def test_gateway_status_requires_admin(client: TestClient):
    user_headers = _make_user(client, admin=False)
    r = client.get("/api/v1/admin/gateway/status", headers=user_headers)
    assert r.status_code == 403

    admin_headers = _make_user(client, admin=True)
    r = client.get("/api/v1/admin/gateway/status", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "routes" in data
    assert "registry" in data


def test_gateway_kill_switch_audit(client: TestClient):
    admin_headers = _make_user(client, admin=True)
    r = client.post(
        "/api/v1/admin/gateway/kill-switch",
        headers=admin_headers,
        json={"active": True},
    )
    assert r.status_code == 200
    assert r.json()["kill_switch"] is True

    r2 = client.post(
        "/api/v1/admin/gateway/kill-switch",
        headers=admin_headers,
        json={"active": False},
    )
    assert r2.status_code == 200
    assert r2.json()["kill_switch"] is False


def test_gateway_reload_routes(client: TestClient):
    admin_headers = _make_user(client, admin=True)
    r = client.post("/api/v1/admin/gateway/reload", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["route_count"] >= 20
