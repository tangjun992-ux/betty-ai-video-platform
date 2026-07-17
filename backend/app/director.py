"""
Director — 导演式编排引擎 (对标 yapper Agent: "DON'T PROMPT, JUST DIRECT")

用户给一句话创作意图，Director 自动：
  1. Plan    — 拆解为多步骤创作计划 (DAG)
  2. Route   — 每步从模型库自动选最合适的模型 + 给出理由 + 预估积分
  3. Execute — 串/并行执行 (复用现有 adapters)，支持 DRY_RUN
  4. Deliver — 产出多资产

这是真实规划逻辑，不是 mock 回复。
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────── 数据模型 ───────────────────────────────
@dataclass
class DirectorStep:
    id: str
    action: str                       # enhance_prompt | image | image_series | video | lipsync | compose
    title: str
    model_id: str
    model_name: str
    reason: str                       # 为什么选这个模型 (导演决策可解释)
    prompt: str
    depends_on: list[str] = field(default_factory=list)
    est_credits: int = 0
    status: str = "pending"           # pending | running | done | failed | skipped
    result: Optional[dict] = None
    params: dict = field(default_factory=dict)   # per-step: aspect_ratio, duration, style, shot
    skip: bool = False                # user toggled off (kept for dependency satisfaction)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "action": self.action, "title": self.title,
            "model_id": self.model_id, "model_name": self.model_name,
            "reason": self.reason, "prompt": self.prompt,
            "depends_on": self.depends_on, "est_credits": self.est_credits,
            "status": self.status, "result": self.result,
            "params": self.params, "skip": self.skip,
        }


@dataclass
class DirectorPlan:
    brief: str
    intent: str                       # image | image_series | video_from_text | video_from_image | talking | campaign
    summary: str
    steps: list[DirectorStep]
    total_credits: int = 0
    scenario: str = ""              # stable card id: product_ad | ugc | ai_portrait | ...

    def to_dict(self) -> dict:
        return {
            "brief": self.brief, "intent": self.intent, "summary": self.summary,
            "total_credits": self.total_credits, "scenario": self.scenario,
            "steps": [s.to_dict() for s in self.steps],
        }


# ─────────────────────────────── 模型选择 ───────────────────────────────
def _catalog() -> list[dict]:
    """延迟读取模型库，避免循环导入。"""
    try:
        from app.api.models_info import MODELS
        return [m.model_dump() if hasattr(m, "model_dump") else m.dict() for m in MODELS]
    except Exception as e:  # pragma: no cover
        logger.warning("[director] catalog load failed: %s", e)
        return []


def _pick_model(media_type: str, want_styles: list[str], prefer: str = "balanced") -> dict:
    """从模型库挑选最合适的模型。prefer: fast | balanced | quality

    可靠性优先：若存在 active(网关已验证可用) 模型，则只在 active 中挑选，避免
    自动路由到 beta/未支持模型导致真实调用 422。用户仍可在编辑器手动切换任意模型。
    """
    all_cands = [m for m in _catalog() if media_type in m["capabilities"]["media_types"]]
    from app.services.model_health import model_health
    active = [
        m for m in all_cands
        if m.get("status") == "active" and model_health.is_routable(m["id"])
    ]
    cands = active or all_cands
    if not cands:
        # 兜底
        return {"id": "seedance-2.0" if media_type == "video" else "gpt-image-2",
                "display_name": "Seedance 2.0" if media_type == "video" else "GPT Image 2",
                "capabilities": {"styles": [], "cost_per_image_credits": 5, "cost_per_5s_video_credits": 4,
                                 "avg_latency_s": 30}, "cost_tier": "medium", "status": "active"}

    def score(m: dict) -> float:
        caps = m["capabilities"]
        s = 0.0
        # 风格契合
        s += 3.0 * len(set(want_styles) & set(caps["styles"]))
        # active 优先 (已验证可用)
        s += 2.0 if m["status"] == "active" else 0.0
        # 偏好档位
        tier = m["cost_tier"]
        if prefer == "fast":
            s += {"low": 2, "medium": 1, "high": 0}.get(tier, 0)
            s -= caps["avg_latency_s"] / 60.0
        elif prefer == "quality":
            s += {"low": 0, "medium": 1, "high": 2}.get(tier, 0)
        else:  # balanced
            s += {"low": 1, "medium": 1.5, "high": 1}.get(tier, 0)
        # Feed live execution reliability back into Director planning.
        s -= max(0.0, (100.0 - model_health.score(m["id"])) * 0.03)
        return s

    return max(cands, key=score)


def _credits_of(model: dict, media_type: str, duration: int = 5) -> int:
    caps = model["capabilities"]
    if media_type == "image":
        return int(caps.get("cost_per_image_credits", 5))
    per5 = int(caps.get("cost_per_5s_video_credits", 4))
    return max(per5, round(duration / 5 * per5))


# ─────────────────────────────── 意图识别 ───────────────────────────────
_VIDEO_KW = [
    "视频", "短片", "宣传片", "广告", "动画", "video", "片子", "镜头", "运镜", "vlog", "短视频",
    # English short-form / ads (matched with word boundaries via _has)
    "ad", "ads", "commercial", "promo", "trailer", "reel", "reels", "clip", "spot", "film", "movie",
]
_TALK_KW = ["口播", "说话", "讲解", "数字人", "主播", "唇形", "talking", "avatar", "配音"]
_SERIES_KW = ["系列", "分镜", "九宫格", "多张", "一组", "套图", "storyboard", "series"]
_IMG_KW = ["图片", "图", "海报", "logo", "标志", "头像", "写真", "插画", "封面", "image", "poster"]
_CAMPAIGN_KW = ["营销", "电商", "带货", "产品", "推广", "campaign", "品牌", "种草"]
# Explicit still-image-only briefs — used to avoid forcing video in minimal mode
_IMAGE_ONLY_KW = ["只要图", "只要图片", "静图", "still image", "image only", "海报图", "logo设计"]


def _styles_from_brief(brief: str) -> list[str]:
    m = {
        "电影": "cinematic", "写实": "realistic", "真实": "realistic", "动漫": "anime",
        "二次元": "anime", "国风": "chinese", "中式": "chinese", "产品": "product",
        "人像": "portrait", "数字人": "portrait", "口播": "portrait", "主播": "portrait",
        "棚拍": "portrait", "半身": "portrait", "风景": "landscape", "科幻": "sci-fi",
        "奇幻": "fantasy", "美食": "food", "logo": "logo", "海报": "poster",
        "矢量": "vector", "梗图": "meme",
    }
    found = [v for k, v in m.items() if k in brief.lower()]
    # Talking / avatar briefs: portrait must win over incidental「产品」卖点.
    if _has(brief, _TALK_KW) and "portrait" in found:
        found = ["portrait"] + [s for s in found if s != "portrait"]
    elif _has(brief, _TALK_KW):
        found = ["portrait"] + found
    return list(dict.fromkeys(found)) or ["cinematic", "realistic"]


def _has(brief: str, kws: list[str]) -> bool:
    """Substring match for CJK / long tokens; word-boundary for short ASCII (avoid 'ad' in 'ready')."""
    b = brief.lower()
    for k in kws:
        token = k.lower()
        if not token:
            continue
        if token.isascii() and len(token) <= 4:
            if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", b):
                return True
        elif token in b:
            return True
    return False


# ─────────────────────────── 分镜 / 运镜 编导语汇 ───────────────────────────
# 顶级导演型 Agent 的关键：把一句话拆成有叙事节奏的分镜，每镜有独立、专业的
# 镜头级 prompt（景别 + 运镜 + 光影），而不是把原始 brief 复制到每一步。

_SHOT_BEATS = [
    ("建立镜头", "大远景交代环境与氛围，缓慢推进", "wide establishing shot, slow push-in"),
    ("主体特写", "特写突出主体质感与细节，浅景深", "detailed close-up, shallow depth of field"),
    ("动态镜头", "中景展现动作过程，平稳跟随运镜", "medium tracking shot following the action"),
    ("情绪高潮", "戏剧性用光与构图，营造张力", "dramatic lighting, high-tension composition"),
    ("氛围镜头", "空镜/细节点缀，丰富叙事层次", "atmospheric insert shot, textured details"),
    ("收尾镜头", "拉远留白，余韵收束", "pull-back closing shot, breathing room"),
]

_ASPECT_BY_STYLE = {
    "portrait": "9:16", "product": "1:1", "cinematic": "16:9",
    "landscape": "16:9", "anime": "16:9",
}


def _aspect_for(styles: list[str], vertical_hint: bool = False) -> str:
    if vertical_hint:
        return "9:16"
    for s in styles:
        if s in _ASPECT_BY_STYLE:
            return _ASPECT_BY_STYLE[s]
    return "16:9"


def _style_phrase(styles: list[str]) -> str:
    names = {
        "cinematic": "电影感", "realistic": "写实", "anime": "动漫", "chinese": "国风",
        "product": "产品商业", "portrait": "人像", "landscape": "风光", "sci-fi": "科幻",
        "fantasy": "奇幻", "food": "美食", "poster": "海报", "vector": "矢量", "meme": "梗图",
    }
    return "、".join(names.get(s, s) for s in styles[:2])


def _shot_prompt(brief: str, beat_cn: str, camera_en: str, styles: list[str]) -> str:
    """Compose a professional shot-level prompt from the brief + a narrative beat."""
    sp = _style_phrase(styles)
    return f"{brief}｜{beat_cn}：{camera_en}，{sp}风格，电影级布光，高细节"


def _series_subject_brief(brief: str) -> str:
    """Strip '四张/一组/系列' count language so each still is a single frame, not a collage."""
    cleaned = re.sub(
        r"(一组|一套|系列|四张|4张|九宫格|多张|套图|四视图|四姿态)",
        "",
        brief or "",
    )
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ，,")
    return cleaned or (brief or "").strip()


def _n_shots(duration: int) -> int:
    """More screen time → more narrative shots (clamped for cost/latency)."""
    return max(1, min(round(duration / 5), 6))


# ─────────────────────────────── 规划器 ───────────────────────────────
class DirectorPlanner:
    def plan(self, brief: str, has_ref_image: bool = False, duration: int = 5,
             ref_image_url: str | None = None, *, minimal: bool = False,
             scenario: str | None = None) -> DirectorPlan:
        """Plan a director workflow.

        ``scenario`` — stable Agent card id (product_ad / ugc / ai_portrait / …).
        When set, uses scenario-specific beats/models/aspect (top-tier card parity).
        ``minimal=True`` skips TTS/subtitle; multi-shot scenarios still stitch compose.
        """
        from app.director_scenarios import (
            AD_BEATS, COMMERCIAL_BEATS, UGC_BEATS, DRAMA_BEATS,
            PRODUCT_PHOTO_VARIATIONS, PORTRAIT_VARIATIONS,
            infer_scenario, scenario_vertical, scenario_intent, SCENARIO_IDS,
        )

        brief = (brief or "").strip()
        has_ref_image = has_ref_image or bool(ref_image_url)
        scenario = (scenario or "").strip().lower()
        if scenario and scenario not in SCENARIO_IDS:
            scenario = ""
        if not scenario:
            scenario = infer_scenario(brief)

        # Brief keywords can force minimal / quick mode (对标 Yapper "just direct")
        if _has(brief, ["快速成片", "最短路径", "minimal", "quick direct", "只要视频", "不要配音"]):
            minimal = True
        # Parse an explicit duration from the brief ("30秒 / 30s / 30 seconds") so the
        # storyboard length matches the user's stated intent, not just the UI dropdown.
        dm = re.search(r"(\d{1,3})\s*(?:秒|s\b|sec|seconds?)", brief, re.I)
        if dm:
            duration = max(5, min(int(dm.group(1)), 60))
        styles = _styles_from_brief(brief)
        vertical = _has(brief, ["竖屏", "抖音", "tiktok", "reels", "shorts", "手机", "9:16"])
        if scenario and scenario_vertical(scenario):
            vertical = True

        # Scenario style bias (prevents「产品」keyword from drowning portrait/anime)
        if scenario == "ai_portrait" or scenario == "talking_avatar":
            styles = ["portrait", "realistic"] + [s for s in styles if s not in ("product", "portrait")]
        elif scenario == "product_photo":
            styles = ["product", "realistic"] + [s for s in styles if s != "product"]
        elif scenario == "anime":
            styles = ["anime"] + [s for s in styles if s != "anime"]
        elif scenario == "ugc":
            styles = ["realistic", "product"] + [s for s in styles if s not in ("cinematic",)]
        elif scenario in ("product_ad", "product_commercial"):
            styles = ["product", "cinematic", "realistic"] + [s for s in styles if s not in ("product", "cinematic")]
        elif scenario == "micro_drama":
            styles = ["cinematic", "realistic"] + styles

        steps: list[DirectorStep] = []

        def sid() -> str:
            return uuid.uuid4().hex[:8]

        # 1) 创意解析 & 分镜脚本 (导演先把口语 brief 变成专业分镜脚本)
        enh_id = sid()
        steps.append(DirectorStep(
            id=enh_id, action="enhance_prompt", title="解析创意 & 编写分镜脚本",
            model_id="prompt-enhancer", model_name="Director LLM",
            reason="把口语意图拆解为带景别/运镜/光影/风格的专业分镜脚本", prompt=brief,
            est_credits=0, params={"styles": styles, "scenario": scenario or None},
        ))

        img_aspect = _aspect_for(styles, vertical)
        vid_aspect = "9:16" if vertical else _aspect_for(styles)
        if scenario == "product_photo":
            img_aspect = "1:1"
        elif scenario == "ai_portrait":
            img_aspect = "3:4"

        # Yapper quick-direct: minimal ⇒ 默认视频最短路径，除非 brief 明确只要静图
        force_video = bool(minimal) and not _has(brief, _IMAGE_ONLY_KW) and not _has(brief, _SERIES_KW)
        # Explicit scenario cards always win over keyword force_video heuristics
        force_image_series = scenario in ("product_photo", "ai_portrait")

        intent = scenario_intent(scenario) if scenario else ""

        def _add_video_shots(prev: str, beats: list, n: int, vid: dict, aspect: str) -> list[str]:
            ids: list[str] = []
            for i in range(n):
                beat_cn, beat_desc, cam_en = beats[i % len(beats)]
                sv = DirectorStep(
                    id=sid(), action="video",
                    title=f"分镜 {i+1}/{n} · {beat_cn}",
                    model_id=vid["id"], model_name=vid["display_name"],
                    reason=f"{beat_desc}，选 {vid['display_name']}",
                    prompt=_shot_prompt(brief, f"{beat_cn}·{beat_desc}", cam_en, styles),
                    depends_on=[prev], est_credits=_credits_of(vid, "video", 5),
                    params={"aspect_ratio": aspect, "duration": 5, "shot": i + 1},
                )
                steps.append(sv)
                ids.append(sv.id)
                prev = sv.id
            return ids

        # ── Scenario-first planning (8 Agent cards) ─────────────────────
        if scenario == "talking_avatar" or (not scenario and _has(brief, _TALK_KW)):
            intent = "talking"
            scenario = scenario or "talking_avatar"
            img = _pick_model("image", styles + ["portrait"], "quality")
            s_voice = DirectorStep(id=sid(), action="audio", title="AI 配音 · 旁白 (TTS)",
                model_id="elevenlabs-tts", model_name="ElevenLabs TTS",
                reason="把脚本转成自然旁白，用于驱动数字人口型与成片解说",
                prompt=brief, depends_on=[enh_id], est_credits=2, params={"script": brief})
            s_img = DirectorStep(id=sid(), action="image", title="生成数字人形象",
                model_id=img["id"], model_name=img["display_name"],
                reason=f"口播需要高保真人像，选 {img['display_name']}（人像/写实强）",
                prompt=(f"{brief}｜digital human talking-head portrait, front-facing, "
                        "chest-up, professional softbox, clean backdrop, natural skin, mouth slightly closed"),
                depends_on=[enh_id], est_credits=_credits_of(img, "image"),
                params={"aspect_ratio": "9:16" if vertical else "3:4"})
            s_talk = DirectorStep(id=sid(), action="lipsync", title="唇形同步驱动 (数字人开口)",
                model_id="kling-avatar", model_name="Kling AI Avatar",
                reason="用旁白音频精准驱动人像口型，生成自然开口说话的数字人",
                prompt=("natural talking head to camera, precise lip sync matching speech audio, "
                        "subtle blinks and micro head motion, identity locked, no warping"),
                depends_on=[s_img.id, s_voice.id], est_credits=6,
                params={"aspect_ratio": "9:16" if vertical else "16:9"})
            steps += [s_voice, s_img, s_talk]

        elif scenario in ("product_ad", "product_commercial", "ugc") or (
            not scenario and _has(brief, _CAMPAIGN_KW) and _has(brief, _VIDEO_KW)
        ):
            intent = "campaign"
            if not scenario:
                scenario = infer_scenario(brief) or "product_ad"
            img = _pick_model("image", styles + ["product"], "quality")
            def _force_vid(*prefer_ids: str, fallback_styles: list[str], prefer: str) -> dict:
                for mid in prefer_ids:
                    hit = next((m for m in _catalog() if m["id"] == mid), None)
                    if hit:
                        return hit
                return _pick_model("video", fallback_styles, prefer)

            # UGC: Pro for native look; ads/commercial: Master for film grade
            if scenario == "ugc":
                vid = _force_vid("kling-2.1-pro", "kling-2.1-master",
                                 fallback_styles=["realistic"], prefer="balanced")
                beats, hero = UGC_BEATS, (
                    f"{brief}｜UGC creator holding product, natural phone-camera look, "
                    "real-life room light, vertical 9:16 framing, authentic not cinematic"
                )
                n = min(3, max(2, _n_shots(duration)))
                vid_aspect = "9:16"
                img_aspect = "9:16"
            elif scenario == "product_commercial":
                vid = _force_vid("kling-2.1-master", "kling-2.1-pro",
                                 fallback_styles=styles, prefer="quality")
                beats, hero = COMMERCIAL_BEATS, (
                    f"{brief}｜luxury brand hero product still, cinematic soft light, "
                    "premium materials, campaign key art, 16:9"
                )
                n = max(4, _n_shots(duration))  # commercial never collapses to 1 shot
                vid_aspect = "16:9"
            else:  # product_ad
                vid = _force_vid("kling-2.1-master", "kling-2.1-pro",
                                 fallback_styles=styles, prefer="quality")
                beats, hero = AD_BEATS, (
                    f"{brief}｜high-converting product ad hero frame, crisp commercial lighting, "
                    "instant product readability, social-ad key art"
                )
                n = min(3, max(2, _n_shots(duration))) if duration <= 15 else _n_shots(duration)
                vid_aspect = "9:16" if vertical else "16:9"

            s_img = DirectorStep(id=sid(), action="image", title="产品主视觉 (Hero Shot)",
                model_id=img["id"], model_name=img["display_name"],
                reason=f"营销片首帧需精致主视觉，选 {img['display_name']}",
                prompt=hero, depends_on=[enh_id], est_credits=_credits_of(img, "image"),
                params={"aspect_ratio": img_aspect})
            steps.append(s_img)
            _add_video_shots(s_img.id, beats, n, vid, vid_aspect)

        elif scenario == "micro_drama":
            intent = "video_from_text"
            img = _pick_model("image", styles + ["cinematic"], "quality")
            # Prefer Seedance for narrative motion
            vid = _pick_model("video", styles, "balanced")
            for mid in ("seedance-2.0",):
                hit = next((m for m in _catalog() if m["id"] == mid), None)
                if hit:
                    vid = hit
                    break
            # Top-tier short drama needs multi-beat even in「快速成片」
            n = 2 if minimal else max(3, min(_n_shots(duration), 4))
            s_img = DirectorStep(id=sid(), action="image", title="短剧首帧 · 人物情绪",
                model_id=img["id"], model_name=img["display_name"],
                reason="锁定人物身份与情绪基调",
                prompt=(f"{brief}｜vertical micro-drama keyframe, expressive lead character, "
                        "cinematic face light, strong emotional subtext, 9:16"),
                depends_on=[enh_id], est_credits=_credits_of(img, "image"),
                params={"aspect_ratio": "9:16"})
            steps.append(s_img)
            _add_video_shots(s_img.id, DRAMA_BEATS, n, vid, "9:16")

        elif scenario == "anime":
            intent = "video_from_text"
            img = _pick_model("image", ["anime"], "balanced")
            vid = _pick_model("video", ["anime"], "balanced")
            for mid in ("nano-banana", "nano-banana-pro"):
                hit = next((m for m in _catalog() if m["id"] == mid), None)
                if hit:
                    img = hit
                    break
            for mid in ("seedance-2.0",):
                hit = next((m for m in _catalog() if m["id"] == mid), None)
                if hit:
                    vid = hit
                    break
            n = 1 if minimal else min(3, _n_shots(duration))
            s_img = DirectorStep(id=sid(), action="image", title="动漫关键帧",
                model_id=img["id"], model_name=img["display_name"],
                reason="锁定二次元角色与光影",
                prompt=(f"{brief}｜anime keyframe, Makoto Shinkai inspired luminous atmosphere, "
                        "detailed character, cinematic color, NOT photoreal live-action"),
                depends_on=[enh_id], est_credits=_credits_of(img, "image"),
                params={"aspect_ratio": "16:9"})
            steps.append(s_img)
            _add_video_shots(s_img.id, _SHOT_BEATS, n, vid, "16:9")

        elif scenario == "ai_portrait" or (
            force_image_series is False and not scenario and _has(brief, ["写真", "形象照", "领英"]) and _has(brief, _SERIES_KW)
        ):
            intent = "image_series"
            scenario = scenario or "ai_portrait"
            img = _pick_model("image", ["portrait", "realistic"], "quality")
            for mid in ("gpt-image-2", "nano-banana-pro"):
                hit = next((m for m in _catalog() if m["id"] == mid), None)
                if hit:
                    img = hit
                    break
            subject = _series_subject_brief(brief)
            for i, (title_cn, en) in enumerate(PORTRAIT_VARIATIONS):
                steps.append(DirectorStep(
                    id=sid(), action="image", title=f"形象照 {i+1}/4 · {title_cn}",
                    model_id=img["id"], model_name=img["display_name"],
                    reason=f"职业写真套图 · {title_cn}（对标 HeadshotPro）",
                    prompt=(f"{subject}｜{title_cn}：{en}，same person identity, matching wardrobe color grade, "
                            "ONE single professional headshot photograph only, "
                            "NOT a collage, NOT a grid, NOT multiple panels, NOT product photography"),
                    depends_on=[enh_id], est_credits=_credits_of(img, "image"),
                    params={"aspect_ratio": "3:4"},
                ))

        elif scenario == "product_photo" or (
            not scenario and _has(brief, _SERIES_KW) and _has(brief, ["产品", "影棚", "产品摄影"])
        ):
            intent = "image_series"
            scenario = scenario or "product_photo"
            img = _pick_model("image", ["product", "realistic"], "quality")
            subject = _series_subject_brief(brief)
            for i, (title_cn, en) in enumerate(PRODUCT_PHOTO_VARIATIONS):
                steps.append(DirectorStep(
                    id=sid(), action="image", title=f"产品摄影 {i+1}/4 · {title_cn}",
                    model_id=img["id"], model_name=img["display_name"],
                    reason=f"影棚套图 · {title_cn}（对标 Photoroom/Claid）",
                    prompt=(f"{subject}｜{title_cn}：{en}，consistent brand color and lighting, "
                            "ONE single product photo only, NOT a collage, NOT a contact sheet, NOT a grid"),
                    depends_on=[enh_id], est_credits=_credits_of(img, "image"),
                    params={"aspect_ratio": "1:1"},
                ))

        elif _has(brief, _VIDEO_KW) or has_ref_image or (force_video and not force_image_series):
            n = 1 if minimal else _n_shots(duration)
            if has_ref_image:
                intent = "video_from_image"
                vid = _pick_model("video", styles, "balanced")
                prev = enh_id
                for i in range(n):
                    beat_cn, beat_desc, cam_en = _SHOT_BEATS[i % len(_SHOT_BEATS)]
                    sv = DirectorStep(id=sid(), action="video",
                        title=(f"分镜 {i+1}/{n} · {beat_cn}" if n > 1 else "参考图转视频"),
                        model_id=vid["id"], model_name=vid["display_name"],
                        reason=f"已有参考图，图生视频 · {beat_desc}",
                        prompt=_shot_prompt(brief, f"{beat_cn}·{beat_desc}", cam_en, styles),
                        depends_on=[prev], est_credits=_credits_of(vid, "video", 5),
                        params={"aspect_ratio": vid_aspect, "duration": 5, "shot": i + 1})
                    steps.append(sv)
                    prev = sv.id
            else:
                intent = "video_from_text"
                img = _pick_model("image", styles, "balanced")
                vid = _pick_model("video", styles, "balanced")
                s_img = DirectorStep(id=sid(), action="image", title="首帧关键画面 (Keyframe)",
                    model_id=img["id"], model_name=img["display_name"],
                    reason=f"先定首帧锁定主体与风格，选 {img['display_name']}",
                    prompt=f"{brief}｜首帧关键画面，{_style_phrase(styles)}风格，电影级构图与布光",
                    depends_on=[enh_id], est_credits=_credits_of(img, "image"),
                    params={"aspect_ratio": img_aspect})
                steps.append(s_img)
                _add_video_shots(s_img.id, _SHOT_BEATS, n, vid, vid_aspect)

        elif _has(brief, _SERIES_KW):
            intent = "image_series"
            img = _pick_model("image", styles, "balanced")
            # Portrait briefs without explicit scenario still get headshot angles
            if _has(brief, ["写真", "形象", "人像", "头像", "领英"]):
                scenario = scenario or "ai_portrait"
                variations = PORTRAIT_VARIATIONS
                aspect = "3:4"
            else:
                variations = [(a, a) for a in ("正面主视角", "侧面 45° 视角", "特写细节", "环境全景")]
                aspect = img_aspect
            for i, v in enumerate(variations):
                title_cn, extra = v if isinstance(v, tuple) else (v, v)
                steps.append(DirectorStep(id=sid(), action="image", title=f"系列图 {i+1}/4 · {title_cn}",
                    model_id=img["id"], model_name=img["display_name"],
                    reason=f"成套出图保持风格一致 · {title_cn}，选 {img['display_name']}",
                    prompt=f"{brief}｜{title_cn}：{extra}，统一{_style_phrase(styles)}风格与配色",
                    depends_on=[enh_id], est_credits=_credits_of(img, "image"),
                    params={"aspect_ratio": aspect}))

        else:
            intent = "image"
            img = _pick_model("image", styles, "quality")
            steps.append(DirectorStep(id=sid(), action="image", title="生成图片",
                model_id=img["id"], model_name=img["display_name"],
                reason=f"单图创作，选质量优先的 {img['display_name']}",
                prompt=f"{brief}｜{_style_phrase(styles)}风格，电影级布光，精致构图，高细节",
                depends_on=[enh_id], est_credits=_credits_of(img, "image"),
                params={"aspect_ratio": img_aspect}))

        # 视频后期：多镜必须合成一条成片（对标顶级投放/短剧平台）
        # minimal：跳过配音/字幕，但仍 stitch；完整成片：TTS+字幕+合成
        video_steps = [s for s in steps if s.action in ("video", "lipsync")]
        multi = len([s for s in steps if s.action == "video"]) > 1
        if video_steps and intent != "talking":
            vid_ids = [s.id for s in video_steps if s.action == "video"] or [s.id for s in video_steps]
            if not minimal:
                s_audio = DirectorStep(id=sid(), action="audio", title="AI 配音 · 解说 (TTS)",
                    model_id="elevenlabs-tts", model_name="ElevenLabs TTS",
                    reason="将创意脚本转成自然解说旁白，随成片一起输出",
                    prompt=brief, depends_on=[vid_ids[-1]], est_credits=2, params={"script": brief})
                s_sub = DirectorStep(id=sid(), action="subtitle", title="智能字幕",
                    model_id="subtitle-engine", model_name="Auto Caption",
                    reason="自动生成并烧录字幕，适配社媒传播",
                    prompt=brief, depends_on=[vid_ids[-1]], est_credits=1)
                s_comp = DirectorStep(id=sid(), action="compose", title="剪辑合成成片",
                    model_id="compose-engine", model_name="FFmpeg Compose",
                    reason=f"将 {len(vid_ids)} 个分镜 + 配乐 + 字幕剪辑合成为最终可发布成片",
                    prompt=brief, depends_on=vid_ids + [s_audio.id, s_sub.id], est_credits=0)
                steps += [s_audio, s_sub, s_comp]
            elif multi:
                # 快速成片但仍交付「一条成片」，避免散落分镜无法验收
                s_comp = DirectorStep(id=sid(), action="compose", title="分镜合成成片",
                    model_id="compose-engine", model_name="FFmpeg Compose",
                    reason=f"将 {len(vid_ids)} 个分镜合成为一条可发布成片（快速模式跳过配音字幕）",
                    prompt=brief, depends_on=vid_ids, est_credits=0)
                steps.append(s_comp)

        # 跨镜共享 seed（保持全片风格一致）+ 参考图注入（真正参与图生视频）
        shared_seed = hashlib.sha1((brief or "x").encode()).hexdigest()[:12]
        for s in steps:
            if s.action in ("image", "video", "lipsync"):
                s.params = {**(s.params or {}), "seed": shared_seed, "scenario": scenario or None}
                if ref_image_url and s.action in ("video", "lipsync"):
                    s.params["image_url"] = ref_image_url

        total = sum(s.est_credits for s in steps)
        n_assets = len([s for s in steps if s.action in ("image", "video", "lipsync", "compose")])
        n_shots = len([s for s in steps if s.action == "video"])
        shot_note = f"，{n_shots} 个分镜" if n_shots > 1 else ""
        sc_note = f"，场景：{scenario}" if scenario else ""
        summary = (f"已规划 {len(steps)} 步{shot_note}，将产出 {n_assets} 个资产，"
                   f"预计消耗 {total} 积分。意图：{intent}{sc_note}")
        return DirectorPlan(
            brief=brief, intent=intent, summary=summary, steps=steps,
            total_credits=total, scenario=scenario or "",
        )


def _catalog_lookup(directive: str, media_type: str):
    """Find a model in the catalog whose name/id appears in the directive."""
    d = directive.lower()
    for m in _catalog():
        if media_type not in m["capabilities"]["media_types"]:
            continue
        name = (m.get("display_name") or "").lower()
        mid = (m.get("id") or "").lower()
        # match by id token, or by display name w/o spaces (e.g. "veo 3.1" ~ "veo3.1")
        if mid and mid in d:
            return m
        if name and (name in d or name.replace(" ", "") in d.replace(" ", "")):
            return m
    return None


_REFINE_MOODS = [
    (["暖", "warmer", "warm", "金色"], "暖色调，金色光线"),
    (["冷色", "更冷", "cooler", "cool", "冷调", "冷峻"], "冷色调，冷峻光线"),
    (["电影感", "cinematic", "大片"], "更强电影感，戏剧性布光"),
    (["明亮", "brighter", "bright", "清新"], "明亮通透，高调布光"),
    (["暗", "darker", "dark", "低调", "深沉"], "暗调氛围，低调布光"),
    (["快节奏", "faster", "fast", "动感"], "快节奏，凌厉剪辑感"),
    (["舒缓", "slower", "slow", "慢节奏", "治愈"], "舒缓节奏，柔和过渡"),
    (["梦幻", "dreamy", "唯美"], "梦幻唯美，柔光颗粒"),
    (["高级", "premium", "质感"], "高级质感，精致细节"),
]

_ASPECT_DIRECTIVES = [
    (["竖屏", "vertical", "9:16", "抖音", "tiktok", "reels", "shorts"], "9:16"),
    (["横屏", "landscape", "16:9", "宽屏"], "16:9"),
    (["方形", "square", "1:1"], "1:1"),
]


def refine_plan(plan: DirectorPlan, directive: str) -> tuple[DirectorPlan, list[str]]:
    """Apply a natural-language director directive to an existing plan.

    Deterministic rules (no LLM needed): mood/color, pace, aspect ratio, add/remove
    a shot, swap model, target a specific shot ("第2镜"), plus a catch-all note.
    Returns (updated_plan, list of human-readable applied changes).
    """
    d = (directive or "").strip()
    changes: list[str] = []
    steps = plan.steps
    media_steps = [s for s in steps if s.action in ("image", "video", "lipsync")]
    video_steps = [s for s in steps if s.action in ("video", "lipsync")]

    def sid() -> str:
        return uuid.uuid4().hex[:8]

    # Target a specific shot? "第2镜 / shot 2 / 分镜3"
    target = None
    m = re.search(r"(?:第|分镜|shot)\s*([0-9一二三四五六七八九十]+)", d, re.I)
    if m:
        num_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}
        raw = m.group(1)
        idx = num_map.get(raw, None) or (int(raw) if raw.isdigit() else None)
        if idx and 1 <= idx <= len(video_steps):
            target = video_steps[idx - 1]

    scope = [target] if target else media_steps

    # 1) Mood / color / pace → append style note to scoped prompts
    applied_note = None
    for kws, note in _REFINE_MOODS:
        if _has(d, kws):
            applied_note = note
            for s in scope:
                if note not in s.prompt:
                    s.prompt = f"{s.prompt}，{note}"
            changes.append(f"{'第' + str(idx) + '镜' if target else '全部镜头'}调整为「{note}」")
            break

    # 2) Aspect ratio
    for kws, ratio in _ASPECT_DIRECTIVES:
        if _has(d, kws):
            for s in media_steps:
                s.params = {**(s.params or {}), "aspect_ratio": ratio}
            changes.append(f"画幅改为 {ratio}")
            break

    # 3) Model swap (video first, then image)
    for mt, label in (("video", "视频"), ("image", "图片")):
        found = _catalog_lookup(d, mt)
        if found and _has(d, ["换", "改用", "用", "switch", "use", "换成"]):
            for s in (video_steps if mt == "video" else [x for x in media_steps if x.action == "image"]):
                s.model_id = found["id"]
                s.model_name = found["display_name"]
            changes.append(f"{label}模型换为 {found['display_name']}")
            break

    # 4) Add a shot
    if _has(d, ["加镜头", "加一个镜头", "多一个镜头", "增加镜头", "再来一个镜头", "add shot", "加个镜头", "多来"]):
        if video_steps:
            base = video_steps[-1]
            styles = (base.params or {}).get("styles") or _styles_from_brief(plan.brief)
            beat_cn, beat_desc, cam_en = _SHOT_BEATS[len(video_steps) % len(_SHOT_BEATS)]
            new = DirectorStep(
                id=sid(), action="video", title=f"分镜 {len(video_steps)+1} · {beat_cn}",
                model_id=base.model_id, model_name=base.model_name,
                reason=f"新增分镜 · {beat_desc}",
                prompt=_shot_prompt(plan.brief, f"{beat_cn}·{beat_desc}", cam_en, styles),
                depends_on=list(base.depends_on), est_credits=base.est_credits,
                params=dict(base.params or {}))
            # insert right after the last video step
            pos = steps.index(base) + 1
            steps.insert(pos, new)
            # compose should depend on the new shot too
            for s in steps:
                if s.action == "compose" and base.id in s.depends_on:
                    s.depends_on.append(new.id)
            changes.append("新增 1 个分镜")

    # 5) Remove a shot
    elif _has(d, ["删镜头", "少一个镜头", "去掉镜头", "删掉", "remove shot", "减一个", "少个镜头"]) and len(video_steps) > 1:
        victim = target or video_steps[-1]
        steps[:] = [s for s in steps if s.id != victim.id]
        for s in steps:
            if victim.id in s.depends_on:
                s.depends_on = [x for x in s.depends_on if x != victim.id]
        changes.append("删除 1 个分镜")

    # 6) Catch-all: if nothing matched, append the raw directive as a director's note
    if not changes and d:
        for s in scope:
            s.prompt = f"{s.prompt}，{d}"
        changes.append(f"已按指令微调镜头：{d[:24]}")

    # Recompute totals + summary
    plan.total_credits = sum(s.est_credits for s in plan.steps if not s.skip)
    n_shots = len([s for s in plan.steps if s.action == "video"])
    n_assets = len([s for s in plan.steps if s.action in ("image", "video", "lipsync", "compose")])
    plan.summary = (f"已按导演指令更新：{'；'.join(changes)}。共 {len(plan.steps)} 步"
                    f"{('，' + str(n_shots) + ' 个分镜') if n_shots > 1 else ''}，"
                    f"预计 {plan.total_credits} 积分。")
    return plan, changes


def plan_from_dict(data: dict) -> DirectorPlan:
    """Rebuild a DirectorPlan from a (possibly user-edited) client payload."""
    steps = []
    for s in data.get("steps", []):
        if not isinstance(s, dict):
            continue
        steps.append(DirectorStep(
            id=s.get("id") or uuid.uuid4().hex[:8],
            action=s.get("action", "image"),
            title=s.get("title", ""),
            model_id=s.get("model_id", ""),
            model_name=s.get("model_name", ""),
            reason=s.get("reason", ""),
            prompt=s.get("prompt", data.get("brief", "")),
            depends_on=s.get("depends_on", []) or [],
            est_credits=int(s.get("est_credits", 0) or 0),
            params=s.get("params", {}) or {},
            skip=bool(s.get("skip", False)),
        ))
    total = sum(s.est_credits for s in steps if not s.skip)
    return DirectorPlan(
        brief=data.get("brief", ""),
        intent=data.get("intent", "image"),
        summary=data.get("summary", ""),
        steps=steps, total_credits=total,
        scenario=data.get("scenario", "") or "",
    )


# ─────────────────────── aspect ratio → 渲染尺寸 ───────────────────────
_RATIO_TO_SIZE = {
    "16:9": "1280x720", "9:16": "720x1280", "1:1": "1024x1024",
    "3:4": "768x1024", "4:3": "1024x768", "21:9": "1280x548", "3:2": "1080x720",
}


def _size_from_params(params: dict, default: str) -> str:
    ratio = (params or {}).get("aspect_ratio")
    return _RATIO_TO_SIZE.get(ratio, default)


_ASPECT_TO_EXPORT = {
    "16:9": "landscape_16_9",
    "9:16": "portrait_9_16",
    "1:1": "square_1_1",
}


def _export_preset_from_params(params: dict | None) -> str | None:
    if not params:
        return None
    preset = params.get("export_preset")
    if preset:
        return preset
    ratio = params.get("aspect_ratio")
    return _ASPECT_TO_EXPORT.get(ratio)


def _script_to_subtitle_track(script: str, duration_per_cue: float = 3.0) -> list[dict]:
    """Build simple timed cues from narration script (Director ↔ timeline/SRT bridge)."""
    parts = re.split(r"[。！？\n.!?]+", script or "")
    cues: list[dict] = []
    t = 0.0
    for part in parts:
        text = part.strip()
        if not text:
            continue
        cues.append({
            "text": text,
            "start": round(t, 3),
            "end": round(t + duration_per_cue, 3),
        })
        t += duration_per_cue
    return cues


# ─────────────────────────────── 执行器 ───────────────────────────────
class DirectorExecutor:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    async def _run_step(self, step: DirectorStep) -> dict:
        step.status = "running"
        try:
            if step.action == "enhance_prompt":
                enhanced = step.prompt
                try:
                    from app.prompt_enhancer import enhancer
                    styles = (step.params or {}).get("styles") or _styles_from_brief(step.prompt)
                    out = enhancer.enhance(step.prompt, media_type="auto",
                                           style=(styles[0] if styles else "auto"), quality="high")
                    enhanced = getattr(out, "enhanced", None) or (
                        out.get("enhanced_prompt", step.prompt) if isinstance(out, dict) else step.prompt)
                except Exception:
                    enhanced = f"{step.prompt}，电影级画质，柔和自然光，高细节，专业构图"
                step.status = "done"
                return {"type": "prompt", "enhanced_prompt": enhanced}

            if step.action == "subtitle":
                results = getattr(self, "_results", {}) or {}
                subtitle_track: list[dict] = []
                params = step.params or {}

                srt_content = params.get("srt") or params.get("srt_content")
                if srt_content:
                    from app.adapters.demo_provider import parse_srt
                    subtitle_track = parse_srt(srt_content)
                else:
                    script = params.get("script") or step.prompt or ""
                    if not script:
                        for dep in step.depends_on:
                            r = results.get(dep)
                            if not isinstance(r, dict):
                                continue
                            script = (
                                r.get("script")
                                or r.get("enhanced_prompt")
                                or r.get("prompt")
                                or script
                            )
                    cue_duration = float(params.get("cue_duration", 3.0) or 3.0)
                    subtitle_track = _script_to_subtitle_track(script, cue_duration)

                self._subtitle_track = subtitle_track
                step.status = "done"
                return {
                    "type": "subtitle",
                    "subtitle_track": subtitle_track,
                    "cue_count": len(subtitle_track),
                    "model": step.model_name,
                    "cost": step.est_credits,
                }

            if step.action == "audio":
                # Real TTS voiceover (配音) — narration that the final film muxes,
                # and that lip-sync uses to drive the avatar. Demo → local tone.
                script = (step.params or {}).get("script") or step.prompt or ""
                script = script[:600]
                try:
                    from app.adapters.demo_provider import demo_mode_active
                    use_demo_a = self.dry_run or demo_mode_active()
                except Exception:
                    use_demo_a = self.dry_run
                try:
                    if use_demo_a:
                        from app.adapters.demo_provider import render_demo_speech
                        url = await asyncio.to_thread(render_demo_speech, script)
                        step.status = "done"
                        return {
                            "type": "audio", "url": url, "media_url": url,
                            "model": "demo-tts", "planned_model": step.model_id,
                            "mode": "demo_tone", "honesty": "offline_preview_not_tts",
                            "cost": 0, "narration": True,
                        }
                    from app.adapters.kie_adapter import KieAdapter
                    from app.services.media_store import persist_results
                    from app.services.audio_prep import synthesize_speech_edge
                    import uuid as _uuid
                    # Concise narration for clearer phonemes / lip sync.
                    narrate = script
                    if len(narrate) > 180:
                        narrate = narrate[:180].rstrip("，。；、 ") + "。"
                    # Prefer Edge Neural (matches 口播 Chinese labels; KIE ElevenLabs flaky).
                    try:
                        wav_bytes, used_voice = await synthesize_speech_edge(
                            narrate, "zh-CN-XiaoxiaoNeural",
                        )
                        url = await KieAdapter().upload_public_url(
                            wav_bytes,
                            filename=f"dir_tts_{_uuid.uuid4().hex[:8]}.wav",
                            content_type="audio/wav",
                        )
                        out = {
                            "type": "audio", "url": url, "media_url": url,
                            "model": f"edge-tts:{used_voice}", "cost": 0,
                            "narration": True, "voice": used_voice,
                            "audio_prep": "loudnorm_-16LUFS",
                        }
                        out = (await asyncio.to_thread(persist_results, [out]))[0]
                        step.status = "done"
                        return out
                    except Exception as edge_err:
                        logger.warning("[director] edge-tts failed (%s) → ElevenLabs", edge_err)
                    last_err: Exception | None = None
                    for voice in ("Rachel", "Adam"):
                        for attempt in range(2):
                            try:
                                res = await KieAdapter().generate_speech(narrate, voice=voice)
                                out = {
                                    "type": "audio", "url": res.media_url,
                                    "media_url": res.media_url, "model": res.model,
                                    "cost": res.cost, "narration": True, "voice": voice,
                                }
                                out = (await asyncio.to_thread(persist_results, [out]))[0]
                                step.status = "done"
                                return out
                            except Exception as e:
                                last_err = e
                                logger.warning(
                                    "[director] tts attempt voice=%s try=%d failed: %s",
                                    voice, attempt + 1, e,
                                )
                                await asyncio.sleep(1.5)
                    raise last_err or RuntimeError("tts failed")
                except Exception as e:
                    logger.warning("[director] tts failed: %s", e)
                    step.status = "failed"
                    return {"type": "audio", "error": f"配音失败: {e}", "ok": False}

            if step.action == "compose":
                # Stitch all upstream shot videos into ONE final film (hero deliverable),
                # muxing the real narration voiceover when available.
                results = getattr(self, "_results", {}) or {}
                shot_urls, narration_url = [], None
                for dep in step.depends_on:
                    r = results.get(dep)
                    if not isinstance(r, dict):
                        continue
                    if r.get("type") == "video":
                        shot_urls.append(r.get("media_url") or r.get("url"))
                    elif r.get("type") == "audio" and (r.get("media_url") or r.get("url")):
                        narration_url = r.get("media_url") or r.get("url")
                shot_urls = [u for u in shot_urls if u]
                if not shot_urls:
                    step.status = "done"
                    return {"type": "compose", "ok": True, "model": step.model_name,
                            "note": "无分镜可合成"}
                subtitle_track: list[dict] = list(getattr(self, "_subtitle_track", None) or [])
                for dep in step.depends_on:
                    r = results.get(dep)
                    if isinstance(r, dict) and r.get("type") == "subtitle":
                        subtitle_track = r.get("subtitle_track") or subtitle_track
                export_preset = _export_preset_from_params(step.params)
                try:
                    from app.adapters.demo_provider import compose_final_video
                    final_url, poster = await asyncio.to_thread(
                        compose_final_video,
                        shot_urls,
                        None,
                        True,
                        narration_url,
                        subtitle_track=subtitle_track,
                        export_preset=export_preset,
                    )
                    step.status = "done"
                    return {
                        "type": "video", "media_url": final_url, "url": final_url,
                        "thumbnail": poster, "model": step.model_name, "cost": 0,
                        "final": True, "shot_count": len(shot_urls),
                        "has_voiceover": bool(narration_url),
                        "subtitle_cues": len(subtitle_track),
                        "export_preset": export_preset,
                    }
                except Exception as e:
                    logger.warning("[director] compose failed: %s", e)
                    step.status = "done"
                    return {"type": "compose", "ok": False, "note": f"合成失败: {e}"}

            if step.action == "lipsync":
                # Talking avatar: drive the avatar image with the narration audio.
                results = getattr(self, "_results", {}) or {}
                img_pub = (step.params or {}).get("image_url")
                aud_pub = None
                img_local = None
                for dep in step.depends_on:
                    r = results.get(dep)
                    if not isinstance(r, dict):
                        continue
                    if r.get("type") == "image":
                        img_pub = img_pub or r.get("source_url") or r.get("media_url")
                        img_local = r.get("media_url") or r.get("url")
                    elif r.get("type") == "audio":
                        aud_pub = r.get("source_url") or r.get("media_url")
                try:
                    from app.adapters.demo_provider import demo_mode_active
                    use_demo_l = self.dry_run or demo_mode_active()
                except Exception:
                    use_demo_l = self.dry_run
                if use_demo_l:
                    # Preview-only: Ken Burns stand-in. Never on real runs.
                    from app.adapters.demo_provider import render_demo_video
                    ls_seed = (step.params or {}).get("seed")
                    v_url, thumb = await asyncio.to_thread(
                        render_demo_video, step.prompt, "720x1280", 5, "portrait", img_local, ls_seed)
                    step.status = "done"
                    return {
                        "type": "video", "media_url": v_url, "url": v_url, "thumbnail": thumb,
                        "model": "demo-lipsync", "planned_model": step.model_id,
                        "mode": "ken_burns", "honesty": "offline_preview_not_lipsync",
                        "cost": 0, "lipsync": False, "lipsync_preview": True,
                    }
                if not (img_pub and aud_pub):
                    # Real path must not silently fake lipsync when upstream failed.
                    step.status = "failed"
                    missing = []
                    if not img_pub:
                        missing.append("人像图")
                    if not aud_pub:
                        missing.append("配音")
                    return {
                        "type": "video",
                        "error": f"唇形同步缺少上游资产：{'、'.join(missing)}（真实生成不会回退 Ken Burns）",
                    }
                try:
                    from app.adapters.kie_adapter import KieAdapter
                    from app.services.media_store import persist_results
                    from app.services.audio_prep import prepare_lipsync_audio_url, boost_video_audio
                    import uuid as _uuid
                    # Loudnorm driving audio before Kling (fixes quiet 口播 + weak mouth drive)
                    try:
                        norm = await asyncio.to_thread(prepare_lipsync_audio_url, aud_pub)
                        aud_pub = await KieAdapter().upload_public_url(
                            norm.read_bytes(),
                            filename=f"dir_ls_norm_{_uuid.uuid4().hex[:8]}.wav",
                            content_type="audio/wav",
                        )
                    except Exception as prep_err:
                        logger.warning("[director] lipsync audio prep skipped: %s", prep_err)
                    ls_prompt = (
                        "close-up talking head, mouth shapes precisely match the speech audio, "
                        "natural jaw and lip motion, clear articulation, keep facial identity"
                    )
                    res = await KieAdapter().generate_lipsync(
                        image_url=img_pub, audio_url=aud_pub, prompt=ls_prompt)
                    final_url = res.media_url
                    try:
                        boosted = await asyncio.to_thread(boost_video_audio, res.media_url)
                        if boosted:
                            final_url = boosted
                    except Exception:
                        pass
                    out = {
                        "type": "video", "url": final_url, "media_url": final_url,
                        "thumbnail": res.thumbnail_url or "", "model": res.model,
                        "cost": res.cost, "lipsync": True, "mode": "kling_avatar",
                        "audio_prep": "loudnorm_-16LUFS",
                    }
                    out = (await asyncio.to_thread(persist_results, [out]))[0]
                    step.status = "done"
                    return out
                except Exception as e:
                    logger.warning("[director] lipsync failed: %s", e)
                    step.status = "failed"
                    return {"type": "video", "error": f"唇形同步失败: {e}"}

            media_type = "video" if step.action in ("video", "lipsync") else "image"
            duration = int((step.params or {}).get("duration", 5) or 5)
            seed = (step.params or {}).get("seed")
            # Image-to-video consistency: a video shot animates its explicit
            # reference image, else the keyframe produced by an image dependency —
            # so every shot shares the same look (跨镜风格一致).
            base_image_url = (step.params or {}).get("image_url")
            if media_type == "video" and not base_image_url:
                results = getattr(self, "_results", {}) or {}
                for dep in step.depends_on:
                    r = results.get(dep)
                    if isinstance(r, dict) and r.get("type") == "image" and (r.get("media_url") or r.get("url")):
                        base_image_url = r.get("media_url") or r.get("url")
                        break

            # Preview (dry_run) or no-key → render viewable local media (Pillow /
            # ffmpeg) for free. Only an explicit real run (dry_run=False) with a
            # configured provider burns credits on the real models below.
            try:
                from app.adapters.demo_provider import demo_mode_active
                use_demo = self.dry_run or demo_mode_active()
            except Exception:
                use_demo = self.dry_run
            if use_demo:
                from app.adapters.demo_provider import render_demo_image, render_demo_video
                styles = _styles_from_brief(step.prompt)
                # Talking-image steps / portrait briefs → portrait stub (not picsum landscape)
                if (
                    step.action == "image"
                    and (
                        _has(step.prompt or "", _TALK_KW)
                        or "数字人" in (step.title or "")
                        or "portrait" in styles
                    )
                ):
                    style = "portrait"
                else:
                    style = styles[0] if styles else "cinematic"
                if media_type == "video":
                    size = _size_from_params(step.params, "1280x720")
                    v_url, thumb = await asyncio.to_thread(
                        render_demo_video, step.prompt, size, min(duration, 6), style, base_image_url, seed)
                    step.status = "done"
                    return {
                        "type": "video", "media_url": v_url, "url": v_url,
                        "thumbnail": thumb, "model": "demo-video",
                        "planned_model": step.model_id, "mode": "ken_burns",
                        "honesty": "offline_preview_not_provider",
                        "cost": 0, "duration": duration, "used_ref": bool(base_image_url),
                    }
                size = _size_from_params(step.params, "1024x1024")
                img_url = await asyncio.to_thread(render_demo_image, step.prompt, size, style, 0, seed)
                step.status = "done"
                return {
                    "type": "image", "media_url": img_url, "url": img_url,
                    "thumbnail": img_url, "model": "demo-image",
                    "planned_model": step.model_id,
                    "mode": "portrait_stub" if style == "portrait" else "stock_or_gradient",
                    "honesty": "offline_preview_not_provider",
                    "cost": 0,
                }

            from app.adapters.registry import get_adapter
            from app.fallback_handler import get_fallback, is_retryable_error
            from app.services.model_health import model_health, validate_generation_results

            async def _call(model_id: str):
                adapter = get_adapter(model_id)
                if adapter is None:
                    raise RuntimeError(f"no adapter for {model_id}")
                if media_type == "video":
                    sp = step.params or {}
                    return await adapter.generate_video(
                        prompt=step.prompt,
                        model_id=model_id,
                        duration=duration,
                        image_url=base_image_url,
                        resolution=_size_from_params(step.params, "1080p"),
                        reference_images=sp.get("reference_images") or None,
                        reference_videos=sp.get("reference_videos") or None,
                        reference_audios=sp.get("reference_audios") or None,
                        omni=bool(sp.get("omni")),
                        generate_audio=bool(sp.get("generate_audio")),
                    )
                generated = await adapter.generate_image(
                    prompt=step.prompt, model_id=model_id,
                    size=_size_from_params(step.params, "1024x1024"), seed=seed)
                return generated[0] if isinstance(generated, list) else generated

            selected_model = step.model_id
            if model_health.is_circuit_open(selected_model) or model_health.is_quarantined(selected_model):
                selected_model = get_fallback(selected_model) or selected_model

            started = time.monotonic()
            try:
                res = await _call(selected_model)
                quality_ok, quality_error = validate_generation_results(res, media_type)
                if not quality_ok:
                    raise RuntimeError(quality_error)
                model_health.record_success(
                    selected_model, int((time.monotonic() - started) * 1000))
            except Exception as primary_error:
                retryable = is_retryable_error(str(primary_error))
                model_health.record_failure(
                    selected_model, str(primary_error), retryable=retryable)
                fallback_id = get_fallback(selected_model) if retryable else None
                if not fallback_id or not model_health.is_routable(fallback_id):
                    raise
                logger.warning(
                    "[director] fallback %s -> %s: %s",
                    selected_model, fallback_id, primary_error)
                fallback_started = time.monotonic()
                try:
                    res = await _call(fallback_id)
                    quality_ok, quality_error = validate_generation_results(res, media_type)
                    if not quality_ok:
                        raise RuntimeError(quality_error)
                    model_health.record_success(
                        fallback_id,
                        int((time.monotonic() - fallback_started) * 1000))
                    selected_model = fallback_id
                except Exception as fallback_error:
                    model_health.record_failure(
                        fallback_id, str(fallback_error),
                        retryable=is_retryable_error(str(fallback_error)))
                    raise RuntimeError(
                        f"primary failed: {primary_error}; "
                        f"fallback {fallback_id} failed: {fallback_error}")

            rd = res.to_dict() if hasattr(res, "to_dict") else (res or {})
            out = {
                "type": media_type,
                "url": rd.get("media_url", ""),
                "media_url": rd.get("media_url", ""),
                "thumbnail": rd.get("thumbnail_url") or rd.get("media_url", ""),
                "model": selected_model,
                "cost": rd.get("cost", step.est_credits),
                "duration": duration if media_type == "video" else None,
            }
            # Localize provider URLs into our storage (persist + video poster) so
            # assets don't expire AND the compose step can stitch local shot files.
            try:
                from app.services.media_store import persist_results
                out = await asyncio.to_thread(persist_results, [out])
                out = out[0] if isinstance(out, list) else out
            except Exception as e:
                logger.warning("[director] persist failed: %s", e)
            step.status = "done"
            return out
        except Exception as e:
            logger.exception("[director] step %s failed", step.id)
            step.status = "failed"
            return {"error": str(e)}

    @staticmethod
    def _asset_from(step: DirectorStep, r: dict) -> dict:
        """Build UI asset. Preview must not display planned provider names as if they ran."""
        mode = r.get("mode") or ""
        honesty = r.get("honesty") or ""
        is_preview = bool(honesty) or mode in (
            "ken_burns", "portrait_stub", "stock_or_gradient",
        ) or str(r.get("model") or "").startswith("demo-")
        base = {k: v for k, v in r.items() if k != "model"}
        if is_preview:
            display = {
                "ken_burns": "本地预览 · Ken Burns（非 Kling）",
                "portrait_stub": "本地预览 · 数字人占位（非 GPT Image）",
                "stock_or_gradient": "本地预览 · 素材图（非真实模型）",
            }.get(mode) or "本地预览（非真实模型）"
            return {
                **base,
                "step_id": step.id,
                "step": step.title,
                "shot": (step.params or {}).get("shot"),
                "model": display,
                "planned_model": r.get("planned_model") or step.model_id,
                "planned_model_name": step.model_name,
                "mode": mode or "demo_preview",
                "honesty": honesty or "offline_preview_not_provider",
            }
        return {
            **base,
            "step_id": step.id,
            "step": step.title,
            "model": step.model_name,
            "shot": (step.params or {}).get("shot"),
        }

    async def run(self, plan: DirectorPlan) -> dict:
        """按 depends_on 拓扑顺序执行，无依赖关系的同层并行 (非流式)。"""
        assets: list[dict] = []
        async for ev in self.run_stream(plan):
            if ev["type"] == "step_done" and ev.get("asset"):
                assets.append(ev["asset"])
        return {"plan": plan.to_dict(), "assets": assets,
                "asset_count": len(assets), "dry_run": self.dry_run}

    async def run_stream(self, plan: DirectorPlan):
        """流式执行：逐步 yield 事件，让前端实时呈现导演推进过程。

        事件: step_start | step_done | step_error | complete
        依赖满足即执行；同层并行，完成一个推一个 (as_completed)。
        跳过(skip)的步骤视为已满足依赖但不产出。
        """
        done: dict[str, dict] = {}
        self._results = done  # expose to _run_step (compose gathers upstream shots)
        assets: list[dict] = []
        remaining = list(plan.steps)
        guard = 0
        t_start = time.monotonic()
        # Real video providers (KIE) queue concurrent shots on limited GPUs, so
        # firing all shots at once stalls them all in 'waiting'. Serialize real
        # video generation (1 at a time) so each shot gets a GPU slot in turn.
        # Demo renders are fast/local → keep them parallel.
        # Real video providers queue concurrent shots on limited GPUs.
        # DIRECTOR_VIDEO_CONCURRENCY (default 2) raises throughput vs serial-1
        # while staying below provider saturation; demo stays highly parallel.
        import os as _os
        try:
            real_conc = max(1, min(8, int(_os.getenv("DIRECTOR_VIDEO_CONCURRENCY", "2"))))
        except ValueError:
            real_conc = 2
        vid_sem = asyncio.Semaphore(8 if self.dry_run else real_conc)

        # 预处理：跳过步骤直接标记完成 (满足依赖)
        for s in remaining:
            if s.skip:
                s.status = "skipped"
                done[s.id] = {"skipped": True}

        while True:
            guard += 1
            if guard > 200:
                break
            pending = [s for s in remaining if s.id not in done]
            if not pending:
                break
            ready = [s for s in pending if all(d in done for d in s.depends_on)]
            if not ready:
                # 依赖无法满足 (循环/缺失) → 标记跳过并结束
                for s in pending:
                    s.status = "skipped"
                    yield {"type": "step_error", "id": s.id, "error": "依赖未满足，已跳过"}
                break

            for s in ready:
                s.status = "running"
                yield {"type": "step_start", "id": s.id, "title": s.title,
                       "action": s.action, "model_name": s.model_name}

            # 并行执行本层，完成一个推一个 (协程返回 (step, result, 耗时) 以便映射与计时)
            async def _exec(step: DirectorStep):
                t0 = time.monotonic()
                if step.action in ("video", "lipsync"):
                    async with vid_sem:  # throttle real video to respect provider GPU queue
                        r = await self._run_step(step)
                else:
                    r = await self._run_step(step)
                return step, r, int((time.monotonic() - t0) * 1000)

            tasks = [asyncio.ensure_future(_exec(s)) for s in ready]
            for fut in asyncio.as_completed(tasks):
                s, r, elapsed_ms = await fut
                s.result = r
                done[s.id] = r
                if "error" in r:
                    yield {"type": "step_error", "id": s.id, "error": r["error"], "elapsed_ms": elapsed_ms}
                    continue
                asset = None
                if s.action in ("image", "video", "lipsync") or (s.action == "compose" and r.get("type") == "video"):
                    asset = self._asset_from(s, r)
                    assets.append(asset)
                yield {"type": "step_done", "id": s.id, "step": s.to_dict(),
                       "asset": asset, "elapsed_ms": elapsed_ms}

        yield {"type": "complete", "asset_count": len(assets), "assets": assets,
               "dry_run": self.dry_run, "plan": plan.to_dict(),
               "total_ms": int((time.monotonic() - t_start) * 1000)}

    async def run_single(self, step: DirectorStep) -> dict:
        """重新执行单个步骤 (用于 per-step 重生成)。"""
        r = await self._run_step(step)
        asset = None
        if s_ok := ("error" not in r):
            if step.action in ("image", "video", "lipsync"):
                asset = self._asset_from(step, r)
        return {"ok": s_ok, "step": step.to_dict(), "asset": asset, "result": r}


def build_storyboard_plan(
    shots: list[dict],
    *,
    brief: str = "",
    ref_image_url: str | None = None,
    reference_images: list[str] | None = None,
    reference_videos: list[str] | None = None,
    reference_audios: list[str] | None = None,
    omni: bool = False,
    generate_audio: bool = False,
    with_compose: bool = True,
) -> DirectorPlan:
    """Build a *true* multi-shot Director plan from explicit shot prompts.

    Unlike Create-Video UI prompt-stitching, each shot becomes a real ``video``
    step with its own prompt/duration, optional shared Omni refs, and an
    optional compose step — executed by DirectorExecutor.
    """
    if not shots:
        raise ValueError("shots required")
    shots = shots[:8]
    brief = (brief or "多镜头分镜创作").strip()
    ref_images = [u for u in (reference_images or []) if u][:9]
    if ref_image_url and ref_image_url not in ref_images:
        ref_images = [ref_image_url] + ref_images
    ref_videos = [u for u in (reference_videos or []) if u][:3]
    ref_audios = [u for u in (reference_audios or []) if u][:3]
    use_omni = bool(omni) or bool(ref_videos or ref_audios or len(ref_images) > 1)
    # Omni → prefer Seedance; otherwise balanced video pick
    if use_omni:
        catalog = _catalog()
        vid = next((m for m in catalog if m["id"] == "seedance-2.0"), None)
        if not vid:
            vid = _pick_model("video", [], "balanced")
            vid = {**vid, "id": "seedance-2.0", "display_name": "Seedance 2.0"}
    else:
        vid = _pick_model("video", [], "balanced")
    steps: list[DirectorStep] = []
    shot_ids: list[str] = []
    prev: str | None = None
    for i, raw in enumerate(shots):
        prompt = (raw.get("prompt") or "").strip()
        if not prompt:
            raise ValueError(f"shot {i + 1} missing prompt")
        duration = int(raw.get("duration") or 5)
        duration = max(1, min(duration, 15))
        label = (raw.get("label") or f"分镜 {i + 1}/{len(shots)}").strip()
        sid = uuid.uuid4().hex[:8]
        params: dict = {
            "aspect_ratio": "16:9",
            "duration": duration,
            "shot": i + 1,
            "storyboard": True,
        }
        primary = ref_images[0] if ref_images else ref_image_url
        if primary:
            params["image_url"] = primary
        if ref_images:
            params["reference_images"] = list(ref_images)
        if ref_videos:
            params["reference_videos"] = list(ref_videos)
        if ref_audios:
            params["reference_audios"] = list(ref_audios)
        if use_omni:
            params["omni"] = True
        if generate_audio or ref_audios:
            params["generate_audio"] = True
        step = DirectorStep(
            id=sid,
            action="video",
            title=label,
            model_id=vid["id"],
            model_name=vid["display_name"],
            reason=(
                f"显式分镜 {i + 1}：独立 prompt/时长"
                + (" · Omni 多模态参考" if use_omni else "")
                + "，非提示词拼接"
            ),
            prompt=prompt,
            depends_on=[prev] if prev else [],
            est_credits=_credits_of(vid, "video", duration),
            params=params,
        )
        steps.append(step)
        shot_ids.append(sid)
        prev = sid

    if with_compose and len(shot_ids) >= 1:
        s_comp = DirectorStep(
            id=uuid.uuid4().hex[:8],
            action="compose",
            title="剪辑合成成片",
            model_id="compose-engine",
            model_name="FFmpeg Compose",
            reason=f"将 {len(shot_ids)} 个真实分镜合成为成片",
            prompt=brief,
            depends_on=list(shot_ids),
            est_credits=0,
            params={"storyboard": True},
        )
        steps.append(s_comp)

    total = sum(s.est_credits for s in steps)
    summary = (
        f"真分镜计划：{len(shot_ids)} 个独立视频步骤"
        f"{' + 合成' if with_compose else ''}，预计 {total} 积分"
    )
    return DirectorPlan(
        brief=brief,
        intent="storyboard",
        summary=summary,
        steps=steps,
        total_credits=total,
    )


planner = DirectorPlanner()
