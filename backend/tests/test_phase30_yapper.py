"""Phase 30 — staging checkout smoke (checkout → webhook → credits)."""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def _guest_user_id(guest_token: str) -> int:
    from app.db import async_session
    from app.services.guest import get_or_create_guest_user

    async with async_session() as db:
        uid = await get_or_create_guest_user(db, guest_token)
        await db.commit()
        return uid


def test_staging_checkout_smoke_dev_grant():
    from app.db import async_session
    from app.services.staging_checkout import run_staging_checkout_smoke
    from app.config import settings

    async def _run():
        gid = f"p30-dev-{os.urandom(4).hex()}"
        uid = await _guest_user_id(gid)
        async with async_session() as db:
            return await run_staging_checkout_smoke(db, uid)

    old_key = settings.STRIPE_API_KEY
    settings.STRIPE_API_KEY = ""
    try:
        result = asyncio.run(_run())
    finally:
        settings.STRIPE_API_KEY = old_key

    assert result["ok"] is True
    assert result["mode"] == "dev_grant"
    assert result["credits_delta"] > 0


def test_staging_checkout_smoke_stripe_webhook(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import settings

    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(settings, "STRIPE_API_KEY", "sk_test_p30")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_p30_checkout")
    monkeypatch.setattr(settings, "STRIPE_SUCCESS_URL", "http://localhost:3000/billing/success")
    monkeypatch.setattr(settings, "STRIPE_CANCEL_URL", "http://localhost:3000/pricing")

    gid = f"p30-stripe-{os.urandom(4).hex()}"
    c = TestClient(app)
    c.get("/api/v1/billing/summary", headers={"X-Guest-Id": gid})
    r = c.post("/api/v1/billing/staging-checkout-smoke", headers={"X-Guest-Id": gid})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert body.get("mode") == "stripe_webhook"
    assert body.get("credits_delta", 0) > 0


def test_staging_checkout_smoke_endpoint_dev():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import settings

    old = settings.STRIPE_API_KEY
    settings.STRIPE_API_KEY = ""
    try:
        c = TestClient(app)
        gid = f"p30-api-{os.urandom(4).hex()}"
        r = c.post("/api/v1/billing/staging-checkout-smoke", headers={"X-Guest-Id": gid})
        assert r.status_code == 200
        assert r.json()["ok"] is True
    finally:
        settings.STRIPE_API_KEY = old


def test_staging_checkout_e2e_spec_exists():
    from pathlib import Path
    assert (Path(__file__).resolve().parents[2] / "frontend" / "e2e" / "staging-checkout-flow.spec.ts").is_file()
