"""Backend test configuration.

Provides an in-process ASGI ``TestClient`` so API tests run against the FastAPI
app directly — no separately running ``uvicorn`` server required. Each test
session uses an isolated SQLite database with all tables created up-front.
"""
import os
import tempfile

import pytest

# Configure an isolated SQLite DB + local storage BEFORE importing the app,
# so module-level engine creation in app.db picks these up.
_TEST_DB = os.path.join(tempfile.gettempdir(), "betty_test_api.db")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TEST_DB}")
os.environ.setdefault("STORAGE_PATH", os.path.join(tempfile.gettempdir(), "betty-test-media"))
os.environ.setdefault("ENV", "test")


@pytest.fixture(scope="session")
def client():
    """In-process ASGI client (no live server needed).

    Creates all DB tables once, then yields a TestClient bound to the app.
    """
    import asyncio

    from fastapi.testclient import TestClient

    from app.db import init_db
    from app.main import app

    asyncio.get_event_loop().run_until_complete(init_db())

    with TestClient(app) as c:
        yield c
