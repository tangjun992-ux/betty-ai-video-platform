"""
Prompt Enhancer — optimizes user prompts for better AI generation results.

Works by:
1. Detecting the prompt language and style
2. Adding style modifiers, camera terms, lighting cues
3. Preserving user intent while improving generation quality
"""
import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EnhancementResult:
    original: str
    enhanced: str
    language: str
    additions: list[str]  # what was added
    style_detected: list[str]


# ─── Enhancement templates ───

# Style-specific additions for image generation
IMAGE_ENHANCEMENTS = {
    "realistic": {
        "zh": [
            "超高清画质",
            "专业摄影棚灯光",
            "精细纹理细节",
            "自然光影渲染",
            "真实材质表现",
        ],
        "en": [
            "ultra detailed",
            "photorealistic",
            "professional studio lighting",
            "8K resolution",
            "ray tracing",
        ],
    },
    "cinematic": {
        "zh": [
            "电影级调色",
            "IMAX画质",
            "史诗级构图",
            "震撼光影效果",
            "杜比视界色调",
        ],
        "en": [
            "cinematic lighting",
            "IMAX quality",
            "epic composition",
            "Hollywood color grading",
            "anamorphic lens",
        ],
    },
    "anime": {
        "zh": [
            "精美动漫画风",
            "赛璐璐风格上色",
            "高质量线稿",
            "精致的色彩渐变",
        ],
        "en": [
            "anime art style",
            "cel shading",
            "high quality anime illustration",
            "vibrant colors",
        ],
    },
    "product": {
        "zh": [
            "商业产品摄影",
            "纯白背景",
            "影棚级灯光",
            "360度展示角度",
            "高端商业质感",
        ],
        "en": [
            "commercial product photography",
            "clean white background",
            "studio lighting",
            "professional retouching",
            "high-end commercial look",
        ],
    },
    "landscape": {
        "zh": [
            "壮丽广角构图",
            "黄金时段自然光",
            "层次分明的景深",
            "大气透视效果",
        ],
        "en": [
            "wide-angle majestic composition",
            "golden hour lighting",
            "atmospheric depth",
            "dramatic landscape photography",
        ],
    },
    "portrait": {
        "zh": [
            "专业人像灯光",
            "柔和的散景背景",
            "精细皮肤纹理",
            "自然的面部光影",
        ],
        "en": [
            "professional portrait lighting",
            "soft bokeh background",
            "fine skin texture",
            "natural facial lighting",
        ],
    },
}

# Video-specific camera movement terms
VIDEO_CAMERAMOVES = {
    "zoom_in": {"zh": "镜头缓慢推进", "en": "slow zoom in"},
    "zoom_out": {"zh": "镜头慢慢拉远", "en": "slow zoom out"},
    "pan_left": {"zh": "镜头左移扫描", "en": "slow pan left"},
    "pan_right": {"zh": "镜头右移扫描", "en": "slow pan right"},
    "orbit": {"zh": "镜头环绕旋转", "en": "slow orbit around subject"},
    "tilt_up": {"zh": "镜头从下往上摇", "en": "camera tilt up"},
    "dolly": {"zh": "镜头平稳前进", "en": "smooth dolly forward"},
    "static": {"zh": "固定镜头微动", "en": "static shot with subtle motion"},
}

# Scene enhancement suffixes
SCENE_SUFFIXES = {
    "zh": [
        "高质量渲染",
        "电影质感",
        "极致细节",
        "专业级画面",
    ],
    "en": [
        "high quality rendering",
        "cinematic quality",
        "extreme detail",
        "professional grade",
    ],
}


class PromptEnhancer:
    """Enhances user prompts for better AI generation results."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def enhance(self, prompt: str, media_type: str = "auto",
                style: str = "auto", quality: str = "balanced") -> EnhancementResult:
        """Enhance a prompt based on detected style and media type."""
        if not self.enabled or quality == "fast":
            # Don't enhance for fast/quick mode
            return EnhancementResult(
                original=prompt,
                enhanced=prompt,
                language=self._detect_language(prompt),
                additions=[],
                style_detected=["none"],
            )

        lang = self._detect_language(prompt)
        style = self._detect_style(prompt) if style == "auto" else style

        enhanced = prompt
        additions = []

        if media_type in ("image", "auto"):
            enhanced, additions = self._enhance_image(enhanced, lang, style, additions)

        if media_type in ("video", "auto"):
            enhanced = self._enhance_video(enhanced, lang, additions)

        return EnhancementResult(
            original=prompt,
            enhanced=enhanced,
            language=lang,
            additions=additions,
            style_detected=[style],
        )

    def _enhance_image(self, prompt: str, lang: str, style: str,
                       additions: list[str]) -> tuple[str, list[str]]:
        """Add style-specific enhancements for image generation."""
        if style not in IMAGE_ENHANCEMENTS:
            return prompt, additions

        enhancements = IMAGE_ENHANCEMENTS[style]
        phrases = enhancements.get(lang, enhancements.get("en", []))

        # Add 1-2 enhancements based on quality
        # For now, add the first one that's not already in the prompt
        for phrase in phrases:
            if phrase.lower() not in prompt.lower():
                if lang == "zh":
                    prompt = f"{prompt}，{phrase}"
                else:
                    prompt = f"{prompt}, {phrase}"
                additions.append(phrase)
                break  # Just add one for now to keep it subtle

        return prompt, additions

    def _enhance_video(self, prompt: str, lang: str,
                       additions: list[str]) -> str:
        """Add camera movement and motion cues for video generation."""
        # If prompt already has camera/motion terms, don't add
        motion_terms_zh = ["镜头", "推进", "拉远", "旋转", "围绕", "移动", "动"]
        motion_terms_en = ["zoom", "pan", "orbit", "dolly", "motion", "move", "camera", "tilt"]

        has_motion = (
            any(t in prompt for t in motion_terms_zh) or
            any(t.lower() in prompt.lower() for t in motion_terms_en)
        )

        if not has_motion:
            # Add a default subtle camera movement
            default_move = VIDEO_CAMERAMOVES["zoom_in" if lang == "zh" else "zoom_in"]
            move_text = default_move.get(lang, default_move.get("en", "slow zoom in"))
            if lang == "zh":
                prompt = f"{prompt}，{move_text}"
            else:
                prompt = f"{prompt}, {move_text}"
            additions.append(move_text)

        return prompt

    def _detect_language(self, prompt: str) -> str:
        """Simple language detection."""
        chinese_chars = sum(1 for c in prompt if '一' <= c <= '鿿')
        if chinese_chars > len(prompt) * 0.2:
            return "zh"
        return "en"

    def _detect_style(self, prompt: str) -> str:
        """Detect style from prompt keywords."""
        prompt_lower = prompt.lower()

        style_patterns = {
            "realistic": ["写实", "真实", "photorealistic", "照片", "逼真", "摄影"],
            "cinematic": ["电影", "cinematic", "大片", "震撼", "trailer", "预告"],
            "anime": ["动漫", "anime", "二次元", "卡通", "manga", "赛博朋克"],
            "product": ["产品", "product", "商品", "电商", "展示", "广告"],
            "landscape": ["风景", "landscape", "自然", "山水", "mountain", "ocean"],
            "portrait": ["人像", "portrait", "人物", "face", "角色"],
        }

        for style_name, kws in style_patterns.items():
            if any(kw in prompt_lower for kw in kws):
                return style_name

        return "realistic"  # default


# Singleton
enhancer = PromptEnhancer(enabled=True)
