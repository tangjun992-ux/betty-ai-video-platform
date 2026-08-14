"""P1 Yapper parity — Explore search/remix funnel + Library Today/batch + session_uid."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

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
    email = f"p1_{uuid.uuid4().hex[:8]}@test.local"
    username = f"p1{uuid.uuid4().hex[:6]}"
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
    engine = create_engine(url)
    return Session(engine)


def _add_task(
    session: Session,
    *,
    user_id: int,
    prompt: str,
    model: str = "nano-banana",
    media_type: str = "image",
    public: bool = True,
    seed: bool = False,
    cost: int = 2,
    params: dict | None = None,
    created_at: datetime | None = None,
    results: list | None = None,
) -> str:
    from app.models.task import Task

    tid = uuid.uuid4().hex
    now = created_at or datetime.now(timezone.utc)
    naive = now.replace(tzinfo=None) if now.tzinfo else now
    merged = {
        "share_public": public,
        "routing_info": json.dumps({"detected_styles": ["cinematic"]}),
        **(params or {}),
    }
    if seed:
        merged["seed_marker"] = "demo_seed_v2"
    t = Task(
        task_id=tid,
        user_id=user_id,
        prompt=prompt,
        media_type=media_type,
        quality="high",
        requested_model="auto",
        selected_model=model,
        parameters=merged,
        status="completed",
        progress=100,
        results=results or [{"type": media_type, "url": f"https://cdn.example.com/{tid}.png", "model": model}],
        estimated_cost=cost,
        actual_cost=cost,
        created_at=naive,
        completed_at=naive,
    )
    session.add(t)
    session.commit()
    return tid


def test_popular_score_weights():
    from app.api.gallery import _popular_score

    assert _popular_score(3, 1) == 7
    assert _popular_score(0, 4) == 4
    assert _popular_score(2, 0) > _popular_score(0, 3)


def test_infer_tool_buckets():
    from app.api.library import _infer_tool
    from app.models.task import Task

    t = Task(task_id="x", user_id=1, prompt="upscale this still", media_type="image")
    t.selected_model = "google/nano-banana-edit"
    t.parameters = {"operation": "upscale"}
    assert _infer_tool(t, {}) == "upscale"

    t2 = Task(task_id="y", user_id=1, prompt="walk cycle", media_type="video")
    t2.selected_model = "kling-3.0/motion-control"
    t2.parameters = {}
    assert _infer_tool(t2, {"model": "kling-3.0/motion-control"}) == "motion"

    t3 = Task(task_id="z", user_id=1, prompt="talking head", media_type="video")
    t3.selected_model = "kling/ai-avatar-pro"
    t3.parameters = {"lipsync_text": "你好"}
    assert _infer_tool(t3, {}) == "lipsync"

    t4 = Task(task_id="w", user_id=1, prompt="a cat", media_type="image")
    t4.selected_model = "nano-banana"
    t4.parameters = {}
    assert _infer_tool(t4, {}) is None


def test_is_today_window():
    from app.api.library import _is_today

    now = datetime(2026, 8, 14, 15, 0, tzinfo=timezone.utc)
    assert _is_today(now.isoformat(), now=now) is True
    old = now - timedelta(days=2)
    assert _is_today(old.isoformat(), now=now) is False


def test_gallery_search_q(client: TestClient):
    with _sync_session() as s:
        neon = _add_task(s, user_id=0, prompt="neon cyberpunk alley rain", model="nano-banana", seed=True)
        _add_task(s, user_id=0, prompt="quiet countryside sunrise", model="nano-banana", seed=True)

    hit = client.get("/api/v1/gallery/?q=cyberpunk&include_seed=true&limit=80")
    assert hit.status_code == 200, hit.text
    items = hit.json()["items"]
    assert any(i["task_id"] == neon for i in items)
    assert all("cyberpunk" in (i["prompt"] or "").lower() or "cyberpunk" in (i.get("style") or "") for i in items)

    miss = client.get("/api/v1/gallery/?q=zzzz-no-such-prompt-xyz&include_seed=true&limit=80")
    assert miss.status_code == 200
    assert miss.json()["items"] == []


def test_gallery_remix_count_and_popular(client: TestClient):
    with _sync_session() as s:
        liked = _add_task(s, user_id=0, prompt="liked city night", model="nano-banana", seed=True, cost=2)
        remixed = _add_task(s, user_id=0, prompt="remixed ocean dawn", model="nano-banana", seed=True, cost=9)

    liked_key = f"{liked}_0"
    remixed_key = f"{remixed}_0"
    like = client.post(f"/api/v1/gallery/{liked_key}/like")
    assert like.status_code == 200, like.text
    like2 = client.post(f"/api/v1/gallery/{liked_key}/like")
    assert like2.status_code == 200

    r1 = client.post(f"/api/v1/gallery/{remixed_key}/remix")
    assert r1.status_code == 200, r1.text
    assert r1.json()["remixes"] == 1
    r2 = client.post(f"/api/v1/gallery/{remixed_key}/remix")
    assert r2.json()["remixes"] == 2
    r3 = client.post(f"/api/v1/gallery/{remixed_key}/remix")
    assert r3.json()["remixes"] == 3
    r4 = client.post(f"/api/v1/gallery/{remixed_key}/remix")
    assert r4.json()["remixes"] == 4
    r5 = client.post(f"/api/v1/gallery/{remixed_key}/remix")
    assert r5.json()["remixes"] >= 5

    listing = client.get("/api/v1/gallery/?sort=popular&include_seed=true&limit=80")
    assert listing.status_code == 200
    items = listing.json()["items"]
    by_id = {i["task_id"]: i for i in items}
    assert remixed in by_id and liked in by_id
    assert by_id[remixed]["remixes"] >= 5
    assert by_id[liked]["likes"] >= 2
    # 5 remixes (score 5) vs 2 likes (score 4) → remixed ranks higher
    ids = [i["task_id"] for i in items if i["task_id"] in (liked, remixed)]
    assert ids[0] == remixed

    credits = client.get("/api/v1/gallery/?sort=credits&include_seed=true&limit=80")
    cred_items = credits.json()["items"]
    ocean = next(i for i in cred_items if i["task_id"] == remixed)
    city = next(i for i in cred_items if i["task_id"] == liked)
    assert ocean["credits_cost"] >= city["credits_cost"]

    share = client.get(f"/api/v1/gallery/share/{remixed}")
    assert share.status_code == 200
    assert share.json()["remixes"] >= 5


def test_library_today_tool_task_id(client: TestClient, auth):
    uid = auth["user_id"]
    headers = auth["headers"]
    now = datetime.now(timezone.utc)
    with _sync_session() as s:
        today_id = _add_task(
            s, user_id=uid, prompt="today talking avatar", model="kling/ai-avatar-pro",
            media_type="video", public=False, params={"lipsync_text": "hello", "duration": 5},
            created_at=now,
            results=[{"type": "video", "url": "https://cdn.example.com/today.mp4", "model": "kling/ai-avatar-pro"}],
        )
        _add_task(
            s, user_id=uid, prompt="old landscape", model="nano-banana",
            public=False, created_at=now - timedelta(days=3),
        )

    all_items = client.get("/api/v1/library/?limit=96", headers=headers)
    assert all_items.status_code == 200, all_items.text
    body = all_items.json()
    assert body["counts"]["today"] >= 1
    gen = next(i for i in body["items"] if i.get("task_id") == today_id)
    assert gen["id"].startswith("gen_")
    assert gen["tool"] == "lipsync"

    today = client.get("/api/v1/library/?period=today&limit=96", headers=headers)
    assert today.status_code == 200
    t_items = today.json()["items"]
    assert any(i.get("task_id") == today_id for i in t_items)
    assert all(_created_is_today(i["created_at"]) for i in t_items)

    lips = client.get("/api/v1/library/?tool=lipsync&limit=96", headers=headers)
    assert lips.status_code == 200
    assert all(i.get("tool") == "lipsync" for i in lips.json()["items"])
    assert any(i.get("task_id") == today_id for i in lips.json()["items"])


def _created_is_today(iso: str) -> bool:
    from app.api.library import _is_today
    return _is_today(iso)


def test_library_batch_delete_and_publish(client: TestClient, auth):
    uid = auth["user_id"]
    headers = auth["headers"]
    with _sync_session() as s:
        a = _add_task(s, user_id=uid, prompt="batch a", public=False)
        b = _add_task(s, user_id=uid, prompt="batch b", public=False)

    listing = client.get("/api/v1/library/?limit=96", headers=headers).json()
    ids = [i["id"] for i in listing["items"] if i.get("task_id") in (a, b)]
    assert len(ids) == 2

    pub = client.post("/api/v1/library/batch-publish", json={"ids": ids}, headers=headers)
    assert pub.status_code == 200, pub.text
    assert pub.json()["ok"] >= 1
    share = client.get(f"/api/v1/gallery/share/{a}")
    assert share.status_code == 200, share.text

    folder = client.patch(f"/api/v1/library/{ids[0]}/folder?folder=Campaign", headers=headers)
    assert folder.status_code == 200, folder.text
    assert folder.json().get("folder") == "Campaign"

    gone = client.post("/api/v1/library/batch-delete", json={"ids": ids}, headers=headers)
    assert gone.status_code == 200, gone.text
    assert gone.json()["ok"] == 2
    after = client.get("/api/v1/library/?limit=96", headers=headers).json()
    left = {i.get("task_id") for i in after["items"]}
    assert a not in left and b not in left


def test_generate_request_accepts_session_uid():
    from app.api.generate import GenerateRequest

    req = GenerateRequest(prompt="session bound clip", media_type="video", session_uid="abc123def456")
    assert req.session_uid == "abc123def456"


def test_session_uid_persisted_on_generate(client: TestClient, auth, monkeypatch):
    headers = auth["headers"]
    created = client.post(
        "/api/v1/director/sessions",
        json={"title": "P1 video session", "intent": "video_create", "status": "active"},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    uid = created.json()["session_uid"]

    class Dummy:
        id = "celery-dummy"

    monkeypatch.setattr("app.api.generate.generate_image_task.delay", lambda **k: Dummy())
    monkeypatch.setattr("app.api.generate.generate_video_task.delay", lambda **k: Dummy())

    async def _ok(*_a, **_k):
        class Snap:
            used = 1
            limit = 4
        return Snap()

    monkeypatch.setattr("app.services.concurrency.acquire_slot", _ok)

    r = client.post(
        "/api/v1/generate/",
        json={
            "prompt": "session bound neon street",
            "media_type": "image",
            "model": "nano-banana",
            "enhance_prompt": False,
            "session_uid": uid,
        },
        headers=headers,
    )
    assert r.status_code in (200, 202), r.text
    task_id = r.json()["task_id"]
    with _sync_session() as s:
        from app.models.task import Task
        t = s.query(Task).filter(Task.task_id == task_id).one()
        params = t.parameters if isinstance(t.parameters, dict) else json.loads(t.parameters or "{}")
        assert params.get("session_uid") == uid
