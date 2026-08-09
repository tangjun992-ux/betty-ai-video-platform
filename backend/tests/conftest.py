"""Backend test configuration — DB bootstrap + in-process API client."""
from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="session", autouse=True)
def _ensure_db_tables():
    """Create ORM tables once per session so TestClient routes can persist rows."""
    from app.db import init_db

    asyncio.run(init_db())


@pytest.fixture
def client():
    """In-process FastAPI client (preferred — no external server required)."""
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def async_client():
    """Async HTTP client for optional live-server integration tests."""
    return httpx.AsyncClient(base_url=BASE_URL, timeout=10)
