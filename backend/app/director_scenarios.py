"""Director scenario specs — 8 Agent cards mapped to top-tier benchmark pipelines.

Cards (UI order on /agent):
  product_ad | product_commercial | ugc | micro_drama | anime |
  product_photo | ai_portrait | talking_avatar

Each scenario owns shot vocabulary, aspect, model bias, and finish ladder so
keyword-only routing cannot collapse UGC into cinematic ads or AI 写真 into
product-angle series.
"""
from __future__ import annotations

# Stable IDs — must match frontend SCENARIOS[].id
SCENARIO_IDS = (
    "product_ad",
    "product_commercial",
    "ugc",
    "micro_drama",
    "anime",
    "product_photo",
    "ai_portrait",
    "talking_avatar",
)

# ── 对标参照（验收时对照，不是声称已对等）──────────────────────────────
BENCHMARKS: dict[str, dict] = {
    "product_ad": {
        "peers": ["Meta Advantage+ creatives", "Pika / Runway product ads", "Pencil"],
        "must": [
            "单条可投放成片（多镜合成，非散落分镜）",
            "前 3 秒钩子清晰、卖点可读",
            "商业级产品质感与稳定主体",
            "响度接近社媒投放习惯（有配音时）",
        ],
    },
    "product_commercial": {
        "peers": ["Runway Gen-3 brand films", "Kling Master demos", "Luma Dream Machine"],
        "must": [
            "多镜叙事（建立→细节→动态→收束）",
            "电影级布光与运镜连贯",
            "品牌高级感，非 UGC 手持感",
            "合成后成片可发布",
        ],
    },
    "ugc": {
        "peers": ["Arcads", "Creatify UGC", "TikTok creative center native ads"],
        "must": [
            "竖屏 9:16，原生信息流节奏",
            "手持/自拍感，避免影院建立镜头",
            "产品出镜自然（手持/使用），口语推荐感",
            "多镜合成一条短视频",
        ],
    },
    "micro_drama": {
        "peers": ["ShortMax / DramaBox pacing", "CapCut AI story", "Runway narrative shorts"],
        "must": [
            "竖屏，钩子开场 + 冲突/反转节拍",
            "人物情绪可读，非纯空镜产品片",
            "至少多镜叙事（非单镜 5 秒敷衍）",
            "合成成片",
        ],
    },
    "anime": {
        "peers": ["Runway anime motion", "Luma stylized", "Pika anime"],
        "must": [
            "明确二次元/新海诚式光影，非写实真人",
            "角色与场景风格统一",
            "运动连贯、氛围优先",
        ],
    },
    "product_photo": {
        "peers": ["Photoroom", "Claid", "Pebblely", "Flair.ai"],
        "must": [
            "影棚布光、商业反光与材质可读",
            "多角度套图风格一致",
            "主体居中、背景干净",
        ],
    },
    "ai_portrait": {
        "peers": ["Aragon / HeadshotPro", "Remini portrait", "Astria headshots"],
        "must": [
            "职业形象照构图（头肩/胸像），非产品三视图",
            "正装/柔光/自然表情",
            "多姿态统一身份与色调",
            "适合领英/简历裁切",
        ],
    },
    "talking_avatar": {
        "peers": ["HeyGen", "Hedra", "D-ID", "Synthesia"],
        "must": [
            "竖屏口播，驱动音清晰（约 -16 LUFS）",
            "口型与语音基本同步（非纯 Ken Burns）",
            "正面人像身份稳定",
            "成片可直接社媒试投放",
        ],
    },
}

# 产品广告：投放钩子节奏（对标 Meta/短视频广告前 3s）
AD_BEATS = [
    ("3秒钩子", "强视觉开场抓住停留，产品或痛点瞬间可读",
     "bold hook in first seconds, product or pain-point instantly readable, social ad pacing"),
    ("卖点特写", "材质/功能特写证明品质",
     "macro product detail proving quality, crisp commercial lighting"),
    ("转化收束", "使用场景或 CTA 氛围收尾，适合投放",
     "lifestyle usage or CTA-ready closing beat, polished ad finish"),
]

