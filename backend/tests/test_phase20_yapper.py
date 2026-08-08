"""Phase 20 — Stripe staging readiness, invoice.paid, sync fallback, billing success E2E."""
import asyncio
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def _guest_user_id(guest_token: str) -> int:
    from app.db import async_session
    from app.services.guest import get_or_create_guest_user

    async with async_session() as db:
        uid = await get_or_create_guest_user(db, guest_token)
        await db.commit()
        return uid


def test_stripe_staging_readiness_shape():
    from app.services.stripe_ready import stripe_staging_readiness

    st = stripe_staging_readiness()
    assert "staging_ready" in st
    assert "checklist" in st
    assert len(st["checklist"]) >= 5
    assert "checkout.session.completed" in st["webhook_events"]
    assert "invoice.paid" in st["webhook_events"]


def test_billing_staging_readiness_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/billing/staging-readiness")
    assert r.status_code == 200
    assert "checklist" in r.json()


def test_readiness_includes_stripe_staging():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/readiness")
    assert r.status_code == 200
    assert "staging" in r.json()["stripe"]


def test_stripe_invoice_paid_renewal(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import settings

    monkeypatch.setattr(settings, "ENV", "development")
    gid = f"p20-inv-{os.urandom(4).hex()}"
    c = TestClient(app)
    c.get("/api/v1/billing/summary", headers={"X-Guest-Id": gid})
    user_id = asyncio.run(_guest_user_id(gid))
    before = c.get("/api/v1/billing/summary", headers={"X-Guest-Id": gid}).json()

    wh = c.post(
        "/api/v1/billing/stripe/webhook",
        content=json.dumps({
            "type": "invoice.paid",
            "data": {
                "object": {
                    "id": "in_test_p20",
                    "lines": {
                        "data": [{
                            "metadata": {"id": "starter", "user_id": str(user_id)},
                        }],
                    },
                },
            },
        }),
        headers={"Content-Type": "application/json"},
    )
    assert wh.status_code == 200, wh.text
    body = wh.json()
    assert body.get("received") is True
    assert body.get("renewed") == "starter"
    assert body.get("balance", 0) >= before.get("credits", 0)


def test_stripe_sync_session_fallback(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import settings

    monkeypatch.setattr(settings, "STRIPE_API_KEY", "sk_test_phase20")
    monkeypatch.setattr(settings, "STRIPE_PRICE_STARTER_MONTHLY", "price_starter_test")
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(settings, "STRIPE_SUCCESS_URL", "http://localhost:3000/billing/success")
    monkeypatch.setattr(settings, "STRIPE_CANCEL_URL", "http://localhost:3000/pricing")

    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.create.return_value = SimpleNamespace(
        url="https://checkout.stripe.test/cs_test_p20",
    )

    gid = f"p20-sync-{os.urandom(4).hex()}"
    with patch.dict(sys.modules, {"stripe": mock_stripe}):
        c = TestClient(app)
        ck = c.post("/api/v1/billing/checkout", headers={"X-Guest-Id": gid}, json={
            "kind": "pack", "id": "pack_mini", "cycle": "monthly", "quantity": 1,
        })
        assert ck.status_code == 200, ck.text
        order_no = ck.json()["order_no"]
        session_id = "cs_test_sync_p20"
        before = c.get("/api/v1/billing/summary", headers={"X-Guest-Id": gid}).json()

        mock_stripe.checkout.Session.retrieve.return_value = {
            "id": session_id,
            "payment_status": "paid",
            "metadata": {"order_no": order_no},
            "customer_details": {"email": "sync@test.example"},
        }

        sync = c.post(
            f"/api/v1/billing/stripe/sync?session_id={session_id}",
            headers={"X-Guest-Id": gid},
        )
        assert sync.status_code == 200, sync.text
        body = sync.json()
        assert body.get("synced") is True
        assert body.get("summary", {}).get("credits", 0) > before.get("credits", 0)


def test_billing_success_e2e_spec_exists():
    from pathlib import Path
    assert (Path(__file__).resolve().parents[2] / "frontend" / "e2e" / "billing-success.spec.ts").is_file()
