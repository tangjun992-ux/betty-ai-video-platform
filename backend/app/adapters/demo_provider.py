"""
Demo generation provider — produces real local media when no model provider
key (KIE / Replicate / OpenAI / ...) is configured.

This keeps the whole platform demonstrable end-to-end (image + video generation,
library, explore gallery, agent) in environments without paid API credentials.
Media is rendered locally (Pillow for images, ffmpeg for video), stored under
STORAGE_LOCAL_PATH and served from /api/v1/media, so it never expires and works
fully offline once the seed photo is fetched (with a pure-Pillow gradient
fallback when there is no network).
"""
from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from app.adapters.base import BaseModelAdapter, GenerationResult
from app.config import settings

logger = logging.getLogger(__name__)

_FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
GENERATED_SUBDIR = "generated"
MEDIA_URL_PREFIX = "/api/v1/media"

# Style → color grade (multiplicative RGB tint + saturation/contrast tweaks)
_STYLE_GRADES = {
    "cyberpunk": {"tint": (0.75, 0.7, 1.25), "sat": 1.35, "contrast": 1.15},
    "赛博朋克": {"tint": (0.75, 0.7, 1.25), "sat": 1.35, "contrast": 1.15},
    "cinematic": {"tint": (1.1, 1.0, 0.85), "sat": 1.1, "contrast": 1.2},
    "电影级": {"tint": (1.1, 1.0, 0.85), "sat": 1.1, "contrast": 1.2},
    "anime": {"tint": (1.05, 1.0, 1.1), "sat": 1.5, "contrast": 1.1},
    "动漫": {"tint": (1.05, 1.0, 1.1), "sat": 1.5, "contrast": 1.1},
    "realistic": {"tint": (1.0, 1.0, 1.0), "sat": 1.05, "contrast": 1.05},
    "写实": {"tint": (1.0, 1.0, 1.0), "sat": 1.05, "contrast": 1.05},
    "product": {"tint": (1.02, 1.02, 1.02), "sat": 1.1, "contrast": 1.1},
    "portrait": {"tint": (1.05, 0.98, 0.95), "sat": 1.08, "contrast": 1.05},
    "fantasy": {"tint": (1.05, 0.95, 1.15), "sat": 1.3, "contrast": 1.1},
    "奇幻": {"tint": (1.05, 0.95, 1.15), "sat": 1.3, "contrast": 1.1},
    "landscape": {"tint": (0.98, 1.05, 1.02), "sat": 1.2, "contrast": 1.1},
    "风景": {"tint": (0.98, 1.05, 1.02), "sat": 1.2, "contrast": 1.1},
    "3d-render": {"tint": (1.0, 1.0, 1.05), "sat": 1.2, "contrast": 1.15},
    "sci-fi": {"tint": (0.85, 0.95, 1.2), "sat": 1.25, "contrast": 1.15},
    "科幻": {"tint": (0.85, 0.95, 1.2), "sat": 1.25, "contrast": 1.15},
}


def any_provider_configured() -> bool:
    """True when at least one real generation provider key is set."""
    return bool(
        settings.KIE_API_KEY
        or settings.REPLICATE_API_KEY
        or settings.OPENAI_API_KEY
        or settings.SEEDANCE_API_KEY
        or (settings.KLING_ACCESS_KEY and settings.KLING_SECRET_KEY)
    )


def demo_mode_active() -> bool:
    """Demo mode kicks in when no provider is configured (or forced via env)."""
    if os.getenv("DEMO_GENERATION", "").lower() in ("1", "true", "yes"):
        return True
    return not any_provider_configured()


def _generated_dir() -> Path:
    out = Path(settings.STORAGE_LOCAL_PATH) / GENERATED_SUBDIR
    out.mkdir(parents=True, exist_ok=True)
    return out


def _parse_size(size: str, default=(1024, 1024)) -> tuple[int, int]:
    """Parse 'WxH', 'WIDTHxHEIGHT', '1080p', '4k' → (w, h) with even numbers."""
    s = (size or "").lower().strip()
    if "x" in s:
        try:
            w, h = s.split("x")[:2]
            w, h = int(w), int(h)
        except (ValueError, IndexError):
            w, h = default
    elif s in ("4k", "2160p"):
        w, h = 3840, 2160
    elif s == "2k" or s == "1440p":
        w, h = 2560, 1440
    elif s == "1080p":
        w, h = 1920, 1080
    elif s == "720p":
        w, h = 1280, 720
    else:
        w, h = default
    # Clamp for local rendering speed and ensure even dims (h264 requirement)
    w = max(64, min(w, 1920))
    h = max(64, min(h, 1920))
    return (w - w % 2, h - h % 2)


