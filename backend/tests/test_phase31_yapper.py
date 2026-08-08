"""Phase 31 — staging runbook auto-execute."""
import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_execute_staging_runbook_shape():
    from app.db import async_session
    from app.services.staging_runbook_exec import execute_staging_runbook
    from app.config import settings

    async def _run():
        async with async_session() as db:
            return await execute_staging_runbook(db)

    old = settings.STRIPE_API_KEY
    settings.STRIPE_API_KEY = ""
    try:
        report = asyncio.run(_run())
    finally:
        settings.STRIPE_API_KEY = old

    assert "execute_ok" in report
    assert "results" in report
    assert report["steps_executed"] >= 3
    ids = {r["id"] for r in report["results"]}
    assert "checkout_smoke" in ids
    assert "acceptance" in ids


def test_runbook_execute_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import settings

    old = settings.STRIPE_API_KEY
    settings.STRIPE_API_KEY = ""
    try:
        c = TestClient(app)
        r = c.post("/api/v1/system/staging-runbook-execute")
        assert r.status_code == 200
        body = r.json()
        assert "results" in body
    finally:
        settings.STRIPE_API_KEY = old


def test_runbook_execute_stripe_path(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import settings

    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(settings, "STRIPE_API_KEY", "sk_test_p31")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_p31_exec")
    monkeypatch.setattr(settings, "STRIPE_PRICE_STARTER_MONTHLY", "price_p31")
    monkeypatch.setattr(settings, "STRIPE_SUCCESS_URL", "http://localhost:3000/billing/success")
    monkeypatch.setattr(settings, "STRIPE_CANCEL_URL", "http://localhost:3000/pricing")

    c = TestClient(app)
    r = c.post("/api/v1/system/staging-runbook-execute")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("steps_executed", 0) >= 5
    checkout = next(x for x in body["results"] if x["id"] == "checkout_smoke")
    assert checkout.get("ok") is True


def test_runbook_execute_script():
    script = Path(__file__).resolve().parents[1] / "scripts" / "staging_runbook_execute.py"
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(script), "--json-only"],
        capture_output=True,
        text=True,
        cwd=str(script.parents[1]),
        env={**os.environ, "ENV": "test", "STRIPE_API_KEY": ""},
    )
    assert proc.returncode in (0, 1)
    data = json.loads(proc.stdout)
    assert "execute_ok" in data


def test_runbook_execute_e2e_spec():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[2] / "frontend" / "e2e" / "staging-go-live.spec.ts").read_text()
    assert "staging-runbook-execute" in text
