"""Three-knife upgrades: packaging / variants batch / identity lock."""
from pathlib import Path

from app.adapters.demo_provider import (
    SUBTITLE_STYLES, BGM_PRESETS, compose_final_video, render_demo_video,
    _local_media_path, build_identity_strip, _render_bgm_wav,
)
from app.director import DirectorPlanner


def test_subtitle_templates_at_least_10():
    assert len(SUBTITLE_STYLES) >= 10
    for key in ("feed", "talking", "ad", "drama", "bold", "neon", "karaoke", "impact"):
        assert key in SUBTITLE_STYLES


def test_identity_lock_modes():
    off = DirectorPlanner().plan("UGC种草", duration=15, minimal=True, scenario="ugc", identity_lock="off")
    vids = [s for s in off.steps if s.action == "video"]
    assert vids and all(not s.params.get("identity_from") for s in vids)
    assert all(s.params.get("identity_variant") is False for s in vids)

    hero = DirectorPlanner().plan("UGC种草", duration=15, minimal=True, scenario="ugc", identity_lock="hero")
    hv = [s for s in hero.steps if s.action == "video"]
    assert hv[0].params.get("identity_from")
    assert hv[0].params.get("identity_variant") is False
    assert hv[1].params.get("identity_variant") is False

    edit = DirectorPlanner().plan("UGC种草", duration=15, minimal=True, scenario="ugc", identity_lock="edit")
    ev = [s for s in edit.steps if s.action == "video"]
    assert ev[0].params.get("identity_variant") is False
    assert ev[1].params.get("identity_variant") is True


def test_product_ad_uses_impact_subtitle():
    plan = DirectorPlanner().plan("产品广告", duration=15, minimal=True, scenario="product_ad")
    comp = next(s for s in plan.steps if s.action == "compose")
    assert comp.params.get("subtitle_style") == "impact"


def test_compose_voice_duck_and_multi_styles(tmp_path):
    u1, _ = render_demo_video("knife a", "320x180", 2, "cinematic")
    u2, _ = render_demo_video("knife b", "320x180", 2, "sci-fi")
    # Fake narration wav via bgm render
    narr = tmp_path / "narr.wav"
    _render_bgm_wav(3.0, narr, preset="soft")
    narr_url = f"/api/v1/media/generated/{narr.name}"
    # Copy narr into generated dir so _local_media_path can find it if needed —
    # compose accepts local via narration after we place file in storage.
    from app.adapters.demo_provider import _generated_dir, MEDIA_URL_PREFIX, GENERATED_SUBDIR
    dest = _generated_dir() / narr.name
    dest.write_bytes(narr.read_bytes())
    narr_url = f"{MEDIA_URL_PREFIX}/{GENERATED_SUBDIR}/{dest.name}"

    for style in ("impact", "neon", "karaoke", "bold"):
        final, _ = compose_final_video(
            [u1, u2],
            None,
            True,
            narr_url,
            subtitle_track=[{"text": f"样式{style}", "start": 0, "end": 3}],
            export_preset="landscape_16_9",
            bgm=True,
            bgm_preset="upbeat",
            subtitle_style=style,
            cta_text="立即了解",
            voice_duck=True,
        )
        p = Path(_local_media_path(final))
        assert p.is_file() and p.stat().st_size > 1000


def test_identity_strip_from_demo_images():
    from app.adapters.demo_provider import render_demo_image
    a = render_demo_image("hero face", "512x512", "portrait")
    b = render_demo_image("shot two", "512x512", "cinematic")
    url, _ = build_identity_strip([a, b], labels=["Hero", "Shot 1"])
    assert url.startswith("/api/v1/media/")
    p = Path(_local_media_path(url))
    assert p.is_file() and p.stat().st_size > 500


def test_plan_variants_respects_identity_lock():
    variants = DirectorPlanner().plan_variants(
        "耳机广告", scenario="product_ad", n=2, minimal=True, identity_lock="hero",
    )
    assert len(variants) == 2
    vids = [s for s in variants[0]["plan"]["steps"] if s["action"] == "video"]
    assert vids[1]["params"].get("identity_variant") is False
