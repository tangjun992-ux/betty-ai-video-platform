"""Integration-style API tests — skip when backend is not running."""
import pytest
from httpx import Client

BASE_URL = "http://localhost:8000"


def _server_up() -> bool:
    try:
        return Client(base_url=BASE_URL, timeout=2).get("/health").status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _server_up(), reason="backend server not running on :8000")


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
        assert r.json().get("status") in ("ok", "degraded")


class TestModels:
    def test_list_models(self, client):
        r = client.get("/api/v1/models/")
        assert r.status_code == 200
        data = r.json()
        models = data.get("models") if isinstance(data, dict) else data
        assert len(models) >= 3
        assert "active_count" in data

    def test_model_detail(self, client):
        r = client.get("/api/v1/models/gpt-image-2")
        assert r.status_code == 200

    def test_pricing_plans(self, client):
        r = client.get("/api/v1/models/pricing/plans")
        assert r.status_code == 200
        body = r.json()
        plans = body.get("plans", body) if isinstance(body, dict) else body
        assert len(plans) >= 3

    def test_pricing_user(self, client):
        r = client.get("/api/v1/models/pricing/user")
        assert r.status_code == 200
        data = r.json()
        assert "credits" in data or "balance" in data
