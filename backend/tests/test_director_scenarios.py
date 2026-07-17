"""Scenario-card planning — 8 Agent features must not collapse into wrong pipelines."""
from app.director import DirectorPlanner
from app.director_scenarios import SCENARIO_IDS, PORTRAIT_VARIATIONS, UGC_BEATS


def test_all_scenario_ids_plan():
    p = DirectorPlanner()
    for sc in SCENARIO_IDS:
        plan = p.plan(f"test brief for {sc}", duration=15, minimal=True, scenario=sc)
        assert plan.scenario == sc
        assert plan.intent
        assert plan.steps


def test_ai_portrait_uses_headshot_angles_not_product():
    plan = DirectorPlanner().plan(
        "一组专业形象写真，正装，柔和棚拍布光",
        duration=5, minimal=True, scenario="ai_portrait",
    )
    assert plan.intent == "image_series"
    titles = " ".join(s.title for s in plan.steps if s.action == "image")
    assert "职业头像" in titles or "形象照" in titles
    assert "侧面 45° 视角" not in titles  # old product-angle template
    for s in plan.steps:
        if s.action == "image" and s.params.get("aspect_ratio"):
            assert s.params["aspect_ratio"] in ("3:4", "9:16", "1:1")
    assert any("NOT product photography" in (s.prompt or "") for s in plan.steps if s.action == "image")


def test_ugc_uses_handheld_beats_and_vertical():
    plan = DirectorPlanner().plan(
        "UGC 种草短视频", duration=15, minimal=True, scenario="ugc",
    )
    assert plan.intent == "campaign"
    titles = [s.title for s in plan.steps if s.action == "video"]
    assert any("自拍" in t or "种草" in t or "安利" in t for t in titles)
    assert not any("建立镜头" in t for t in titles)
    for s in plan.steps:
        if s.action == "video":
            assert s.params.get("aspect_ratio") == "9:16"
    assert any(s.action == "compose" for s in plan.steps)


def test_product_ad_has_hook_beats_and_compose():
    plan = DirectorPlanner().plan(
        "高转化产品广告", duration=15, minimal=True, scenario="product_ad",
    )
    titles = [s.title for s in plan.steps if s.action == "video"]
    assert any("钩子" in t for t in titles)
    assert any(s.action == "compose" for s in plan.steps)
    assert any(s.model_id.startswith("kling") for s in plan.steps if s.action == "video")


def test_micro_drama_multi_shot_even_minimal():
    plan = DirectorPlanner().plan(
        "竖屏微短剧反转", duration=30, minimal=True, scenario="micro_drama",
    )
    vids = [s for s in plan.steps if s.action == "video"]
    assert len(vids) >= 2
    assert any(s.action == "compose" for s in plan.steps)


def test_infer_scenario_from_card_briefs():
    from app.director_scenarios import infer_scenario
    assert infer_scenario("一条 UGC 风格种草短视频") == "ugc"
    assert infer_scenario("一组专业形象写真，正装") == "ai_portrait"
    assert infer_scenario("一个竖屏数字人口播视频") == "talking_avatar"
    assert infer_scenario("一段电影级动漫短片，新海诚") == "anime"


def test_portrait_variations_count():
    assert len(PORTRAIT_VARIATIONS) == 4
    assert len(UGC_BEATS) == 3


def test_series_prompts_forbid_collage_and_strip_count():
    plan = DirectorPlanner().plan(
        "一组专业形象写真，正装，四张统一风格",
        duration=5, minimal=True, scenario="ai_portrait",
    )
    for s in plan.steps:
        if s.action != "image":
            continue
        assert "四张" not in s.prompt
        assert "NOT a collage" in s.prompt or "single" in s.prompt.lower()
    plan2 = DirectorPlanner().plan(
        "影棚级产品摄影图，系列四张",
        duration=5, minimal=True, scenario="product_photo",
    )
    for s in plan2.steps:
        if s.action == "image":
            assert "四张" not in s.prompt
            assert "NOT a collage" in s.prompt
