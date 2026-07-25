"""Adapter contract tests — result payloads, cost estimation, registry."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.adapters import registry
from app.adapters.base import BaseModelAdapter, GenerationResult, MediaSize


class _DummyAdapter(BaseModelAdapter):
    @property
    def provider_name(self):
        return "Dummy"

    @property
    def supported_models(self):
        return ["dummy-image", "dummy-video"]

    @property
    def capabilities(self):
        return {
            "media_types": ["image", "video"],
            "cost_per_image_credits": 7,
            "cost_per_5s_video_credits": 4,
        }

    async def generate_image(self, prompt, size="1024x1024", style="auto", count=1, **kwargs):
        return [GenerationResult(media_url="local://img.png", model="dummy-image")]

    async def generate_video(self, prompt, image_url=None, duration=5,
                             resolution="1080p", **kwargs):
        return GenerationResult(media_url="local://clip.mp4", media_type="video",
                                model="dummy-video", duration=duration)


class _BareAdapter(_DummyAdapter):
    @property
    def capabilities(self):
        return {}


def test_generation_result_media_type_helpers():
    image = GenerationResult(media_url="a.png")
    video = GenerationResult(media_url="a.mp4", media_type="video")
    assert image.is_image and not image.is_video
    assert video.is_video and not video.is_image


def test_generation_result_to_dict_round_trip():
    result = GenerationResult(
        media_url="a.mp4", thumbnail_url="a.jpg", media_type="video",
        model="seedance-2.0", resolution=MediaSize.HD_1080.value, duration=5.0,
        cost=4.0, meta={"task_id": "t1"})
    assert result.to_dict() == {
        "media_url": "a.mp4",
        "thumbnail_url": "a.jpg",
        "media_type": "video",
        "model": "seedance-2.0",
        "resolution": "1920x1080",
        "duration": 5.0,
        "cost": 4.0,
        "meta": {"task_id": "t1"},
        "error": None,
    }


def test_estimate_cost_scales_with_video_duration():
    adapter = _DummyAdapter()
    assert adapter.estimate_cost("image") == 7
    assert adapter.estimate_cost("video") == 4
    assert adapter.estimate_cost("video", duration=10) == 8
    # Sub-5s clips are never cheaper than one billing unit.
    assert adapter.estimate_cost("video", duration=2) == 4


def test_estimate_cost_falls_back_to_defaults_without_capabilities():
    adapter = _BareAdapter()
    assert adapter.estimate_cost("image") == 5
    assert adapter.estimate_cost("video", duration=15) == 9


def test_default_health_check_is_optimistic():
    assert asyncio.run(_DummyAdapter().health_check()) is True


def test_registry_registers_every_supported_model():
    try:
        registry.register_adapter(_DummyAdapter)
        adapter = registry.get_adapter("dummy-image")
        assert adapter is not None
        assert adapter is registry.get_adapter("dummy-video")
        assert "dummy-image" in registry.list_adapters()
    finally:
        registry._ADAPTER_CLASSES.pop("dummy-image", None)
        registry._ADAPTER_CLASSES.pop("dummy-video", None)


def test_registry_returns_none_for_unknown_model():
    assert registry.get_adapter("no-such-model") is None


def test_list_adapters_returns_a_copy():
    listed = registry.list_adapters()
    listed["tampered"] = object()
    assert "tampered" not in registry._ADAPTER_CLASSES


def test_registered_adapters_expose_the_documented_contract():
    for model_id, adapter in registry.list_adapters().items():
        assert model_id in adapter.supported_models
        assert isinstance(adapter.provider_name, str) and adapter.provider_name
        assert isinstance(adapter.capabilities, dict)
