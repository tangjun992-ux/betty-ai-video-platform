"""Concurrent first-touch requests for a new guest must not 500.

Reproduces the UNIQUE(user_balance.user_id) race: the first page load fires
several parallel API calls sharing one X-Guest-Id; each ran in its own session
and raced to INSERT the same guest user/balance.
"""
import secrets
import concurrent.futures

import pytest
from httpx import Client

BASE_URL = "http://localhost:8000"
API = f"{BASE_URL}/api/v1"


def _server_up() -> bool:
    try:
        return Client(base_url=BASE_URL, timeout=2).get("/health").status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _server_up(), reason="backend server not running on :8000"
)


def test_concurrent_new_guest_balance_no_500():
    guest = f"race-{secrets.token_hex(8)}"

    def hit(path: str) -> int:
        with Client(base_url=API, timeout=15, headers={"X-Guest-Id": guest}) as c:
            return c.get(path).status_code

    # Endpoints the frontend fires in parallel on first load, all touching
    # resolve_user_id → guest creation for a brand-new guest id.
    paths = [
        "/models/pricing/user",
        "/library/?media_type=video&limit=10",
        "/timeline/projects",
        "/models/pricing/user",
        "/library/?media_type=audio&limit=10",
        "/models/pricing/user",
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(paths)) as ex:
        codes = list(ex.map(hit, paths))

    assert all(c == 200 for c in codes), f"guest race produced non-200: {codes}"

    # Balance must be consistent afterwards.
    with Client(base_url=API, timeout=15, headers={"X-Guest-Id": guest}) as c:
        r = c.get("/models/pricing/user")
        assert r.status_code == 200
        body = r.json()
        assert body["credits"] >= 0
