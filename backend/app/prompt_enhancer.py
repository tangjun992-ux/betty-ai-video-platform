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
# Each style bucket mixes lighting / composition / lens / detail cues so the
# enhancer can compose a rich, coherent prompt (multiple complementary phrases),
# not just a single tacked-on word.

IMAGE_ENHANCEMENTS = {
    "realistic": {
        "zh": ["超高清写实质感", "专业摄影棚灯光", "精细纹理细节", "自然光影渲染", "浅景深虚化", "85mm 定焦镜头"],
        "en": ["photorealistic", "professional studio lighting", "ultra-detailed textures", "natural soft light", "shallow depth of field", "shot on 85mm lens"],
    },
    "cinematic": {
        "zh": ["电影级调色", "戏剧性光影", "史诗级宽银幕构图", "体积光氛围", "宽荧幕变形镜头", "35mm 胶片质感"],
        "en": ["cinematic color grading", "dramatic lighting", "epic widescreen composition", "volumetric light", "anamorphic lens flare", "35mm film grain"],
    },
    "anime": {
        "zh": ["精美动漫画风", "赛璐璐上色", "干净的线稿", "鲜明的色彩渐变", "细腻的高光", "新海诚式天空"],
        "en": ["beautiful anime art style", "cel shading", "clean lineart", "vibrant color gradients", "detailed highlights", "Makoto Shinkai style sky"],
    },
    "product": {
        "zh": ["商业产品摄影", "干净背景", "柔光箱布光", "细腻反射高光", "极简构图", "高端质感"],
        "en": ["commercial product photography", "clean seamless background", "softbox lighting", "crisp reflective highlights", "minimal composition", "premium look"],
    },
    "landscape": {
        "zh": ["壮丽广角构图", "黄金时段光线", "层次分明的景深", "大气透视", "细腻的天空细节", "自然色彩"],
        "en": ["majestic wide-angle composition", "golden hour light", "layered depth", "atmospheric perspective", "detailed sky", "natural color palette"],
    },
    "portrait": {
        "zh": ["专业人像布光", "柔和散景背景", "细腻皮肤质感", "自然的面部光影", "眼神光", "50mm 人像镜头"],
        "en": ["professional portrait lighting", "soft bokeh background", "fine skin detail", "natural facial light", "catchlight in eyes", "50mm portrait lens"],
    },
    "sci-fi": {
        "zh": ["未来科技感", "霓虹辉光", "冷色调金属反射", "体积雾光", "全息元素", "赛博朋克氛围"],
        "en": ["futuristic sci-fi", "neon glow", "cool metallic reflections", "volumetric fog", "holographic elements", "cyberpunk atmosphere"],
    },
    "fantasy": {
        "zh": ["奇幻史诗氛围", "魔法光效", "梦幻粒子", "戏剧性云层", "宏大场景", "概念艺术风格"],
        "en": ["epic fantasy atmosphere", "magical glow", "dreamy particles", "dramatic clouds", "grand scale", "concept art style"],
    },
    "food": {
        "zh": ["诱人美食摄影", "暖色调布光", "微距特写", "蒸汽与新鲜感", "浅景深", "杂志级摆盘"],
        "en": ["appetizing food photography", "warm lighting", "macro close-up", "steam and freshness", "shallow depth of field", "magazine-quality plating"],
    },
    "architecture": {
        "zh": ["建筑摄影", "广角透视校正", "干净的几何线条", "自然天光", "材质细节", "极简现代"],
        "en": ["architectural photography", "wide-angle with perspective correction", "clean geometric lines", "natural daylight", "material detail", "minimal modern"],
    },
    "artistic": {
        "zh": ["当代艺术风格", "富有表现力的笔触", "大胆的撞色", "细腻的肌理", "构图讲究", "画廊级作品"],
        "en": ["contemporary art style", "expressive brushstrokes", "bold color contrast", "rich texture", "considered composition", "gallery-quality"],
    },
    "3d-render": {
        "zh": ["高质量 3D 渲染", "柔和全局光照", "细腻材质", "光线追踪反射", "干净的工作室背景", "皮克斯质感"],
        "en": ["high-quality 3D render", "soft global illumination", "detailed materials", "ray-traced reflections", "clean studio background", "Pixar-style"],
    },
    "cute/kawaii": {
        "zh": ["可爱治愈风", "柔和粉彩色调", "圆润造型", "明亮均匀布光", "细腻插画质感"],
        "en": ["cute kawaii style", "soft pastel palette", "rounded shapes", "bright even lighting", "detailed illustration"],
    },
    "chinese": {
        "zh": ["国风美学", "水墨意境", "细腻工笔", "东方色彩", "留白构图", "高级质感"],
        "en": ["Chinese aesthetic", "ink-wash mood", "fine gongbi detail", "oriental color palette", "negative-space composition", "premium finish"],
    },
}

