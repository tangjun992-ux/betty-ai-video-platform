"""Main Line B — ad delivery completeness."""
from app.export_specs import (
    list_export_specs, resolve_placement, clamp_duration, validate_plan_against_placement,
)
from app.director_brief_templates import list_brief_templates, get_brief_template
from app.director import DirectorPlanner
from app.adapters.demo_provider import (
    BGM_PRESETS, ensure_bgm_stock_installed, _bgm_url_for_preset, compose_final_video,
    render_demo_video, _local_media_path, _generated_dir, MEDIA_URL_PREFIX, GENERATED_SUBDIR,
    _render_bgm_wav,
)
from pathlib import Path


def test_eight_bgm_presets_and_stock_urls():
    assert len(BGM_PRESETS) >= 8
    installed = ensure_bgm_stock_installed()
    assert len(installed) >= 6
    url = _bgm_url_for_preset("upbeat")
    assert "bgm/upbeat" in url or url.startswith("http")


def test_export_specs_cover_meta_tiktok_reels():
    specs = {s["id"]: s for s in list_export_specs()}
    for pid in ("meta_feed", "meta_stories", "tiktok", "reels", "youtube_shorts"):
        assert pid in specs
    feed = resolve_placement("product_ad", "meta_feed")
    assert feed["aspect_ratio"] == "16:9"
    stories = resolve_placement("product_ad", "meta_stories")
    assert stories["aspect_ratio"] == "9:16"
    assert clamp_duration(3, feed) == feed["duration_min"]
    assert clamp_duration(99, feed) == feed["duration_max"]


def test_plan_respects_tiktok_placement():
    plan = DirectorPlanner().plan(
        "UGC种草", duration=15, minimal=True, scenario="ugc",
        export_placement="tiktok",
    )
    comp = next(s for s in plan.steps if s.action == "compose")
    assert comp.params.get("aspect_ratio") == "9:16"
    assert comp.params.get("export_placement") == "tiktok"
    assert comp.params.get("bgm_preset") == "energetic"


def test_meta_stories_forces_portrait_for_ad():
    plan = DirectorPlanner().plan(
        "产品广告", duration=15, minimal=True, scenario="product_ad",
        export_placement="meta_stories",
    )
    vids = [s for s in plan.steps if s.action == "video"]
    assert vids and all(s.params.get("aspect_ratio") == "9:16" for s in vids)


def test_brief_templates_for_ad_ugc_talking():
    ads = list_brief_templates("product_ad")
    ugc = list_brief_templates("ugc")
    talk = list_brief_templates("talking_avatar")
    assert len(ads) >= 2 and len(ugc) >= 2 and len(talk) >= 2
    t = get_brief_template("ugc_selfie_rec")
    assert t and t["placement"] == "tiktok" and "竖屏" in t["brief"]


def test_placement_validation_warns_on_mismatch():
    plan = DirectorPlanner().plan(
        "产品广告", duration=15, minimal=True, scenario="product_ad",
        export_placement="meta_feed",
    ).to_dict()
    # Force wrong aspect on compose for warning
    for s in plan["steps"]:
        if s["action"] == "compose":
            s["params"]["aspect_ratio"] = "9:16"
    warns = validate_plan_against_placement(plan, "meta_feed")
    assert any("画幅" in w for w in warns)


def test_compose_fetches_stock_bgm_url():
    ensure_bgm_stock_installed()
    u1, _ = render_demo_video("mlb a", "320x180", 2, "cinematic")
    u2, _ = render_demo_video("mlb b", "320x180", 2, "sci-fi")
    narr = _generated_dir() / "mlb_narr.wav"
    _render_bgm_wav(3.0, narr, preset="soft")
    narr_url = f"{MEDIA_URL_PREFIX}/{GENERATED_SUBDIR}/{narr.name}"
    final, _ = compose_final_video(
        [u1, u2], None, True, narr_url,
        subtitle_track=[{"text": "投放字幕", "start": 0, "end": 3}],
        export_preset="landscape_16_9",
        bgm=True, bgm_preset="hype", subtitle_style="impact",
        cta_text="了解更多", voice_duck=True,
    )
    p = Path(_local_media_path(final))
    assert p.is_file() and p.stat().st_size > 1000
