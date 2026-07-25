"""Prompt router tests — prompt analysis and model scoring."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.router import (
    MODEL_STYLE_PREFS,
    MediaType,
    PromptRouter,
    QualityTier,
)


@pytest.fixture
def router(monkeypatch):
    """Router with a healthy, closed-circuit model registry."""
    monkeypatch.setattr("app.router.model_health.is_circuit_open", lambda model_id: False)
    monkeypatch.setattr("app.router.model_health.score", lambda model_id: 100.0)
    return PromptRouter()


def test_detects_media_type_from_keywords(router):
    assert router.analyze("一段森林短片，镜头推进").media_type == MediaType.VIDEO
    assert router.analyze("a poster illustration of a cat").media_type == MediaType.IMAGE
    assert router.analyze("dragon on a hill").media_type == MediaType.AUTO


def test_media_type_hint_overrides_keywords(router):
    assert router.analyze("a poster of a cat", "video").media_type == MediaType.VIDEO
    assert router.analyze("一段短片", "image").media_type == MediaType.VIDEO  # keywords win for video


def test_quality_detection(router):
    assert router.analyze("4k cinematic masterpiece").quality == QualityTier.HIGH
    assert router.analyze("quick draft sketch").quality == QualityTier.FAST
    assert router.analyze("a cat").quality == QualityTier.BALANCED
    assert router.analyze("a cat", quality_hint="high").quality == QualityTier.HIGH


def test_style_and_language_extraction(router):
    analysis = router.analyze("赛博朋克风格的城市夜景，写实摄影")
    assert "sci-fi" in analysis.styles and "realistic" in analysis.styles
    assert analysis.language == "zh"
    assert router.analyze("a realistic mountain landscape").language == "en"


def test_complexity_buckets(router):
    assert router.analyze("a cat").complexity == "simple"
    assert router.analyze("a golden cat sitting on a wooden table").complexity == "medium"
    assert router.analyze(
        "a golden retriever puppy running through a field of autumn leaves at "
        "sunset with warm cinematic backlighting and shallow depth of field"
    ).complexity == "complex"


def test_mood_detection(router):
    assert router.analyze("a warm sunset over the hills").mood == "warm"
    assert router.analyze("dramatic storm over the ocean").mood == "dramatic"
    assert router.analyze("一个盒子").mood == ""


def test_subject_extraction_is_deduped_and_capped(router):
    subjects = router.analyze(
        "a cat and a dog and a cat playing with a ball in the garden near a house"
    ).key_subjects
    assert len(subjects) <= 5
    assert len(subjects) == len(set(subjects))
    assert "the" not in subjects


def test_explicit_user_model_bypasses_scoring(router):
    analysis = router.analyze("a cat")
    choice = router.select_model(analysis, user_model="nano-banana")
    assert choice.model_id == "nano-banana"
    assert choice.score == 100.0


def test_style_match_beats_the_generic_baseline(router):
    analysis = router.analyze("清新可爱的小猫插画", "image")
    choice = router.select_model(analysis)
    assert choice.model_id == "nano-banana"  # boosted for cute/kawaii
    assert any("风格匹配" in r for r in choice.reasons)


def test_high_quality_prefers_the_flagship_model(router):
    analysis = router.analyze("commercial product photo, 8k, premium", "image", "high")
    assert router.select_model(analysis).model_id == "gpt-image-2"


def test_degraded_health_penalises_a_model(monkeypatch, router):
    prompt = "commercial product photo, 8k, premium"
    healthy = router.select_model(router.analyze(prompt, "image", "high"))

    monkeypatch.setattr("app.router.model_health.score", lambda model_id: 0.0)
    r = PromptRouter()
    degraded = r.select_model(r.analyze(prompt, "image", "high"))

    assert degraded.model_id == healthy.model_id
    assert degraded.score == healthy.score - 30
    assert any("实时健康" in reason for reason in degraded.reasons)


def test_all_circuits_open_still_returns_a_candidate(monkeypatch):
    monkeypatch.setattr("app.router.model_health.is_circuit_open", lambda model_id: True)
    monkeypatch.setattr("app.router.model_health.score", lambda model_id: 0.0)
    r = PromptRouter()
    choice = r.select_model(r.analyze("a cat", "image"))
    assert choice.model_id in MODEL_STYLE_PREFS["image"]
    assert choice.score == 1.0


def test_auto_media_type_routes_by_complexity(router):
    simple = router.select_model(router.analyze("a cat"))
    complex_prompt = router.select_model(router.analyze(
        "an epic dragon flying above a medieval castle during a golden sunset, "
        "highly detailed concept art"))
    assert simple.recommended_media_type == MediaType.IMAGE
    assert complex_prompt.recommended_media_type == MediaType.VIDEO


def test_get_all_model_scores_covers_both_media_for_auto(router):
    scores = router.get_all_model_scores(router.analyze("dragon on a hill"))
    assert {s.model_id for s in scores} == (
        set(MODEL_STYLE_PREFS["image"]) | set(MODEL_STYLE_PREFS["video"]))
    assert scores == sorted(scores, key=lambda s: s.score, reverse=True)


def test_get_all_model_scores_for_a_single_media_type(router):
    scores = router.get_all_model_scores(router.analyze("一段电影级短片", "video"))
    assert {s.model_id for s in scores} == set(MODEL_STYLE_PREFS["video"])
    assert all(s.recommended_media_type == MediaType.VIDEO for s in scores)
    assert all(s.reasons for s in scores)
