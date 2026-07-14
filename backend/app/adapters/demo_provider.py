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


def _cover_resize(img, w: int, h: int):
    """Resize+center-crop so the image fills (w,h) without distortion."""
    from PIL import Image
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = max(w, int(iw * scale)), max(h, int(ih * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


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


def _load_local_image(url: str):
    """Load a locally-stored /api/v1/media image as a PIL.Image (for keyframe base)."""
    if not url:
        return None
    try:
        from PIL import Image
        prefix = f"{MEDIA_URL_PREFIX}/"
        idx = url.find(prefix)
        if idx >= 0:
            rel = url[idx + len(prefix):].split("?", 1)[0]
            p = Path(settings.STORAGE_LOCAL_PATH) / rel
            if p.exists():
                return Image.open(p).convert("RGB")
        if url.startswith(("http://", "https://")):
            import httpx
            from io import BytesIO
            with httpx.Client(timeout=15, follow_redirects=True) as c:
                r = c.get(url); r.raise_for_status()
                return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception as e:
        logger.warning("[demo] load base image failed: %s", e)
    return None


def render_demo_image(prompt: str, size: str, style: Optional[str], index: int = 0,
                      seed: Optional[str] = None) -> str:
    """Render one demo image locally; return its /api/v1/media/... URL."""
    from PIL import Image  # noqa: F401 — ensure Pillow present

    w, h = _parse_size(size)
    seed = seed or _seed_from(prompt, index)
    img = _fetch_seed_photo(seed, w, h) or _gradient_image(seed, w, h)
    if img.size != (w, h):
        img = img.resize((w, h))
    img = _apply_style_grade(img, style)
    img = _add_watermark(img)

    name = f"{uuid.uuid4().hex[:12]}.jpg"
    out_path = _generated_dir() / name
    img.save(out_path, "JPEG", quality=88)
    return f"{MEDIA_URL_PREFIX}/{GENERATED_SUBDIR}/{name}"


def render_demo_video(prompt: str, resolution: str, duration: int, style: Optional[str],
                      base_image_url: Optional[str] = None, seed: Optional[str] = None) -> tuple[str, str]:
    """
    Render one demo video (Ken Burns zoom over an image) with ffmpeg.
    If base_image_url is given (keyframe / reference image), animate THAT image —
    this mirrors real image-to-video and keeps every shot visually consistent.
    Returns (video_url, thumbnail_url).
    """
    w, h = _parse_size(resolution, default=(1280, 720))
    duration = max(2, min(int(duration or 5), 12))
    seed = seed or _seed_from(prompt, 0)
    img = _load_local_image(base_image_url) or _fetch_seed_photo(seed, w, h) or _gradient_image(seed, w, h)
    if img.size != (w, h):
        # cover-crop to fill the target canvas (keeps aspect, no distortion)
        img = _cover_resize(img, w, h)
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


def _local_media_path(url: str) -> Optional[str]:
    """Map a served /api/v1/media/<sub>/<name> URL back to a local file path."""
    if not url:
        return None
    prefix = f"{MEDIA_URL_PREFIX}/"
    idx = url.find(prefix)
    if idx < 0:
        return None
    rel = url[idx + len(prefix):].split("?", 1)[0]
    p = Path(settings.STORAGE_LOCAL_PATH) / rel
    return str(p) if p.exists() else None


def _probe_size(path: str) -> tuple[int, int]:
    """Return (w,h) of a video via ffprobe; fall back to 1280x720."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", path],
            check=True, capture_output=True, timeout=30,
        ).stdout.decode().strip()
        w, h = out.split("x")[:2]
        return int(w), int(h)
    except Exception:
        return 1280, 720


def _probe_duration(path: str) -> float:
    """Return duration (s) of a media file via ffprobe; fall back to 5.0."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            check=True, capture_output=True, timeout=30,
        ).stdout.decode().strip()
        return float(out)
    except Exception:
        return 5.0


def _srt_timestamp(seconds: float) -> str:
    s = max(0.0, float(seconds))
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    ms = int(round((s - int(s)) * 1000))
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def _write_srt(subtitle_track: list[dict], path: Path) -> None:
    lines: list[str] = []
    for i, sub in enumerate(subtitle_track, 1):
        text = (sub.get("text") or "").strip()
        if not text:
            continue
        start = float(sub.get("start", 0))
        end = float(sub.get("end", start + 5))
        if end <= start:
            end = start + 3
        lines.append(str(i))
        lines.append(f"{_srt_timestamp(start)} --> {_srt_timestamp(end)}")
        lines.append(text)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _burn_subtitles(video_path: Path, subtitle_track: list[dict]) -> Path:
    """Burn SRT subtitles into the composed video (bottom-center)."""
    if not subtitle_track:
        return video_path
    srt_path = video_path.with_suffix(".srt")
    _write_srt(subtitle_track, srt_path)
    if not srt_path.exists() or srt_path.stat().st_size == 0:
        return video_path
    out_path = video_path.with_name(f"{video_path.stem}_sub.mp4")
    srt_esc = str(srt_path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    vf = (
        f"subtitles=filename='{srt_esc}':"
        "force_style='FontSize=22,PrimaryColour=&HFFFFFF&,"
        "OutlineColour=&H000000&,BorderStyle=3,Outline=2,Alignment=2,MarginV=36'"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path),
         "-vf", vf, "-c:a", "copy", str(out_path)],
        check=True, capture_output=True, timeout=180,
    )
    return out_path


