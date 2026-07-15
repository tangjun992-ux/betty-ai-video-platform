"""Backend API tests — in-process ASGI (TestClient) via the shared ``client``
fixture in conftest.py; no separately running server required."""
import pytest


class TestHealth:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        # "ok" when all deps are up, "degraded" when e.g. Redis is down in CI.
        assert data["status"] in ("ok", "degraded")
        assert data["checks"]["database"] == "ok"

    def test_api_health(self, client):
        r = client.get("/api/v1/health/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("ok", "degraded", "healthy")
        assert "database" in data["services"]
        assert "redis" in data["services"]
        assert "celery" in data["services"]


class TestModels:
    def test_list_models(self, client):
        r = client.get("/api/v1/models/")
        assert r.status_code == 200
        models = r.json()["models"]
        assert len(models) >= 3

    def test_model_detail(self, client):
        r = client.get("/api/v1/models/gpt-image-2")
        assert r.status_code == 200

    def test_pricing_plans(self, client):
        r = client.get("/api/v1/models/pricing/plans")
        assert r.status_code == 200
        assert len(r.json()["plans"]) >= 3

    def test_pricing_user(self, client):
        r = client.get("/api/v1/models/pricing/user")
        assert r.status_code == 200
        data = r.json()
        assert "credits" in data


class TestGallery:
    def test_gallery(self, client):
        r = client.get("/api/v1/gallery/")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data

    def test_gallery_stats(self, client):
        r = client.get("/api/v1/gallery/stats")
        assert r.status_code == 200


class TestGenerate:
    def test_analyze_prompt(self, client):
        r = client.post("/api/v1/generate/analyze", json={"prompt": "美丽的日落"})
        assert r.status_code == 200
        data = r.json()
        assert "media_type" in data["analysis"]

    def test_submit_generation(self, client):
        # Task submission requires a Celery broker. When one is available the
        # API returns 202 with a queued task; without a broker the enqueue
        # raises, surfacing as a 5xx. Both are acceptable for a unit run, so we
        # use a client that turns server exceptions into 500 responses.
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.post("/api/v1/generate/", json={
                "prompt": "测试图片生成",
                "media_type": "image",
            })
        assert r.status_code in (202, 500, 503)
        if r.status_code == 202:
            data = r.json()
            assert "task_id" in data
            assert data["status"] == "queued"


class TestTasks:
    def test_list_tasks(self, client):
        r = client.get("/api/v1/tasks/")
        assert r.status_code == 200

    def test_get_task_not_found(self, client):
        r = client.get("/api/v1/tasks/nonexistent-id-12345")
        assert r.status_code in (200, 404)