# 品牌商业片：电影级叙事
COMMERCIAL_BEATS = [
    ("建立镜头", "大远景交代品牌世界与氛围，缓慢推进",
     "wide cinematic establishing shot, slow push-in, luxury brand world"),
    ("主体特写", "英雄产品特写，浅景深与精致反光",
     "hero product close-up, shallow depth of field, exquisite reflections"),
    ("动态运镜", "流畅跟拍展示形态与使用动势",
     "smooth tracking shot revealing form and motion"),
    ("情绪高潮", "戏剧光影与构图张力",
     "dramatic lighting peak, high-end campaign tension"),
    ("氛围点缀", "材质/环境空镜丰富层次",
     "atmospheric insert, tactile material details"),
    ("品牌收束", "拉远留白，标志性余韵",
     "pull-back brand closing shot, breathing room"),
]

# UGC：原生创作者节奏（绝不用影院建立镜头）
UGC_BEATS = [
    ("自拍开场", "手持竖屏自拍开场，对镜头说话感",
     "handheld vertical selfie opening, talking-to-camera native feel, slight natural shake"),
    ("展示种草", "中近景手持产品真实展示，生活场景",
     "medium close-up authentic product demo in hand, real-life setting, UGC lighting"),
    ("口语安利", "自然推荐收尾，信息流节奏",
     "casual recommendation close, vertical social feed pacing, genuine creator energy"),
]

# 微短剧：钩子→冲突→反转
DRAMA_BEATS = [
    ("强钩子", "开场 2 秒抓住好奇，人物表情或反差情境",
     "cold open hook in two seconds, expressive face or situational irony, vertical drama"),
    ("冲突升温", "关系/选择压力上升，情绪张力",
     "rising conflict, emotional tension between characters, cinematic vertical framing"),
    ("反转落点", "信息反转或决定时刻",
     "twist reveal or decision moment, sharp emotional turn"),
    ("余韵收束", "短暂停顿留悬念，可追更感",
     "brief lingering close, cliffhanger energy for episode follow"),
]

PRODUCT_PHOTO_VARIATIONS = [
    ("正面主视觉", "centered hero angle, softbox key light, clean seamless backdrop, commercial catalog"),
    ("侧面 45°", "three-quarter product angle, controlled specular highlights, premium material read"),
    ("材质特写", "macro material/texture detail, razor focus, studio reflection control"),
    ("场景置景", "styled lifestyle set still keeping product hero, cohesive color grade"),
]

# AI 写真：职业头像套图（对标 HeadshotPro）— 绝不能用产品三视图
PORTRAIT_VARIATIONS = [
    ("正面职业头像", "professional LinkedIn headshot, eyes to camera, soft beauty-dish key, neutral seamless, sharp eyes"),
    ("四分之三侧脸", "three-quarter portrait, natural micro-expression, consistent wardrobe and identity"),
    ("自然微笑胸像", "chest-up corporate portrait, gentle smile, flattering Rembrandt-soft light"),
    ("名片裁切感", "tight head-and-shoulders crop ready for resume/avatar, clean background, skin texture real"),
]


def infer_scenario(brief: str) -> str:
    """Best-effort scenario inference when client omits scenario id."""
    b = (brief or "").lower()

    def has(*kws: str) -> bool:
        return any(k.lower() in b for k in kws)

    if has("口播", "数字人", "talking", "唇形", "主播讲解"):
        return "talking_avatar"
    if has("ugc", "种草"):
        return "ugc"
    if has("微短剧", "短剧"):
        return "micro_drama"
    if has("动漫", "二次元", "新海诚", "anime"):
        return "anime"
    if has("写真", "形象照", "领英", "头像", "简历照"):
        return "ai_portrait"
    if has("产品摄影", "产品图", "影棚级产品"):
        return "product_photo"
    if has("商业片", "宣传片", "品牌大片", "campaign film"):
        return "product_commercial"
    if has("产品广告", "投放广告", "高转化") or (has("广告") and has("产品")):
        return "product_ad"
    return ""


def scenario_vertical(scenario: str) -> bool:
    return scenario in ("ugc", "micro_drama", "talking_avatar", "ai_portrait")


def scenario_intent(scenario: str) -> str:
    return {
        "product_ad": "campaign",
        "product_commercial": "campaign",
        "ugc": "campaign",
        "micro_drama": "video_from_text",
        "anime": "video_from_text",
        "product_photo": "image_series",
        "ai_portrait": "image_series",
        "talking_avatar": "talking",
    }.get(scenario, "")
