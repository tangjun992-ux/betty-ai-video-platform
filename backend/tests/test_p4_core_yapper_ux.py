"""P4 — core Yapper UX: pricing limits contract + video-idea fill-in source."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.services.concurrency import PLAN_CONCURRENCY
from app.api.pricing import PLAN_INCLUDED_SEATS, plan_limit_fields


ROOT = Path(__file__).resolve().parents[2]


def test_plan_limit_fields_match_yapper_table():
    expected = {
        "starter": (4, 0),
        "personal": (6, 0),
        "creator": (10, 2),
        "max": (40, 7),
        "pro": (40, 7),
    }
    for pid, (conc, seats) in expected.items():
        fields = plan_limit_fields(pid)
        assert fields["concurrent_generations"] == conc, pid
        assert fields["included_team_seats"] == seats, pid
        assert PLAN_CONCURRENCY[pid if pid != "pro" else "max"] == conc


def test_pricing_plans_expose_concurrent_and_seats():
    from app.main import app

    with TestClient(app) as client:
        r = client.get("/api/v1/pricing/plans")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "limits_honesty" in body
        assert "Stripe" in body["limits_honesty"] or "收款" in body["limits_honesty"]
        by_id = {p["id"]: p for p in body["plans"]}
        assert by_id["starter"]["concurrent_generations"] == 4
        assert by_id["starter"]["included_team_seats"] == 0
        assert by_id["personal"]["concurrent_generations"] == 6
        assert by_id["personal"]["included_team_seats"] == 0
        assert by_id["creator"]["concurrent_generations"] == 10
        assert by_id["creator"]["included_team_seats"] == 2
        assert by_id["max"]["concurrent_generations"] == 40
        assert by_id["max"]["included_team_seats"] == 7
        assert PLAN_INCLUDED_SEATS["creator"] == 2


def test_quote_and_capabilities_stay_fast_enough_for_ux():
    """Latency probe — catalog quote, not a live SLA claim."""
    import time
    from app.main import app

    with TestClient(app) as client:
        import uuid

        email = f"p4ux_{uuid.uuid4().hex[:8]}@test.local"
        username = f"p4ux{uuid.uuid4().hex[:6]}"
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Test1234!", "username": username},
        )
        assert reg.status_code == 200, reg.text
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        samples: list[float] = []
        for _ in range(3):
            t0 = time.perf_counter()
            q = client.post(
                "/api/v1/generate/quote",
                json={"prompt": "赛博朋克夜景", "media_type": "video", "duration": 5, "model": "seedance-2.0"},
                headers=headers,
            )
            samples.append((time.perf_counter() - t0) * 1000)
            assert q.status_code == 200, q.text
            assert q.json()["estimated_cost_credits"] >= 1

        t0 = time.perf_counter()
        caps = client.get("/api/v1/system/capabilities")
        cap_ms = (time.perf_counter() - t0) * 1000
        assert caps.status_code == 200
        # In-process TestClient; 800ms is a generous UX budget, not a production SLA.
        assert min(samples) < 800, samples
        assert cap_ms < 800, cap_ms


def test_video_page_ideas_fill_composer_not_agent_only():
    page = (ROOT / "frontend/src/app/create/video/page.tsx").read_text(encoding="utf-8")
    assert 'data-testid="video-ideas-row"' in page
    assert 'data-testid={`video-idea-${idea.id}`}' in page or 'data-testid="video-idea-ugc"' in page
    assert "setPrompt(idea.prompt)" in page
    assert "setAspectRatio(idea.aspect)" in page
    # Must not be the old "Video ideas → /agent only" bounce.
    assert '{ label: en ? "Video ideas" : "视频灵感", href: "/agent" }' not in page
    assert "VIDEO_IDEAS" in page
