"""P1 next-3: tool cost board, multi-ref/storyboard, Stripe Price IDs — verified."""
import asyncio
import inspect
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── 1) Tool cost vs upstream ─────────────────────────────────

def test_pricing_costs_exposes_tools_slice():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/pricing/costs?days=30")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "tools" in data
    assert "charged_credits" in data["tools"]
    assert "upstream_cost" in data["tools"]
    assert "margin_credits" in data["tools"]
    assert "charged_vs_upstream" in data


def test_edit_tool_persists_task_with_upstream_cost(tmp_path):
    """Successful edit writes Task(media_type=image_tool) with charged vs upstream."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.adapters.base import GenerationResult

    c = TestClient(app)
    headers = {"X-Guest-Id": "p1-cost-tool-guest-xx"}
    img = tmp_path / "src.png"
    img.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    fake = GenerationResult(
        media_url="https://example.com/edited.png",
        media_type="image",
        model="google/nano-banana-edit",
        cost=1.25,
    )

    with patch("app.api.generate.deduct_credits", new_callable=AsyncMock) as deduct, \
         patch("app.adapters.demo_provider.demo_mode_active", return_value=False), \
         patch("app.adapters.kie_adapter.KieAdapter") as Kie:
        deduct.return_value = True
        inst = Kie.return_value
        inst.upload_public_url = AsyncMock(return_value="https://cdn.example.com/src.png")
        inst.edit_image = AsyncMock(return_value=fake)
        inst.upscale_image = AsyncMock(return_value=fake)
        inst.remove_background = AsyncMock(return_value=fake)
        inst.extend_image = AsyncMock(return_value=fake)

        with patch("app.services.media_store.persist_results", side_effect=lambda xs: xs):
            r = c.post(
                "/api/v1/generate/edit",
                headers=headers,
                data={"operation": "edit", "prompt": "make it warmer"},
                files={"image_file": ("src.png", img.read_bytes(), "image/png")},
            )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("cost_credits") == 3
    assert body.get("cost") == 1.25
    assert "task_id" in body
    assert body.get("margin_credits") == pytest.approx(3 - 1.25)

    costs = c.get("/api/v1/pricing/costs?days=1")
    assert costs.status_code == 200
    tools = costs.json()["tools"]
    assert tools["count"] >= 1


# ── 2) Multi-ref / true storyboard ───────────────────────────

def test_generate_request_accepts_reference_images():
    from app.api.generate import GenerateRequest, execute_generation
    sig = inspect.signature(execute_generation)
    assert "req" in sig.parameters
    req = GenerateRequest(
        prompt="a cat",
        media_type="image",
        reference_images=["https://a.com/1.png", "https://a.com/2.png"],
    )
    assert req.reference_images and len(req.reference_images) == 2


def test_image_task_routes_refs_to_edit_image():
    """Celery image task must call edit_image when reference_images present."""
    from app.tasks import image_tasks

    calls = {}

    class FakeAdapter:
        async def edit_image(self, *, image_urls, prompt, image_size="auto", **kw):
            calls["edit"] = {"image_urls": image_urls, "prompt": prompt}
            from app.adapters.base import GenerationResult
            return GenerationResult(
                media_url="https://out.example/x.png", media_type="image",
                model="edit", cost=1.0,
            )

        async def generate_image(self, *a, **k):
            calls["gen"] = True
            raise AssertionError("should not t2i when refs present")

    with patch.object(image_tasks.generate_image_task, "update_state"), \
         patch.object(image_tasks, "_update_task"), \
         patch.object(image_tasks, "_broadcast_progress"), \
         patch("app.adapters.demo_provider.demo_mode_active", return_value=True), \
         patch("app.adapters.demo_provider.DemoAdapter", return_value=FakeAdapter()), \
         patch("app.services.media_store.persist_results", side_effect=lambda xs: xs), \
         patch("app.services.model_health.validate_generation_results", return_value=(True, "")), \
         patch("app.services.model_health.model_health") as mh:
        mh.record_success = MagicMock()
        out = image_tasks.generate_image_task.apply(
            args=["task-ref-1", "nano-banana", "edit me",
                  {"resolution": "1024x1024", "reference_images": ["https://a/1.png", "https://a/2.png"]}],
        ).get()
    assert out["status"] == "completed"
    assert "edit" in calls
    assert calls["edit"]["image_urls"] == ["https://a/1.png", "https://a/2.png"]
    assert "gen" not in calls


def test_build_storyboard_plan_real_steps():
    from app.director import build_storyboard_plan

    plan = build_storyboard_plan(
        [
            {"prompt": "wide establishing shot of a cafe", "duration": 4, "label": "镜头1"},
            {"prompt": "close-up of coffee pour", "duration": 5},
        ],
        brief="咖啡广告",
        ref_image_url="https://example.com/ref.png",
        with_compose=True,
    )
    assert plan.intent == "storyboard"
    video_steps = [s for s in plan.steps if s.action == "video"]
    assert len(video_steps) == 2
    assert video_steps[0].prompt == "wide establishing shot of a cafe"
    assert video_steps[0].params.get("duration") == 4
    assert video_steps[0].params.get("image_url") == "https://example.com/ref.png"
    assert video_steps[0].params.get("storyboard") is True
    # Second depends on first — true sequencing, not prompt stitch
    assert video_steps[1].depends_on == [video_steps[0].id]
    assert any(s.action == "compose" for s in plan.steps)


def test_storyboard_api_dry_run():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    headers = {"X-Guest-Id": "p1-storyboard-guest-01"}
    with patch("app.api.director._dry_run_default", return_value=True), \
         patch("app.tasks.director_tasks.run_director") as rd:
        rd.delay = MagicMock()
        r = c.post(
            "/api/v1/director/storyboard",
            headers=headers,
            json={
                "shots": [
                    {"prompt": "shot one city skyline at dusk", "duration": 3},
                    {"prompt": "shot two neon street walk", "duration": 4},
                ],
                "brief": "夜景短片",
                "dry_run": True,
                "async_mode": True,
            },
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["storyboard"] is True
    assert data["shot_count"] == 2
    assert data["dry_run"] is True
    assert data.get("job_id")
    plan = data["plan"]
    videos = [s for s in plan["steps"] if s["action"] == "video"]
    assert len(videos) == 2
    assert videos[0]["prompt"] != videos[1]["prompt"]


# ── 3) Stripe Price IDs ──────────────────────────────────────

def test_stripe_plan_price_map_covers_all_plans():
    from app.api.billing import _STRIPE_PLAN_PRICE, _stripe_line_item, CheckoutRequest
    from app.config import settings

    for plan in ("starter", "personal", "creator", "pro"):
        for cycle in ("monthly", "yearly"):
            assert (plan, cycle) in _STRIPE_PLAN_PRICE


def test_stripe_line_item_uses_starter_personal_price_ids(monkeypatch):
    from app.api import billing
    from app.api.billing import CheckoutRequest, _stripe_line_item
    from app.config import settings

    monkeypatch.setattr(settings, "STRIPE_PRICE_STARTER_MONTHLY", "price_starter_m")
    monkeypatch.setattr(settings, "STRIPE_PRICE_PERSONAL_YEARLY", "price_personal_y")

    starter = _stripe_line_item(
        CheckoutRequest(kind="plan", id="starter", cycle="monthly"),
        credits=100, price_usd=9.0, label="Starter",
    )
    assert starter == {"price": "price_starter_m", "quantity": 1}

    personal = _stripe_line_item(
        CheckoutRequest(kind="plan", id="personal", cycle="yearly"),
        credits=500, price_usd=99.0, label="Personal",
    )
    assert personal == {"price": "price_personal_y", "quantity": 1}

    # Without price id → price_data fallback
    monkeypatch.setattr(settings, "STRIPE_PRICE_CREATOR_MONTHLY", "")
    creator = _stripe_line_item(
        CheckoutRequest(kind="plan", id="creator", cycle="monthly"),
        credits=1000, price_usd=29.0, label="Creator",
    )
    assert "price_data" in creator


def test_stripe_status_subscription_ready_with_starter(monkeypatch):
    from app.services import stripe_ready

    monkeypatch.setattr(stripe_ready.settings, "STRIPE_API_KEY", "sk_test")
    monkeypatch.setattr(stripe_ready.settings, "ENV", "development")
    for name in stripe_ready.PLAN_PRICE_ENVS:
        monkeypatch.setattr(stripe_ready.settings, name, "")
    monkeypatch.setattr(stripe_ready.settings, "STRIPE_PRICE_STARTER_MONTHLY", "price_s")
    st = stripe_ready.stripe_status()
    assert st.subscription_ready is True
    assert st.plan_price_ids["STRIPE_PRICE_STARTER_MONTHLY"] is True
