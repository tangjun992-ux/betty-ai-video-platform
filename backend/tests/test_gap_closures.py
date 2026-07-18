"""Gap-closure tests: native 9:16 mapping, packaging presets, variants fan-out."""
from app.adapters.kie_adapter import _size_to_ratio
from app.adapters.demo_provider import SUBTITLE_STYLES, BGM_PRESETS
from app.director import DirectorPlanner, _size_from_params


def test_size_to_ratio_maps_director_portrait_sizes():
    """Root cause fix: 720x1280 / 1080x1920 must be 9:16, never 1:1."""
    assert _size_to_ratio("720x1280") == "9:16"
    assert _size_to_ratio("1080x1920") == "9:16"
    assert _size_to_ratio("1280x720") == "16:9"
    assert _size_to_ratio("1920x1080") == "16:9"


def test_director_ratio_to_size_uses_kie_mapped_pixels():
    assert _size_from_params({"aspect_ratio": "9:16"}, "x") == "1080x1920"
    assert _size_from_params({"aspect_ratio": "16:9"}, "x") == "1920x1080"


def test_ugc_plan_locks_9_16_and_identity_variant():
    plan = DirectorPlanner().plan("UGC种草", duration=15, minimal=True, scenario="ugc")
    vids = [s for s in plan.steps if s.action == "video"]
    assert len(vids) >= 2
    assert all(s.params.get("aspect_ratio") == "9:16" for s in vids)
    assert vids[0].params.get("identity_variant") is False
    assert vids[1].params.get("identity_variant") is True
    imgs = [s for s in plan.steps if s.action == "image"]
    assert imgs and imgs[0].params.get("aspect_ratio") == "9:16"


def test_talking_closeup_and_reliable_kling_default():
    plan = DirectorPlanner().plan(
        "竖屏数字人口播女主播", duration=10, minimal=True, scenario="talking_avatar",
    )
    lips = next(s for s in plan.steps if s.action == "lipsync")
    # InfiniTalk-first burned ~4min on timeout in live eval — default Kling
    assert lips.params.get("prefer_infinitalk") is False
    assert lips.params.get("lipsync_model") == "kling/ai-avatar-pro"
    img = next(s for s in plan.steps if s.action == "image")
    assert "CLOSE-UP" in img.prompt or "close-up" in img.prompt.lower()


def test_packaging_presets_on_compose():
    plan = DirectorPlanner().plan("产品广告", duration=15, minimal=True, scenario="product_ad")
    comp = next(s for s in plan.steps if s.action == "compose")
    assert comp.params.get("subtitle_style") == "ad"
    assert comp.params.get("bgm_preset") == "upbeat"
    assert "feed" in SUBTITLE_STYLES and "talking" in SUBTITLE_STYLES
    assert "upbeat" in BGM_PRESETS and "cinematic" in BGM_PRESETS


def test_plan_variants_fanout():
    variants = DirectorPlanner().plan_variants(
        "Aurora耳机投放广告", scenario="product_ad", duration=15, minimal=True, n=3,
    )
    assert len(variants) == 3
    seeds = set()
    ctas = set()
    for v in variants:
        assert v["variant_id"]
        assert v["plan"]["steps"]
        for s in v["plan"]["steps"]:
            if s["action"] in ("image", "video"):
                seeds.add((s.get("params") or {}).get("seed"))
            if s["action"] == "compose":
                ctas.add((s.get("params") or {}).get("cta_text"))
    assert len(seeds) >= 2
    assert len(ctas) >= 2
