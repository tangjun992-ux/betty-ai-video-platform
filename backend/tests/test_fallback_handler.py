"""Model fallback tests (pure, no external deps)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.fallback_handler import (
    FALLBACK_MAP,
    get_fallback,
    is_retryable_error,
    try_with_fallback,
)


def test_transient_errors_are_retryable():
    for msg in [
        "Request timed out after 60s",
        "429 Too Many Requests",
        "upstream returned 503",
        "connection reset by peer",
        "任务排队中，请稍后重试",
        "invalid result: missing media url",
    ]:
        assert is_retryable_error(msg), msg


def test_fatal_errors_are_not_retryable():
    for msg in [
        "OPENAI_API_KEY not configured",
        "no adapter for model",
        "blocked by content policy: nudity",
        "Credits insufficient",
        "余额不足，请充值",
    ]:
        assert not is_retryable_error(msg), msg


def test_unknown_errors_do_not_trigger_fallback():
    assert not is_retryable_error("something unexpected happened")


def test_fatal_patterns_win_over_retryable_ones():
    # "timeout" is retryable, but an API key problem is a config error.
    assert not is_retryable_error("timeout while validating API key")


def test_get_fallback_pairs():
    assert get_fallback("seedance-2.0") == "seedance-2.0-fast"
    assert get_fallback("nano-banana") == "gpt-image-2"
    assert get_fallback("unknown-model") is None
    for model_id, config in FALLBACK_MAP.items():
        assert config.primary == model_id
        assert config.fallback != model_id


class _FakeAdapter:
    def __init__(self):
        self.image_calls = 0
        self.video_calls = 0

    async def generate_image(self, **kwargs):
        self.image_calls += 1
        return ["image-result"]

    async def generate_video(self, **kwargs):
        self.video_calls += 1
        return "video-result"


def test_primary_success_returns_result_and_model():
    seen = {}

    async def primary(**kwargs):
        seen.update(kwargs)
        return "ok"

    out = asyncio.run(try_with_fallback(primary, "gpt-image-2", prompt="a cat"))
    assert out == {
        "result": "ok",
        "model_used": "gpt-image-2",
        "used_fallback": False,
        "errors": {},
    }
    assert seen == {"prompt": "a cat", "_model": "gpt-image-2"}


def test_fatal_primary_error_does_not_fall_back():
    async def primary(**kwargs):
        raise RuntimeError("OPENAI_API_KEY not configured")

    out = asyncio.run(try_with_fallback(primary, "gpt-image-2"))
    assert out["result"] is None
    assert out["used_fallback"] is False
    assert "not configured" in out["errors"]["gpt-image-2"]


def test_unknown_primary_model_without_fallback_returns_error():
    async def primary(**kwargs):
        raise RuntimeError("timeout")

    out = asyncio.run(try_with_fallback(primary, "mystery-model"))
    assert out["result"] is None
    assert out["used_fallback"] is False
    assert out["errors"] == {"mystery-model": "timeout"}


def test_retryable_error_falls_back_to_configured_model(monkeypatch):
    adapter = _FakeAdapter()
    monkeypatch.setattr("app.adapters.registry.get_adapter", lambda m: adapter)

    async def primary(**kwargs):
        raise RuntimeError("rate limit exceeded")

    out = asyncio.run(try_with_fallback(primary, "gpt-image-2", _is_image=True))
    assert out["result"] == ["image-result"]
    assert out["model_used"] == "nano-banana"
    assert out["used_fallback"] is True
    assert out["errors"] == {"gpt-image-2": "rate limit exceeded"}
    assert adapter.image_calls == 1 and adapter.video_calls == 0


def test_video_fallback_uses_video_endpoint(monkeypatch):
    adapter = _FakeAdapter()
    monkeypatch.setattr("app.adapters.registry.get_adapter", lambda m: adapter)

    async def primary(**kwargs):
        raise RuntimeError("connection refused")

    out = asyncio.run(try_with_fallback(primary, "seedance-2.0"))
    assert out["result"] == "video-result"
    assert out["model_used"] == "seedance-2.0-fast"
    assert adapter.video_calls == 1


def test_explicit_fallback_model_overrides_the_map(monkeypatch):
    monkeypatch.setattr("app.adapters.registry.get_adapter", lambda m: _FakeAdapter())

    async def primary(**kwargs):
        raise RuntimeError("timeout")

    out = asyncio.run(
        try_with_fallback(primary, "gpt-image-2", fallback_model="seedance-2.0"))
    assert out["model_used"] == "seedance-2.0"


def test_missing_fallback_adapter_is_reported(monkeypatch):
    monkeypatch.setattr("app.adapters.registry.get_adapter", lambda m: None)

    async def primary(**kwargs):
        raise RuntimeError("timeout")

    out = asyncio.run(try_with_fallback(primary, "gpt-image-2"))
    assert out["result"] is None
    assert out["used_fallback"] is False
    assert "No adapter" in out["errors"]["nano-banana"]


def test_both_models_failing_reports_both_errors(monkeypatch):
    class _Broken(_FakeAdapter):
        async def generate_video(self, **kwargs):
            raise RuntimeError("fallback exploded")

    monkeypatch.setattr("app.adapters.registry.get_adapter", lambda m: _Broken())

    async def primary(**kwargs):
        raise RuntimeError("timeout")

    out = asyncio.run(try_with_fallback(primary, "seedance-2.0"))
    assert out["result"] is None
    assert out["used_fallback"] is True
    assert out["errors"] == {
        "seedance-2.0": "timeout",
        "seedance-2.0-fast": "fallback exploded",
    }
