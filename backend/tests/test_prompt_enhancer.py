"""Prompt enhancer tests (pure, no external deps)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.prompt_enhancer import (
    IMAGE_ENHANCEMENTS,
    UNIVERSAL_QUALITY,
    VIDEO_CAMERAMOVES,
    PromptEnhancer,
)


def test_fast_quality_skips_enhancement():
    r = PromptEnhancer().enhance("a red apple", quality="fast")
    assert r.enhanced == r.original == "a red apple"
    assert r.additions == []
    assert r.style_detected == ["none"]


def test_disabled_enhancer_is_a_noop():
    r = PromptEnhancer(enabled=False).enhance("赛博朋克城市")
    assert r.enhanced == "赛博朋克城市"
    assert r.additions == []


def test_detects_chinese_and_english():
    e = PromptEnhancer()
    assert e._detect_language("一只猫在屋顶上") == "zh"
    assert e._detect_language("a cat on the roof") == "en"
    # Mostly-English prompt with a stray Chinese char stays English.
    assert e._detect_language("a cat on the roof 猫") == "en"


def test_detect_style_prefers_specific_styles():
    e = PromptEnhancer()
    assert e._detect_style("赛博朋克城市夜景") == "sci-fi"
    assert e._detect_style("a cute kitten") == "cute/kawaii"
    assert e._detect_style("appetizing ramen bowl") == "food"
    assert e._detect_style("水墨山水") == "chinese"
    # Unknown content falls back to the realistic bucket.
    assert e._detect_style("something entirely unclassified") == "realistic"


def test_image_enhancement_uses_detected_style_and_language():
    r = PromptEnhancer().enhance("一只猫在赛博朋克城市", media_type="image")
    assert r.style_detected == ["sci-fi"]
    assert r.language == "zh"
    # 3 style modifiers (balanced) + 1 universal quality suffix.
    assert len(r.additions) == 4
    assert r.additions[:3] == IMAGE_ENHANCEMENTS["sci-fi"]["zh"][:3]
    assert r.additions[3] == UNIVERSAL_QUALITY["zh"][0]
    assert r.enhanced.startswith("一只猫在赛博朋克城市，")
    assert all(a in r.enhanced for a in r.additions)


def test_high_quality_adds_more_style_modifiers():
    balanced = PromptEnhancer().enhance("a portrait of a woman", media_type="image")
    high = PromptEnhancer().enhance(
        "a portrait of a woman", media_type="image", quality="high")
    assert len(balanced.additions) == 4
    assert len(high.additions) == 5


def test_explicit_style_overrides_detection():
    r = PromptEnhancer().enhance("a cat", media_type="image", style="anime")
    assert r.style_detected == ["anime"]
    assert r.additions[0] == IMAGE_ENHANCEMENTS["anime"]["en"][0]


def test_unknown_style_falls_back_to_realistic_bucket():
    r = PromptEnhancer().enhance("a cat", media_type="image", style="not-a-style")
    assert r.additions[0] == IMAGE_ENHANCEMENTS["realistic"]["en"][0]


def test_modifiers_already_present_are_not_duplicated():
    prompt = "a cat, photorealistic"
    r = PromptEnhancer().enhance(prompt, media_type="image")
    assert "photorealistic" not in r.additions
    assert r.enhanced.count("photorealistic") == 1


def test_video_adds_camera_move_and_motion_cue():
    r = PromptEnhancer().enhance("a cozy coffee shop", media_type="video")
    assert VIDEO_CAMERAMOVES["zoom_in"]["en"] in r.additions  # food → zoom_in
    assert "smooth natural motion, coherent transitions" in r.additions
    # Video keeps the style list short: 2 modifiers + universal + camera + cue.
    assert len(r.additions) == 5


def test_video_keeps_user_specified_camera_move():
    r = PromptEnhancer().enhance("mountain landscape with slow pan", media_type="video")
    assert not any(m["en"] in r.additions for m in VIDEO_CAMERAMOVES.values())
    assert "smooth natural motion, coherent transitions" in r.additions


def test_auto_media_type_gets_both_image_and_video_cues():
    r = PromptEnhancer().enhance("测试画面", media_type="auto")
    assert VIDEO_CAMERAMOVES["zoom_in"]["zh"] in r.additions
    assert UNIVERSAL_QUALITY["zh"][0] in r.additions
