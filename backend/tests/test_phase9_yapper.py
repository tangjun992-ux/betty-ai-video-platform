"""Phase 9 — tool estimate API, billing summary plan, stripe sync."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_estimate_tool_lipsync_tiers():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.cost_estimate import estimate_tool

    demo_s, demo_c = estimate_tool(tool="lipsync", tier="demo")
    studio_s, studio_c = estimate_tool(tool="lipsync", tier="studio")
    assert demo_c == 4
    assert studio_c == 10
    assert studio_s >= demo_s

    c = TestClient(app)
    r = c.post("/api/v1/generate/estimate", json={"tool": "lipsync", "tier": "demo"})
    assert r.status_code == 200
    assert r.json()["estimated_cost_credits"] == demo_c


def test_estimate_tool_motion():
    from app.services.cost_estimate import estimate_tool

    credits = estimate_tool(tool="motion", tier="demo")[1]
    assert credits == 6


def test_estimate_tool_performance_with_talk():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    base = c.post("/api/v1/generate/estimate", json={"tool": "performance", "tier": "demo", "with_talk": False})
    talk = c.post("/api/v1/generate/estimate", json={"tool": "performance", "tier": "demo", "with_talk": True})
    assert base.status_code == 200 and talk.status_code == 200
    assert talk.json()["estimated_cost_credits"] == base.json()["estimated_cost_credits"] + 4


def test_billing_summary_includes_plan_and_role():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    headers = {"X-Guest-Id": "phase9-billing-summary-guest"}
    r = c.get("/api/v1/billing/summary", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "role" in data
    assert "plan" in data
    assert "credits" in data


def test_estimate_unknown_tool_rejected():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.post("/api/v1/generate/estimate", json={"tool": "unknown-tool", "tier": "demo"})
    assert r.status_code == 400
