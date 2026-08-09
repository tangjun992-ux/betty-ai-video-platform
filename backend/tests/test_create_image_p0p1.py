"""P0/P1 create-image upgrades — server-free unit checks.

Covers the backend-side contract that the front-end wiring relies on:
- KIE adapter threads a negative prompt into the request payload.
- GenerateRequest accepts negative_prompt and clamps count to ≤4.
- SessionCreate accepts an intent so image sessions can be tagged.
"""
import asyncio

from app.adapters.kie_adapter import KieAdapter
from app.adapters.base import GenerationResult
from app.api.generate import GenerateRequest
from app.api.director import SessionCreate


def test_kie_generate_image_includes_negative_prompt(monkeypatch):
    captured = {}

    async def fake_submit(self, payload, media_type="image", timeout=180):
        captured["payload"] = payload
        return {"taskId": "t1", "imageUrl": "https://example.com/x.png"}

    monkeypatch.setattr(KieAdapter, "_submit_and_poll", fake_submit, raising=True)

    adapter = KieAdapter()
    res = asyncio.run(
        adapter.generate_image(
            prompt="a cat",
            model_id="sdxl",
            size="1024x1024",
            negative_prompt="blurry, extra fingers, watermark",
        )
    )
    assert isinstance(res, GenerationResult)
    p = captured["payload"]
    assert p.get("negativePrompt") == "blurry, extra fingers, watermark"
    assert p.get("negative_prompt") == "blurry, extra fingers, watermark"


def test_kie_generate_image_omits_empty_negative(monkeypatch):
    captured = {}

    async def fake_submit(self, payload, media_type="image", timeout=180):
        captured["payload"] = payload
        return {"taskId": "t1", "imageUrl": "https://example.com/x.png"}

    monkeypatch.setattr(KieAdapter, "_submit_and_poll", fake_submit, raising=True)

    adapter = KieAdapter()
    asyncio.run(
        adapter.generate_image(prompt="a cat", model_id="sdxl", size="1024x1024", negative_prompt="  ")
    )
    assert "negativePrompt" not in captured["payload"]
    assert "negative_prompt" not in captured["payload"]


def test_generate_request_accepts_negative_and_clamps_count():
    req = GenerateRequest(prompt="hi", count=4, negative_prompt="ugly")
    assert req.negative_prompt == "ugly"
    assert req.count == 4
    # count is bounded at 4 by the schema
    import pytest
    with pytest.raises(Exception):
        GenerateRequest(prompt="hi", count=8)


def test_session_create_accepts_intent():
    s = SessionCreate(title="my images", intent="image_create", status="active")
    assert s.intent == "image_create"
    assert s.status == "active"
