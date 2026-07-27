"""Backend test configuration."""
import pytest
import httpx

BASE_URL = "http://localhost:8000"


@pytest.fixture
def client():
    """HTTP client for API testing."""
    return httpx.Client(base_url=BASE_URL, timeout=10)


@pytest.fixture
def async_client():
    """Async HTTP client for API testing."""
    return httpx.AsyncClient(base_url=BASE_URL, timeout=10)
