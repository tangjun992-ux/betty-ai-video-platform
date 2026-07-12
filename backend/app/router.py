"""
Smart Prompt Router — two-stage model selection engine.

Stage 1: Semantic analysis — extract prompt features (type, style, complexity, mood)
Stage 2: Rule-based scoring — match prompt features against model capabilities
"""
import re
import logging
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum
from app.services.model_health import model_health

logger = logging.getLogger(__name__)


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUTO = "auto"


class QualityTier(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    HIGH = "high"


@dataclass
class PromptAnalysis:
    """Structured analysis of a user prompt."""
    media_type: MediaType = MediaType.AUTO
    quality: QualityTier = QualityTier.BALANCED
    styles: list[str] = field(default_factory=list)
    complexity: str = "medium"  # simple | medium | complex
    mood: str = ""
    key_subjects: list[str] = field(default_factory=list)
    language: str = "zh"  # estimated language
    has_reference_image: bool = False
    score_rationale: str = ""


# ─── Style keyword database ───

VIDEO_KEYWORDS = [
    "视频", "video", "动画", "动效", "短片", "clip", "movie", "电影",
    "motion", "move", "旋转", "zoom", "推进", "拉远", "pan", "镜头",
    "trailer", "预告", "动态", "fly", "slow-mo", "timelapse",
]

IMAGE_KEYWORDS = [
    "图片", "image", "photo", "照片", "绘画", "画", "poster", "海报",
    "插画", "illustration", "icon", "图标", "壁纸", "wallpaper",
]

HIGH_Q_KEYWORDS = [
    "4k", "8k", "高清", "高质量", "fine", "电影级", "cinematic",
    "专业", "大片", "masterpiece", "photorealistic", "超高清",
    "HDR", "UHD", "商业级", "commercial", "广告", "premium",
]

FAST_Q_KEYWORDS = [
    "快速", "quick", "fast", "秒出", "简单", "草稿", "draft", "草图",
    "sketch", "随便", "简单", "预览", "preview",
]

# Style patterns per model
STYLE_SCENES = {
    "realistic": [
        "写实", "真实", "photorealistic", "照片级", "逼真", "摄影",
        "实景", "realistic", "real life", "真人", "实拍", "纪录片",
    ],
    "cinematic": [
        "电影", "cinematic", "大片", "震撼", "光影", "trailer",
        "预告", "hollywood", "dramatic", "史诗", "宽屏",
    ],
    "anime": [
        "动漫", "anime", "二次元", "日系", "卡通", "manga",
        "宫崎", "新海", "赛博朋克", "赛博", "cyberpunk",
    ],
    "product": [
        "产品", "product", "电商", "商品", "展示", "commercial",
        "广告片", "棚拍", "影棚", "white background", "白底",
    ],
    "landscape": [
        "风景", "landscape", "自然", "山水", "日出", "日落",
        "sunset", "sunrise", "山脉", "mountain", "ocean", "海洋",
        "星空", "starry", "极光", "aurora", "草原", "forest", "森林",
    ],
    "portrait": [
        "人像", "portrait", "自拍", "人物", "people", "face", "脸部",
        "角色", "character", "模特", "model", "美女",
    ],
    "artistic": [
        "油画", "watercolor", "水墨", "sketch", "素描", "art",
        "艺术", "抽象", "abstract", "手绘", "hand-drawn",
        "impressionist", "印象派", "surreal", "超现实",
    ],
    "sci-fi": [
        "科幻", "sci-fi", "futuristic", "未来", "太空", "space",
        "外星", "alien", "赛博", "cyberpunk", "太空站", "机器人",
        "robot", "AI", "全息", "holographic",
    ],
    "architecture": [
        "建筑", "architecture", "室内设计", "房间", "house", "别墅",
        "villa", "现代", "minimal", "极简", "loft", "apartment",
    ],
    "food": [
        "食物", "food", "美食", "甜品", "cake", "coffee", "咖啡",
        "restaurant", "餐厅", "饮料", "drink", "水果",
    ],
    "fantasy": [
        "奇幻", "fantasy", "魔法", "magic", "精灵", "dragon",
        "dragon", "城堡", "castle", "中世纪", "medieval",
        "仙侠", "修仙", "神话", "mythology", "god", "神",
    ],
    "cute/kawaii": [
        "可爱", "cute", "kawaii", "萌", "Q版", "chibi", "小动物",
        "pet", "猫咪", "cat", "猫咪", "dog", "dog", "puppy",
        "兔子", "rabbit", "bunny",
    ],
}

# ─── Model routing matrix ───

@dataclass
class ModelScore:
    model_id: str
    score: float
    reasons: list[str] = field(default_factory=list)
    recommended_media_type: MediaType = MediaType.AUTO
    is_fallback: bool = False


# Model preference order per style
MODEL_STYLE_PREFS = {
    "video": {
        "seedance-2.0": {
            "priority": 1,
            "boost_styles": ["cinematic", "dramatic", "documentary", "commercial", "realistic", "landscape"],
            "max_duration": 15,
            "strengths": ["电影级画质", "流畅自然", "Seedance 2.0 旗舰"],
            "cost_credits_per_5s": 4,
            "avg_latency_s": 90,
        },
        "seedance-2.0-fast": {
            "priority": 2,
            "boost_styles": ["realistic", "landscape", "portrait", "product", "anime", "fantasy", "sci-fi", "food", "cute/kawaii"],
            "max_duration": 10,
            "strengths": ["快速生成", "图像转视频", "流畅自然", "性价比高"],
            "cost_credits_per_5s": 3,
            "avg_latency_s": 30,
        },
    },
    "image": {
        "gpt-image-2": {
            "priority": 1,
            "boost_styles": ["product", "artistic", "architecture", "food", "realistic", "portrait"],
            "strengths": ["细节处理最优", "文字渲染准确", "构图能力强", "高质量需求"],
            "cost_credits": 5,
            "avg_latency_s": 15,
        },
        "nano-banana": {
            "priority": 2,
            "boost_styles": ["anime", "fantasy", "sci-fi", "landscape", "cute/kawaii", "realistic", "portrait"],
            "strengths": ["写实风格优秀", "人物生成强", "速度快"],
            "cost_credits": 2,
            "avg_latency_s": 8,
        },
    },
}


class PromptRouter:
    """Two-stage prompt router for optimal model selection."""

    def __init__(self):
        self._style_cache = {}

    def analyze(self, prompt: str, media_type_hint: str = "auto",
                quality_hint: str = "balanced") -> PromptAnalysis:
        """Stage 1: Extract semantic features from prompt."""
        analysis = PromptAnalysis()
        prompt_lower = prompt.lower()

        # Language detection (simple)
        has_chinese = any('一' <= c <= '鿿' for c in prompt)
        has_english = any('a' <= c <= 'z' for c in prompt_lower)
        if has_chinese:
            analysis.language = "zh"
        elif has_english:
            analysis.language = "en"

        # Media type detection
        video_count = sum(1 for kw in VIDEO_KEYWORDS if kw in prompt_lower)
        image_count = sum(1 for kw in IMAGE_KEYWORDS if kw in prompt_lower)

        if media_type_hint == "video" or (video_count > 0 and video_count >= image_count):
            analysis.media_type = MediaType.VIDEO
        elif media_type_hint == "image" or (image_count > 0 and image_count > video_count):
            analysis.media_type = MediaType.IMAGE
        else:
            analysis.media_type = MediaType.AUTO

        # Quality detection
        hq_count = sum(1 for kw in HIGH_Q_KEYWORDS if kw in prompt_lower)
        fq_count = sum(1 for kw in FAST_Q_KEYWORDS if kw in prompt_lower)

        if quality_hint == "high" or hq_count > fq_count:
            analysis.quality = QualityTier.HIGH
        elif quality_hint == "fast" or fq_count > hq_count:
            analysis.quality = QualityTier.FAST
        else:
            analysis.quality = QualityTier.BALANCED

        # Style extraction
        styles = []
        for style_name, keywords in STYLE_SCENES.items():
            if any(kw in prompt_lower for kw in keywords):
                styles.append(style_name)
        analysis.styles = styles

        # Complexity estimation
        words = prompt_lower.split()
        char_count = len(prompt)
        if char_count < 20 or len(words) < 5:
            analysis.complexity = "simple"
        elif char_count > 80 or len(words) > 20:
            analysis.complexity = "complex"
        else:
            analysis.complexity = "medium"

        # Mood estimation (simplified)
        mood_keywords = {
            "warm": ["温暖", "warm", "日出", "sunrise", "日落", "sunset", "金色"],
            "cool": ["冷", "cool", "蓝", "blue", "night", "夜", "月光", "moon"],
            "dramatic": ["震撼", "dramatic", "史诗", "storm", "风暴", "dark", "黑暗"],
            "peaceful": ["宁静", "peaceful", "安静", "安静", "serene", "禅意"],
            "energetic": ["活力", "energetic", "动感", "action", "爆炸", "explosion"],
        }
        for mood, kws in mood_keywords.items():
            if any(kw in prompt_lower for kw in kws):
                analysis.mood = mood
                break

        # Key subjects extraction (nouns and important entities)
        analysis.key_subjects = self._extract_subjects(prompt_lower)

        return analysis

    def select_model(self, analysis: PromptAnalysis,
                     user_model: str = "auto") -> ModelScore:
        """Stage 2: Score models and select the best one."""
        if user_model != "auto":
            return ModelScore(
                model_id=user_model,
                score=100.0,
                reasons=[f"用户指定模型: {user_model}"],
                recommended_media_type=analysis.media_type,
            )

        # Determine target media type
        if analysis.media_type == MediaType.AUTO:
            target_media = "video" if analysis.complexity in ("medium", "complex") else "image"
        else:
            target_media = analysis.media_type.value

        models = MODEL_STYLE_PREFS.get(target_media, {})
        scores = []

        for model_id, pref in models.items():
            if model_health.is_circuit_open(model_id):
                logger.warning("Router skipped open circuit model: %s", model_id)
                continue
            model_score = 50.0  # base score
            reasons = []

            # Style match bonus
            style_bonus = 0
            for s in analysis.styles:
                if s in pref.get("boost_styles", []):
                    style_bonus += 15
                    reasons.append(f"风格匹配: {s}")

            # Quality alignment
            if analysis.quality == QualityTier.HIGH:
                if pref["priority"] == 1:
                    model_score += 20
                    reasons.append("高质量偏好")
            elif analysis.quality == QualityTier.FAST:
                if "fast" in model_id.lower() or pref.get("avg_latency_s", 999) < 20:
                    model_score += 15
                    reasons.append("速度偏好")

            # Complexity adjustment
            if analysis.complexity == "complex" and "kling" in model_id:
                model_score += 10
                reasons.append("复杂场景适合 Kling")

            # Cost efficiency (small bonus for cheaper models if quality not high)
            if analysis.quality != QualityTier.HIGH:
                cost = pref.get("cost_credits", pref.get("cost_credits_per_5s", 99))
                if cost <= 3:
                    model_score += 5
                    reasons.append("性价比高")

            model_score += style_bonus

            # Live reliability feeds back into routing. Healthy/unseen models are
            # neutral; degraded models receive up to a 30-point penalty.
            health_score = model_health.score(model_id)
            health_penalty = max(0.0, (100.0 - health_score) * 0.30)
            model_score -= health_penalty
            if health_penalty:
                reasons.append(f"实时健康 {health_score:.0f}/100")

            scores.append(ModelScore(
                model_id=model_id,
                score=round(model_score, 1),
                reasons=reasons if reasons else ["默认选择"],
                recommended_media_type=MediaType(target_media),
            ))

        # A transient outage must not make routing impossible: if all circuits
        # are open, retain the static candidates and let runtime fallback decide.
        if not scores:
            for model_id in models:
                scores.append(ModelScore(
                    model_id=model_id, score=1.0,
                    reasons=["所有候选模型暂时降级，尝试恢复探测"],
                    recommended_media_type=MediaType(target_media),
                ))

        # Sort by score descending
        scores.sort(key=lambda s: s.score, reverse=True)

        best = scores[0]
        if len(scores) > 1:
            best.is_fallback_model = scores[1].model_id  # attach fallback

        return best

    def get_all_model_scores(self, analysis: PromptAnalysis) -> list[ModelScore]:
        """Get scores for all available models (for UI display)."""
        if analysis.media_type == MediaType.VIDEO:
            media = "video"
        elif analysis.media_type == MediaType.IMAGE:
            media = "image"
        else:
            # Return both image and video scores for auto
            all_scores = []
            for m in ["video", "image"]:
                for model_id, pref in MODEL_STYLE_PREFS.get(m, {}).items():
                    score = self._score_single(model_id, pref, analysis, m)
                    all_scores.append(score)
            all_scores.sort(key=lambda s: s.score, reverse=True)
            return all_scores

        all_scores = []
        for model_id, pref in MODEL_STYLE_PREFS.get(media, {}).items():
            score = self._score_single(model_id, pref, analysis, media)
            all_scores.append(score)
        all_scores.sort(key=lambda s: s.score, reverse=True)
        return all_scores

    def _score_single(self, model_id: str, pref: dict,
                      analysis: PromptAnalysis, target_media: str) -> ModelScore:
        score = 50.0
        reasons = []

        style_bonus = 0
        for s in analysis.styles:
            if s in pref.get("boost_styles", []):
                style_bonus += 15
                reasons.append(f"风格匹配: {s}")

        if analysis.quality == QualityTier.HIGH and pref["priority"] == 1:
            score += 20
            reasons.append("高质量偏好")

        if analysis.complexity == "complex" and "kling" in model_id:
            score += 10
            reasons.append("复杂场景适合")

        if analysis.quality != QualityTier.HIGH:
            cost = pref.get("cost_credits", pref.get("cost_credits_per_5s", 99))
            if cost <= 3:
                score += 5
                reasons.append("性价比高")

        score += style_bonus

        return ModelScore(
            model_id=model_id,
            score=round(score, 1),
            reasons=reasons if reasons else ["通用选择"],
            recommended_media_type=MediaType(target_media),
        )

    def _extract_subjects(self, prompt_lower: str) -> list[str]:
        """Extract key subjects/entities from prompt."""
        subjects = []
        # Common subject patterns in Chinese
        patterns = [
            r'([一-龥]{1,4})(?:在|有|是一只|画着|拍摄|展示)',
            r'一只?([一-龥]{1,3})',
            r'一个?([一-龥]{1,4})',
            r'([一-龥]{2,6})(?:风格|场景|画面)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, prompt_lower)
            subjects.extend(matches)

        # Also check for English nouns (simple heuristic)
        en_subjects = re.findall(r'([a-z]{3,15})', prompt_lower)
        for s in en_subjects:
            if s not in ('the', 'and', 'with', 'for', 'from', 'this', 'that', 'what', 'which', 'style', 'scene'):
                subjects.append(s)

        # Deduplicate and limit
        seen = set()
        result = []
        for s in subjects:
            if s not in seen and len(s) > 1:
                seen.add(s)
                result.append(s)
        return result[:5]


# Singleton instance
router = PromptRouter()