def compose_final_video(video_urls: list[str], style: Optional[str] = None,
                        with_audio: bool = True, narration_url: Optional[str] = None,
                        *, transitions: Optional[list[str]] = None,
                        subtitle_track: Optional[list[dict]] = None) -> tuple[str, str]:
    """
    Stitch multiple shot videos into ONE final film (the Director Agent's hero
    deliverable). Scales/pads every shot to the first shot's canvas, concatenates
    with ffmpeg, and muxes audio: a real TTS narration track when provided
    (narration_url), otherwise a soft procedural ambient bed. Optional subtitle_track
    is burned into the final MP4 via ffmpeg subtitles filter. Returns
    (final_video_url, poster_url).
    """
    paths = [p for p in (_local_media_path(u) for u in video_urls) if p]
    if not paths:
        raise RuntimeError("compose: no local shot videos to stitch")

    gen_dir = _generated_dir()
    out_name = f"final_{uuid.uuid4().hex[:12]}.mp4"
    out_path = gen_dir / out_name

    w, h = _probe_size(paths[0])
    w -= w % 2
    h -= h % 2

    audio_args = []
    total_dur = sum(_probe_duration(p) for p in paths) if with_audio else 0.0
    narration_path = _local_media_path(narration_url) if narration_url else None
    if with_audio and narration_path:
        # Real narration voiceover, trimmed to film length via -shortest.
        audio_args = ["-i", narration_path]
    elif with_audio and total_dur > 0:
        # FINITE soft sine pad (196Hz), length = total film — 无限源会让 ffmpeg 挂起。
        audio_args = ["-f", "lavfi", "-t", f"{total_dur:.2f}",
                      "-i", "sine=frequency=196:sample_rate=44100"]
    else:
        with_audio = False

    inputs = []
    for p in paths:
        inputs += ["-i", p]
    audio_idx = len(paths)  # the lavfi audio input index (added after video inputs)

    filters = []
    for i in range(len(paths)):
        filters.append(
            f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25[v{i}]"
        )
    concat_in = "".join(f"[v{i}]" for i in range(len(paths)))
    filter_complex = ";".join(filters) + f";{concat_in}concat=n={len(paths)}:v=1:a=0[outv]"
    if with_audio:
        # Narration at full listenable volume; procedural ambient bed kept subtle.
        a_filter = "volume=1.0" if narration_path else "tremolo=f=0.12:d=0.6,volume=0.05"
        filter_complex += f";[{audio_idx}:a]{a_filter}[aud]"

    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, *audio_args,
           "-filter_complex", filter_complex, "-map", "[outv]"]
    if with_audio:
        cmd += ["-map", "[aud]", "-c:a", "aac", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25",
            "-movflags", "+faststart", str(out_path)]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        stderr = getattr(e, "stderr", b"")
        logger.error("[demo] compose failed: %s", stderr[:600] if stderr else e)
        raise RuntimeError(f"Final compose failed: {e}")

    if subtitle_track:
        try:
            burned = _burn_subtitles(out_path, subtitle_track)
            if burned != out_path and burned.exists():
                out_path = burned
                out_name = out_path.name
        except Exception as e:
            logger.warning("[demo] subtitle burn failed (video still usable): %s", e)

    # Poster = first frame of the final film
    poster_name = f"finalposter_{uuid.uuid4().hex[:12]}.jpg"
    poster_path = gen_dir / poster_name
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.1", "-i", str(out_path),
             "-frames:v", "1", "-q:v", "3", str(poster_path)],
            check=True, capture_output=True, timeout=60,
        )
        poster_url = f"{MEDIA_URL_PREFIX}/{GENERATED_SUBDIR}/{poster_name}"
    except Exception:
        poster_url = ""

    return (f"{MEDIA_URL_PREFIX}/{GENERATED_SUBDIR}/{out_name}", poster_url)


def run_demo_image_tool(op: str, data: bytes, factor: str = "2", ratio: str = "16:9") -> str:
    """Offline image-tool fallback (used only when no KIE key is configured).
    upscale = Lanczos resize; bg-remove/edit/extend = pass-through re-encode."""
    import io as _io
    gen_dir = _generated_dir()
    name = f"tool_{op}_{uuid.uuid4().hex[:10]}.png"
    out = gen_dir / name
    img = Image.open(_io.BytesIO(data)).convert("RGBA")
    if op == "upscale":
        try:
            f = int(float(factor))
        except Exception:
            f = 2
        f = max(1, min(f, 4))
        img = img.resize((img.width * f, img.height * f), Image.LANCZOS)
    elif op == "extend":
        try:
            rw, rh = (int(x) for x in ratio.split(":"))
        except Exception:
            rw, rh = 16, 9
        target_w = max(img.width, int(img.height * rw / rh))
        target_h = max(img.height, int(img.width * rh / rw))
        canvas = Image.new("RGBA", (target_w, target_h), (20, 20, 30, 255))
        canvas.paste(img, ((target_w - img.width) // 2, (target_h - img.height) // 2))
        img = canvas
    img.save(out, "PNG")
    return f"{MEDIA_URL_PREFIX}/{GENERATED_SUBDIR}/{name}"


def render_demo_speech(text: str) -> str:
    """Offline placeholder 'voiceover': a short soft tone whose length scales
    with the text (used only when no TTS provider key is configured)."""
    dur = max(2, min(len(text) // 6, 20))
    gen_dir = _generated_dir()
    name = f"tts_{uuid.uuid4().hex[:12]}.mp3"
    out = gen_dir / name
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-t", str(dur),
             "-i", "sine=frequency=330:sample_rate=44100",
             "-af", "tremolo=f=5:d=0.4,volume=0.25", "-c:a", "libmp3lame", str(out)],
            check=True, capture_output=True, timeout=60,
        )
    except Exception as e:
        raise RuntimeError(f"Demo speech render failed: {e}")
    return f"{MEDIA_URL_PREFIX}/{GENERATED_SUBDIR}/{name}"


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
