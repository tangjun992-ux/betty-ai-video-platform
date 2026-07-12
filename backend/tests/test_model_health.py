"""Dynamic model health, circuit breaker, and output quality guard tests."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.model_health import (
    CIRCUIT_FAILURES,
    ModelHealthRegistry,
    validate_generation_results,
)


def memory_registry() -> ModelHealthRegistry:
    registry = ModelHealthRegistry()
    registry._client = lambda: (_ for _ in ()).throw(ConnectionError("redis down"))  # type: ignore
    return registry


def test_unseen_model_is_healthy():
    r = memory_registry()
    snap = r.snapshot("model-a")
    assert snap.score == 100.0
    assert not snap.circuit_open


def test_failures_open_circuit_and_success_recovers():
    r = memory_registry()
    for i in range(CIRCUIT_FAILURES):
        snap = r.record_failure("model-a", "timeout", retryable=True)
    assert snap.circuit_open
    assert r.score("model-a") == 0.0

    recovered = r.record_success("model-a", latency_ms=1200)
    assert not recovered.circuit_open
    assert recovered.consecutive_failures == 0
    assert recovered.successes == 1


def test_fatal_failure_does_not_open_circuit():
    r = memory_registry()
    for _ in range(10):
        r.record_failure("model-a", "content policy", retryable=False)
    assert not r.is_circuit_open("model-a")
    assert r.snapshot("model-a").failures == 0


def test_quality_guard_requires_media_url():
    ok, reason = validate_generation_results([], "image")
    assert not ok and "no results" in reason
    ok, reason = validate_generation_results([{"media_url": ""}], "image")
    assert not ok and "missing media URL" in reason
    ok, reason = validate_generation_results([{"media_url": "https://example.com/a.png"}], "image")
    assert ok and not reason


def test_router_skips_open_circuit(monkeypatch):
    from app.router import PromptRouter

    monkeypatch.setattr(
        "app.router.model_health.is_circuit_open",
        lambda model_id: model_id == "gpt-image-2",
    )
    monkeypatch.setattr("app.router.model_health.score", lambda model_id: 100.0)
    router = PromptRouter()
    analysis = router.analyze(
        "premium product photography, 4k commercial poster", "image", "high")
    assert router.select_model(analysis).model_id == "nano-banana"