def _seed_from(prompt: str, index: int = 0) -> str:
    return hashlib.sha1(f"{prompt}|{index}".encode("utf-8")).hexdigest()[:16]


def _fetch_seed_photo(seed: str, w: int, h: int):
    """Fetch a deterministic stock photo from picsum; return PIL.Image or None."""
    try:
        import httpx
        from PIL import Image
        from io import BytesIO

        url = f"https://picsum.photos/seed/{seed}/{w}/{h}"
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            return img
    except Exception as e:
        logger.warning("[demo] seed photo fetch failed (%s), using gradient", e)
        return None


def _gradient_image(seed: str, w: int, h: int):
    """Pure-Pillow deterministic gradient fallback (no network)."""
    from PIL import Image

    hv = int(seed, 16)
    c1 = ((hv >> 0) & 0xFF, (hv >> 8) & 0xFF, (hv >> 16) & 0xFF)
    c2 = ((hv >> 24) & 0xFF, (hv >> 32) & 0xFF, (hv >> 40) & 0xFF)
    base = Image.new("RGB", (w, h))
    px = base.load()
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(c1[0] * (1 - t) + c2[0] * t)
        g = int(c1[1] * (1 - t) + c2[1] * t)
        b = int(c1[2] * (1 - t) + c2[2] * t)
        for x in range(w):
            tx = x / max(1, w - 1)
            px[x, y] = (
                int(r * (0.7 + 0.3 * tx)),
                int(g * (0.7 + 0.3 * (1 - tx))),
                int(b * (0.8 + 0.2 * tx)),
            )
    return base


def _apply_style_grade(img, style: Optional[str]):
    from PIL import ImageEnhance

    grade = _STYLE_GRADES.get((style or "").lower())
    if not grade:
        return img
    r, g, b = img.split()
    tr, tg, tb = grade["tint"]
    r = r.point(lambda v: min(255, int(v * tr)))
    g = g.point(lambda v: min(255, int(v * tg)))
    b = b.point(lambda v: min(255, int(v * tb)))
    from PIL import Image as _Image

    img = _Image.merge("RGB", (r, g, b))
    img = ImageEnhance.Color(img).enhance(grade["sat"])
    img = ImageEnhance.Contrast(img).enhance(grade["contrast"])
    return img


def _add_watermark(img):
    """Small unobtrusive 'DEMO' badge in the corner to keep things honest."""
    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    fs = max(12, int(min(w, h) * 0.028))
    try:
        font = ImageFont.truetype(_FONT_BOLD, fs)
    except Exception:
        font = ImageFont.load_default()
    label = "DEMO"
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = int(fs * 0.5)
    x0, y0 = w - tw - pad * 3, h - th - pad * 3
    draw.rounded_rectangle(
        [x0 - pad, y0 - pad, x0 + tw + pad, y0 + th + pad],
        radius=pad, fill=(0, 0, 0, 120),
    )
    draw.text((x0, y0 - bbox[1]), label, font=font, fill=(255, 255, 255, 210))
    return img


def render_demo_image(prompt: str, size: str, style: Optional[str], index: int = 0) -> str:
    """Render one demo image locally; return its /api/v1/media/... URL."""
    from PIL import Image  # noqa: F401 — ensure Pillow present

    w, h = _parse_size(size)
    seed = _seed_from(prompt, index)
    img = _fetch_seed_photo(seed, w, h) or _gradient_image(seed, w, h)
    if img.size != (w, h):
        img = img.resize((w, h))
    img = _apply_style_grade(img, style)
    img = _add_watermark(img)

    name = f"{uuid.uuid4().hex[:12]}.jpg"
    out_path = _generated_dir() / name
    img.save(out_path, "JPEG", quality=88)
    return f"{MEDIA_URL_PREFIX}/{GENERATED_SUBDIR}/{name}"


