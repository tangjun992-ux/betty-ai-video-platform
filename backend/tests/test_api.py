"""Backend API 单元测试 — pytest + httpx"""
import pytest
from httpx import Client

BASE_URL = "http://localhost:8000"


@pytest.fixture
def client():
    return Client(base_url=BASE_URL, timeout=15)


class TestHealth:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"

    def test_api_health(self, client):
        r = client.get("/api/v1/health/")
        assert r.status_code == 200
        data = r.json()
        assert data["database"] == "healthy"
        assert data["redis"] in ("healthy", "connected")
        assert data["celery"] in ("healthy", "running")


class TestModels:
    def test_list_models(self, client):
        r = client.get("/api/v1/models/")
        assert r.status_code == 200
        models = r.json()
        assert len(models) >= 3

    def test_model_detail(self, client):
        r = client.get("/api/v1/models/gpt-image-2-text-to-image")
        assert r.status_code == 200

    def test_pricing_plans(self, client):
        r = client.get("/api/v1/models/pricing/plans")
        assert r.status_code == 200
        assert len(r.json()) >= 3

    def test_pricing_user(self, client):
        r = client.get("/api/v1/models/pricing/user")
        assert r.status_code == 200
        data = r.json()
        assert "balance" in data


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
        assert "media_type" in data

    def test_submit_generation(self, client):
        r = client.post("/api/v1/generate/", json={
            "prompt": "测试图片生成",
            "media_type": "image",
        })
        assert r.status_code == 202
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
