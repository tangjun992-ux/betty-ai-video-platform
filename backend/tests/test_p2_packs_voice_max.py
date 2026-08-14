"""P2 — photo pack quote/precheck, Max slider checkout, voice/TTS honesty."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _no_celery(monkeypatch):
    class Dummy:
        id = "celery-p2-fake"
    monkeypatch.setattr(
        "app.api.generate.generate_image_task.delay",
        lambda *args, **kwargs: Dummy(),
    )


@pytest.fixture
def auth(client: TestClient):
    email = f"p2_{uuid.uuid4().hex[:8]}@test.local"
    username = f"p2{uuid.uuid4().hex[:6]}"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "username": username},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    return {"headers": {"Authorization": f"Bearer {body['access_token']}"}}


def test_photo_packs_list_and_quote(client: TestClient, auth):
    listing = client.get("/api/v1/generate/packs")
    assert listing.status_code == 200, listing.text
    packs = listing.json()["packs"]
    ids = {p["id"] for p in packs}
    assert {"product", "headshots", "lifestyle", "brand"}.issubset(ids)
    product = next(p for p in packs if p["id"] == "product")
    assert product["cost_per"] >= 1
    assert "独立" in (product.get("honesty") or listing.json().get("honesty") or "")

    q = client.get("/api/v1/generate/pack/quote?pack_id=product&count=2", headers=auth["headers"])
    assert q.status_code == 200, q.text
    body = q.json()
    assert body["count"] == 2
    assert body["estimated_cost_credits"] == body["cost_per"] * 2
    assert body["resolved_model"]
    assert "affordable" in body


def test_photo_pack_dispatch_prechecks_and_creates_tasks(client: TestClient, auth):
    q = client.get("/api/v1/generate/pack/quote?pack_id=headshots&count=2", headers=auth["headers"])
    assert q.status_code == 200
    quote = q.json()
    if not quote.get("affordable"):
        pytest.skip("fixture user has fewer credits than pack quote")
    r = client.post(
        "/api/v1/generate/pack",
        json={"pack_id": "headshots", "subject": "一位工程师", "count": 2},
        headers=auth["headers"],
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["dispatched"] == 2
    assert len(body["items"]) == 2
    assert body["resolved_model"]
    assert all(it["status"] == "queued" for it in body["items"])


def test_photo_pack_402_when_batch_unaffordable(client: TestClient, auth, monkeypatch):
    async def zero(_bal):
        return 0
    monkeypatch.setattr("app.services.credits.available_personal_credits", zero)
    r = client.post(
        "/api/v1/generate/pack",
        json={"pack_id": "product", "subject": "香水", "count": 2},
        headers=auth["headers"],
    )
    assert r.status_code == 402, r.text


def test_max_slider_checkout_credits(client: TestClient, auth):
    plans = client.get("/api/v1/pricing/plans")
    assert plans.status_code == 200
    max_plan = next(p for p in plans.json()["plans"] if p["id"] == "max")
    assert "max_tiers" in max_plan
    assert 15000 in [t["credits"] for t in max_plan["max_tiers"]]

    from app.api.billing import CheckoutRequest, _resolve_purchase
    credits, price, label, extra = _resolve_purchase(
        CheckoutRequest(kind="plan", id="max", cycle="monthly", credits=15000)
    )
    assert extra.get("max_tier_credits") == 15000
    assert credits == 15000
    assert price == 99.99

    default_c, default_p, _, default_x = _resolve_purchase(
        CheckoutRequest(kind="plan", id="max", cycle="monthly")
    )
    assert default_c == 22500
    assert "max_tier_credits" not in default_x


def test_voice_and_pack_capabilities_honesty(client: TestClient):
    r = client.get("/api/v1/system/capabilities")
    assert r.status_code == 200
    feats = r.json()["features"]
    assert feats["photo_packs"]["mode"] == "batch_sku"
    vc = feats["voice_changer"]
    assert vc["mode"] == "tts_narration"
    assert "RVC" in vc["note"] or "变声" in vc["note"]
    assert feats["max_slider"]["available"] is True
    assert feats["team_seats"]["available"] is True


def test_credit_packs_include_max_tiers(client: TestClient):
    r = client.get("/api/v1/billing/credit-packs")
    assert r.status_code == 200
    d = r.json()
    assert d["packs"]
    assert d["team_seat_skus"]["seat_monthly"]["seats"] == 1
    assert any(t["credits"] == 22500 for t in d["max_tiers"])