def render_demo_video(prompt: str, resolution: str, duration: int, style: Optional[str]) -> tuple[str, str]:
    """
    Render one demo video (Ken Burns zoom over a seeded image) with ffmpeg.
    Returns (video_url, thumbnail_url).
    """
    w, h = _parse_size(resolution, default=(1280, 720))
    duration = max(2, min(int(duration or 5), 12))
    seed = _seed_from(prompt, 0)
    img = _fetch_seed_photo(seed, w, h) or _gradient_image(seed, w, h)
    if img.size != (w, h):
        img = img.resize((w, h))
    img = _apply_style_grade(img, style)

    gen_dir = _generated_dir()
    thumb_name = f"{uuid.uuid4().hex[:12]}.jpg"
    thumb_path = gen_dir / thumb_name
    watermarked = _add_watermark(img.copy())
    watermarked.save(thumb_path, "JPEG", quality=88)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        base_png = tf.name
    img.save(base_png, "PNG")

    video_name = f"{uuid.uuid4().hex[:12]}.mp4"
    video_path = gen_dir / video_name

    fps = 25
    total_frames = duration * fps
    # Ken Burns: slow zoom-in with gentle drift, then a bottom gradient + DEMO tag
    zoom_expr = f"min(zoom+0.0012,1.25)"
    vf = (
        f"scale={w*2}:{h*2},"
        f"zoompan=z='{zoom_expr}':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={w}x{h}:fps={fps},"
        f"drawbox=x=0:y=ih-ih/6:w=iw:h=ih/6:color=black@0.35:t=fill,"
        f"drawtext=fontfile={_FONT_BOLD}:text='DEMO':fontcolor=white@0.85:"
        f"fontsize={max(16,int(min(w,h)*0.03))}:x=w-tw-24:y=h-th-24:"
        f"box=1:boxcolor=black@0.4:boxborderw=8"
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", base_png,
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps),
        "-movflags", "+faststart",
        str(video_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        stderr = getattr(e, "stderr", b"")
        logger.error("[demo] ffmpeg failed: %s", stderr[:500] if stderr else e)
        raise RuntimeError(f"Demo video render failed: {e}")
    finally:
        try:
            os.unlink(base_png)
        except OSError:
            pass

    return (
        f"{MEDIA_URL_PREFIX}/{GENERATED_SUBDIR}/{video_name}",
        f"{MEDIA_URL_PREFIX}/{GENERATED_SUBDIR}/{thumb_name}",
    )


class DemoAdapter(BaseModelAdapter):
    """Drop-in adapter used by Celery tasks when no provider key is configured."""

    def __init__(self, model_label: str = "demo"):
        # Preserve the originally-selected model name for nicer gallery display.
        self._label = model_label or "demo"

    @property
    def provider_name(self) -> str:
        return "Demo (local render)"

    @property
    def supported_models(self) -> list[str]:
        return ["demo"]

    @property
    def capabilities(self) -> dict:
        return {
            "media_types": ["image", "video"],
            "max_resolution": "1080p",
            "max_duration_s": 12,
            "avg_latency_s": 3,
            "styles": list(_STYLE_GRADES.keys()),
            "cost_per_image_credits": 2,
            "cost_per_5s_video_credits": 3,
        }

    async def generate_image(
        self, prompt: str, size: str = "1024x1024", style: str = "auto",
        count: int = 1, **kwargs,
    ) -> list[GenerationResult]:
        count = max(1, min(int(count or 1), 4))
        results = []
        for i in range(count):
            url = render_demo_image(prompt, size, style, index=i)
            results.append(GenerationResult(
                media_url=url, thumbnail_url=url, media_type="image",
                model=self._label, resolution=size, cost=2.0,
                meta={"demo": True, "style": style},
            ))
        return results

    async def generate_video(
        self, prompt: str, image_url: Optional[str] = None, duration: int = 5,
        resolution: str = "1080p", **kwargs,
    ) -> GenerationResult:
        video_url, thumb_url = render_demo_video(prompt, resolution, duration, kwargs.get("style"))
        return GenerationResult(
            media_url=video_url, thumbnail_url=thumb_url, media_type="video",
            model=self._label, resolution=resolution,
            duration=float(duration or 5), cost=3.0,
            meta={"demo": True},
        )
