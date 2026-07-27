"""投放向 brief 模板库 — 钩子句式 / 时长 / CTA（口播 & UGC & 广告）。

对标 Creatify/Arcads「选模板开拍」：降低空白输入，默认就具备可试投结构。
"""
from __future__ import annotations

from typing import Any

# id must be stable for FE chips
BRIEF_TEMPLATES: list[dict[str, Any]] = [
    # ── product_ad ──────────────────────────────────────────────
    {
        "id": "ad_pain_hook",
        "scenario": "product_ad",
        "label": "痛点钩子 · 15s",
        "placement": "meta_feed",
        "duration": 15,
        "cta": "了解更多 · 立即选购",
        "hook": "痛点钩子",
        "brief": (
            "15秒产品广告：前3秒用痛点钩子抓住停留，中间展示核心卖点与产品特写，"
            "结尾强CTA引导点击。电影级布光，主体稳定，适合Meta信息流投放测试"
        ),
    },
    {
        "id": "ad_benefit_hook",
        "scenario": "product_ad",
        "label": "利益钩子 · 15s",
        "placement": "meta_feed",
        "duration": 15,
        "cta": "限时优惠 · 马上行动",
        "hook": "利益钩子",
        "brief": (
            "15秒高转化广告：开场直接承诺结果利益，中段用前后对比强化效果，"
            "收束品牌露出与购买理由，适合快速A/B试投"
        ),
    },
    {
        "id": "ad_stories_vertical",
        "scenario": "product_ad",
        "label": "Stories 竖版 · 15s",
        "placement": "meta_stories",
        "duration": 15,
        "cta": "滑动查看 · 立即选购",
        "hook": "场景钩子",
        "brief": (
            "竖屏9:16 Stories广告：生活场景开场，产品自然入镜，大字幕卖点，"
            "结尾滑动CTA，节奏紧凑适合Instagram/Facebook Stories"
        ),
    },
    # ── ugc ─────────────────────────────────────────────────────
    {
        "id": "ugc_selfie_rec",
        "scenario": "ugc",
        "label": "自拍安利 · 15s",
        "placement": "tiktok",
        "duration": 15,
        "cta": "同款安利 · 评论区见",
        "hook": "社交钩子",
        "brief": (
            "竖屏UGC种草：手机自拍开场对镜头说话，手持产品真实展示，口语化推荐，"
            "自然手持晃动，适合TikTok/抖音信息流原生投放"
        ),
    },
    {
        "id": "ugc_before_after",
        "scenario": "ugc",
        "label": "前后对比 · 20s",
        "placement": "tiktok",
        "duration": 20,
        "cta": "同款链接 · 主页自取",
        "hook": "反差钩子",
        "brief": (
            "竖屏UGC：用前后对比制造反差钩子，创作者真实使用产品，卧室自然光，"
            "口语节奏，结尾引导主页链接，避免影院建立镜头"
        ),
    },
    {
        "id": "ugc_reels_hype",
        "scenario": "ugc",
        "label": "Reels 种草 · 15s",
        "placement": "reels",
        "duration": 15,
        "cta": "点击主页 · 同款链接",
        "hook": "利益钩子",
        "brief": (
            "Instagram Reels竖屏种草：前2秒强利益承诺，中段快速演示用法，"
            "花字字幕吸睛，结尾主页CTA，原生创作者气质"
        ),
    },
    # ── talking_avatar ──────────────────────────────────────────
    {
        "id": "talk_product_pitch",
        "scenario": "talking_avatar",
        "label": "卖点口播 · 15s",
        "placement": "tiktok",
        "duration": 15,
        "cta": "关注了解更多",
        "hook": "利益钩子",
        "brief": (
            "竖屏数字人口播：正面特写女主播，讲解产品三大卖点与使用场景，"
            "自然口型，清晰发音，棚拍柔光，结尾关注引导，可直接社媒试投"
        ),
    },
    {
        "id": "talk_faq",
        "scenario": "talking_avatar",
        "label": "问答口播 · 20s",
        "placement": "reels",
        "duration": 20,
        "cta": "评论区扣1 · 领取同款",
        "hook": "痛点钩子",
        "brief": (
            "竖屏口播：主播用问答形式解答用户对产品的三大疑虑，正面头肩特写，"
            "语速适中便于口型，字幕清晰，适合Reels/短视频答疑投放"
        ),
    },
    {
        "id": "talk_unbox",
        "scenario": "talking_avatar",
        "label": "开箱讲解 · 15s",
        "placement": "tiktok",
        "duration": 15,
        "cta": "同款安利 · 主页链接",
        "hook": "场景钩子",
        "brief": (
            "竖屏数字人开箱讲解：开场展示包装惊喜，中段讲解材质与功能，"
            "特写口型同步，亲和语气，适合电商种草口播"
        ),
    },
]


def list_brief_templates(scenario: str | None = None) -> list[dict[str, Any]]:
    sc = (scenario or "").strip().lower()
    if not sc:
        return [dict(t) for t in BRIEF_TEMPLATES]
    return [dict(t) for t in BRIEF_TEMPLATES if t["scenario"] == sc]


def get_brief_template(template_id: str) -> dict[str, Any] | None:
    tid = (template_id or "").strip()
    for t in BRIEF_TEMPLATES:
        if t["id"] == tid:
            return dict(t)
    return None