# Appended once for a final quality boost (deduped against the prompt).
UNIVERSAL_QUALITY = {
    "zh": ["超高清 4K 画质", "极致细节", "专业级出品"],
    "en": ["ultra high definition 4K", "extreme detail", "professional grade"],
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

        if media_type == "video":
            # Video benefits from a couple of visual/lighting cues too, plus camera.
            enhanced, additions = self._enhance_image(enhanced, lang, style, additions, "video")
            enhanced = self._enhance_video(enhanced, lang, additions, style)
        else:  # image or auto
            enhanced, additions = self._enhance_image(enhanced, lang, style, additions, quality)
            if media_type == "auto":
                enhanced = self._enhance_video(enhanced, lang, additions, style)

        return EnhancementResult(
            original=prompt,
            enhanced=enhanced,
            language=lang,
            additions=additions,
            style_detected=[style],
        )

    # How many style modifiers to append per quality tier.
    _STYLE_COUNT = {"fast": 0, "balanced": 3, "high": 4, "video": 2}

    def _join(self, prompt: str, phrase: str, lang: str) -> str:
        sep = "，" if lang == "zh" else ", "
        return f"{prompt}{sep}{phrase}"

    def _enhance_image(self, prompt: str, lang: str, style: str,
                       additions: list[str], quality: str = "balanced") -> tuple[str, list[str]]:
        """Compose several complementary style/lighting/detail modifiers."""
        bucket = IMAGE_ENHANCEMENTS.get(style) or IMAGE_ENHANCEMENTS["realistic"]
        phrases = bucket.get(lang, bucket.get("en", []))

        want = self._STYLE_COUNT.get(quality, 3)
        added = 0
        for phrase in phrases:
            if added >= want:
                break
            if phrase.lower() not in prompt.lower():
                prompt = self._join(prompt, phrase, lang)
                additions.append(phrase)
                added += 1

        # One universal quality suffix for a final polish.
        for q in UNIVERSAL_QUALITY.get(lang, UNIVERSAL_QUALITY["en"]):
            if q.lower() not in prompt.lower():
                prompt = self._join(prompt, q, lang)
                additions.append(q)
                break

        return prompt, additions

    # Style → best-fit default camera movement.
    _STYLE_CAMERA = {
        "landscape": "pan_right", "architecture": "tilt_up", "product": "orbit",
        "portrait": "dolly", "food": "zoom_in", "cinematic": "dolly",
        "sci-fi": "orbit", "fantasy": "zoom_out",
    }

    def _enhance_video(self, prompt: str, lang: str, additions: list[str],
                       style: str = "realistic") -> str:
        """Add a style-appropriate camera move plus a motion/quality cue."""
        motion_terms_zh = ["镜头", "推进", "拉远", "旋转", "围绕", "移动", "运镜", "摇"]
        motion_terms_en = ["zoom", "pan", "orbit", "dolly", "motion", "move", "camera", "tilt", "tracking"]
        has_motion = (
            any(t in prompt for t in motion_terms_zh) or
            any(t.lower() in prompt.lower() for t in motion_terms_en)
        )

        if not has_motion:
            move_key = self._STYLE_CAMERA.get(style, "zoom_in")
            move = VIDEO_CAMERAMOVES[move_key]
            move_text = move.get(lang, move.get("en", "slow zoom in"))
            prompt = self._join(prompt, move_text, lang)
            additions.append(move_text)

        # Cinematic motion / continuity cue for smoother, more filmic output.
        cue = "流畅自然的运动，连贯的画面过渡" if lang == "zh" else "smooth natural motion, coherent transitions"
        if cue.lower() not in prompt.lower():
            prompt = self._join(prompt, cue, lang)
            additions.append(cue)

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

        # Order matters — more specific styles first.
        style_patterns = {
            "sci-fi": ["科幻", "sci-fi", "赛博朋克", "cyberpunk", "未来", "futuristic", "机甲", "robot", "太空", "space", "全息"],
            "fantasy": ["奇幻", "fantasy", "魔法", "magic", "精灵", "dragon", "城堡", "castle", "仙侠", "神话"],
            "food": ["美食", "food", "食物", "甜品", "cake", "咖啡", "coffee", "拉面", "ramen", "餐"],
            "architecture": ["建筑", "architecture", "室内", "interior", "别墅", "villa", "loft", "楼"],
            "3d-render": ["3d", "渲染", "render", "c4d", "blender", "octane", "皮克斯", "pixar"],
            "cute/kawaii": ["可爱", "cute", "kawaii", "萌", "q版", "chibi", "小猫", "小狗", "puppy", "kitten"],
            "chinese": ["国风", "中式", "水墨", "工笔", "汉服", "古风"],
            "anime": ["动漫", "anime", "二次元", "卡通", "manga", "漫画"],
            "product": ["产品", "product", "商品", "电商", "展示", "广告", "包装"],
            "portrait": ["人像", "portrait", "人物", "face", "角色", "写真", "头像", "肖像"],
            "landscape": ["风景", "landscape", "自然", "山水", "mountain", "ocean", "森林", "日出", "日落"],
            "cinematic": ["电影", "cinematic", "大片", "震撼", "trailer", "预告", "宣传片"],
            "artistic": ["油画", "水彩", "art", "艺术", "抽象", "abstract", "插画", "illustration"],
            "realistic": ["写实", "真实", "photorealistic", "照片", "逼真", "摄影", "realistic"],
        }

        for style_name, kws in style_patterns.items():
            if any(kw in prompt_lower for kw in kws):
                return style_name

        return "realistic"  # default


# Singleton
enhancer = PromptEnhancer(enabled=True)
