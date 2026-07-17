"""Scenario-card planning — 8 Agent features must not collapse into wrong pipelines."""
from app.director import DirectorPlanner, refine_plan
from app.director_scenarios import (
    SCENARIO_IDS, PORTRAIT_VARIATIONS, UGC_BEATS, ANIME_BEATS, scenario_aspect,
)


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
    assert len(ANIME_BEATS) >= 4


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


def test_aspect_hardening_by_scenario():
    """UGC/短剧/口播 → 9:16；广告/商业片/动漫 → 16:9（竖屏关键词也不能撬开）。"""
    expect = {
        "ugc": "9:16",
        "micro_drama": "9:16",
        "talking_avatar": "9:16",
        "product_ad": "16:9",
        "product_commercial": "16:9",
        "anime": "16:9",
    }
    for sc, ar in expect.items():
        assert scenario_aspect(sc) == ar
        plan = DirectorPlanner().plan(
            f"竖屏 9:16 {sc} 测试", duration=15, minimal=True, scenario=sc,
        )
        for s in plan.steps:
            if s.action in ("video", "lipsync", "compose"):
                assert s.params.get("aspect_ratio") == ar, (sc, s.action, s.params)
        if sc == "product_ad":
            refined, changes = refine_plan(plan, "改成竖屏 9:16")
            assert any("锁定" in c or "9:16" in c for c in changes) or all(
                s.params.get("aspect_ratio") == "16:9"
                for s in refined.steps if s.action == "video"
            )


def test_finish_packaging_subtitle_bgm_cta():
    plan = DirectorPlanner().plan(
        "高转化产品广告", duration=15, minimal=True, scenario="product_ad",
    )
    assert any(s.action == "subtitle" for s in plan.steps)
    comp = next(s for s in plan.steps if s.action == "compose")
    assert comp.params.get("bgm") is True
    assert comp.params.get("cta_text")
    assert comp.params.get("export_preset") == "landscape_16_9"


def test_identity_lock_on_video_shots():
    plan = DirectorPlanner().plan(
        "UGC 种草", duration=15, minimal=True, scenario="ugc",
    )
    hero = next(s for s in plan.steps if s.action == "image")
    for s in plan.steps:
        if s.action == "video":
            assert s.params.get("identity_from") == hero.id


def test_anime_multi_shot_narrative_even_minimal():
    plan = DirectorPlanner().plan(
        "新海诚风格动漫短片", duration=15, minimal=True, scenario="anime",
    )
    vids = [s for s in plan.steps if s.action == "video"]
    assert len(vids) >= 2
    titles = " ".join(s.title for s in vids)
    assert any(k in titles for k in ("开场", "登场", "情感", "高潮", "余韵"))
    assert any(s.action == "compose" for s in plan.steps)


def test_talking_voice_and_packaging():
    plan = DirectorPlanner().plan(
        "竖屏数字人口播：专业男主播讲解护肤",
        duration=10, minimal=True, scenario="talking_avatar",
    )
    audio = next(s for s in plan.steps if s.action == "audio")
    assert "Yunxi" in (audio.params.get("voice_id") or "")
    assert any(s.action == "subtitle" for s in plan.steps)
    comp = next(s for s in plan.steps if s.action == "compose")
    assert comp.params.get("keep_source_audio") is True
    assert comp.params.get("aspect_ratio") == "9:16"
