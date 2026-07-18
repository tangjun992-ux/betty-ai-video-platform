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


_PORTRAIT_HINTS = (
    "portrait", "人像", "数字人", "口播", "主播", "半身", "棚拍",
    "talking", "avatar", "face", "headshot", "唇形",
)


def _wants_portrait(prompt: str, style: Optional[str]) -> bool:
    s = (style or "").lower()
    if s in ("portrait", "人像"):
        return True
    p = (prompt or "").lower()
    return any(h.lower() in p for h in _PORTRAIT_HINTS)


def _render_portrait_stub(w: int, h: int, seed: str):
    """Deterministic studio headshot placeholder (no random landscape).

    Free preview must never imply a photoreal digital human from picsum stock.
    This draws an obvious DEMO avatar so talking/lipsync plans stay on-subject.
    """
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    hv = int(seed[:12], 16) if seed else 0
    # Soft studio backdrop
    bg = (
        40 + (hv & 0x1F),
        44 + ((hv >> 5) & 0x1F),
        56 + ((hv >> 10) & 0x2F),
    )
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img, "RGBA")
    # Soft key light ellipse behind subject
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = w // 2, int(h * 0.38)
    gd.ellipse(
        [cx - int(w * 0.42), cy - int(h * 0.28), cx + int(w * 0.42), cy + int(h * 0.28)],
        fill=(255, 240, 220, 55),
    )
    img = Image.alpha_composite(img.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(radius=max(8, w // 40)))).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    skin = (
        210 - ((hv >> 8) & 0x28),
        175 - ((hv >> 12) & 0x20),
        150 - ((hv >> 16) & 0x18),
    )
    shirt = (
        70 + ((hv >> 4) & 0x40),
        90 + ((hv >> 10) & 0x50),
        140 + ((hv >> 14) & 0x40),
    )
    # Shoulders / torso
    shoulder_y = int(h * 0.58)
    draw.ellipse(
        [int(w * 0.08), shoulder_y, int(w * 0.92), h + int(h * 0.2)],
        fill=shirt + (255,),
    )
    # Neck
    nw = int(w * 0.14)
    draw.rectangle(
        [cx - nw // 2, int(h * 0.42), cx + nw // 2, shoulder_y + int(h * 0.05)],
        fill=skin + (255,),
    )
    # Head
    head_r = int(min(w, h) * 0.18)
    draw.ellipse(
        [cx - head_r, cy - int(head_r * 1.15), cx + head_r, cy + int(head_r * 1.05)],
        fill=skin + (255,),
    )
    # Simple facial features (clearly a placeholder, not photoreal)
    eye_y = cy - int(head_r * 0.15)
    eye_dx = int(head_r * 0.38)
    eye_r = max(3, head_r // 10)
    for ex in (cx - eye_dx, cx + eye_dx):
        draw.ellipse([ex - eye_r, eye_y - eye_r, ex + eye_r, eye_y + eye_r], fill=(40, 35, 35, 255))
    # Mouth (neutral closed line — preview is NOT lip-synced)
    mw = int(head_r * 0.45)
    my = cy + int(head_r * 0.35)
    draw.arc([cx - mw, my - eye_r, cx + mw, my + eye_r * 2], 20, 160, fill=(120, 70, 70, 255), width=max(2, head_r // 18))

    try:
        font = ImageFont.truetype(_FONT_BOLD, max(14, int(min(w, h) * 0.035)))
        font_s = ImageFont.truetype(_FONT_REGULAR, max(11, int(min(w, h) * 0.022)))
    except Exception:
        font = ImageFont.load_default()
        font_s = font
    title = "DEMO · Digital Human Placeholder"
    sub = "Not GPT Image / Not real lipsync"
    # Top banner
    draw.rectangle([0, 0, w, int(h * 0.08)], fill=(0, 0, 0, 160))
    draw.text((int(w * 0.04), int(h * 0.02)), title, font=font, fill=(255, 255, 255, 230))
    draw.text((int(w * 0.04), int(h * 0.085) + 4), sub, font=font_s, fill=(255, 220, 160, 220))
    return img.convert("RGB")


def render_demo_image(prompt: str, size: str, style: Optional[str], index: int = 0,
                      seed: Optional[str] = None) -> str:
    """Render one demo image locally; return its /api/v1/media/... URL.

    Portrait / talking briefs use a studio headshot stub — never random picsum
    landscapes — so free Director preview stays on-subject for digital humans.
    """
    from PIL import Image  # noqa: F401 — ensure Pillow present

    w, h = _parse_size(size)
    seed = seed or _seed_from(prompt, index)
    if _wants_portrait(prompt, style):
        img = _render_portrait_stub(w, h, seed)
    else:
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


def _srt_time_to_seconds(raw: str) -> float:
    """Parse SRT timestamp (HH:MM:SS,mmm or HH:MM:SS.mmm) to seconds."""
    ts = (raw or "").strip().replace(",", ".")
    parts = ts.split(":")
    if len(parts) != 3:
        raise ValueError(f"invalid SRT timestamp: {raw!r}")
    h = int(parts[0])
    m = int(parts[1])
    sec_parts = parts[2].split(".")
    sec = int(sec_parts[0])
    ms = int(sec_parts[1]) if len(sec_parts) > 1 else 0
    return h * 3600 + m * 60 + sec + ms / 1000.0


def parse_srt(content: str) -> list[dict]:
    """Parse SubRip (.srt) text into [{text, start, end}, ...]."""
    text = (content or "").lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    cues: list[dict] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if len(lines) < 2:
            continue
        idx = 0
        if lines[0].isdigit():
            idx = 1
        if idx >= len(lines):
            continue
        timing = lines[idx]
        if "-->" not in timing:
            continue
        start_raw, end_raw = [p.strip() for p in timing.split("-->", 1)]
        try:
            start = _srt_time_to_seconds(start_raw)
            end = _srt_time_to_seconds(end_raw)
        except ValueError:
            continue
        if end <= start:
            end = start + 1.0
        body = "\n".join(lines[idx + 1:]).strip()
        if not body:
            continue
        cues.append({"text": body, "start": round(start, 3), "end": round(end, 3)})
    return cues


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


EXPORT_PRESETS: dict[str, tuple[int, int]] = {
    "landscape_16_9": (1920, 1080),
    "portrait_9_16": (1080, 1920),
    "square_1_1": (1080, 1080),
}


def _trim_video(src: Path, start: float, end: float, dest: Path) -> None:
    """Trim a source clip to [start, end] seconds (video-only for concat pipeline)."""
    start_s = max(0.0, float(start))
    full = _probe_duration(src)
    end_s = float(end) if float(end) > 0 else full
    end_s = min(full, max(start_s + 0.1, end_s))
    duration = end_s - start_s
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", f"{start_s:.3f}",
            "-i", str(src),
            "-t", f"{duration:.3f}",
            "-an",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25",
            str(dest),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )


# CapCut/Creatify-style subtitle presets (ASS force_style). Not licensed fonts.
SUBTITLE_STYLES: dict[str, str] = {
    # Default / feed: high-contrast bottom caption
    "feed": (
        "FontSize=26,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,"
        "BorderStyle=3,Outline=3,Alignment=2,MarginV=48,Bold=1"
    ),
    # Talking avatar: larger, slightly higher for face clearance
    "talking": (
        "FontSize=28,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,"
        "BorderStyle=3,Outline=3,Alignment=2,MarginV=120,Bold=1"
    ),
    # Product ad: clean commercial caption
    "ad": (
        "FontSize=24,PrimaryColour=&H00F0F0F0&,OutlineColour=&H00101010&,"
        "BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=56"
    ),
    # Drama: cinematic softer caption
    "drama": (
        "FontSize=24,PrimaryColour=&H00FFF8E7&,OutlineColour=&H00202020&,"
        "BorderStyle=1,Outline=2,Alignment=2,MarginV=64"
    ),
}


def _burn_subtitles(
    video_path: Path,
    subtitle_track: list[dict],
    *,
    style: str | None = None,
) -> Path:
    """Burn SRT subtitles; ``style`` selects a SUBTITLE_STYLES preset."""
    if not subtitle_track:
        return video_path
    srt_path = video_path.with_suffix(".srt")
    _write_srt(subtitle_track, srt_path)
    if not srt_path.exists() or srt_path.stat().st_size == 0:
        return video_path
    out_path = video_path.with_name(f"{video_path.stem}_sub.mp4")
    srt_esc = str(srt_path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    force = SUBTITLE_STYLES.get(style or "", SUBTITLE_STYLES["feed"])
    vf = f"subtitles=filename='{srt_esc}':force_style='{force}'"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path),
         "-vf", vf, "-c:a", "copy", str(out_path)],
        check=True, capture_output=True, timeout=180,
    )
    return out_path


_CTA_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    _FONT_BOLD,
)


def _cta_fontfile() -> str:
    for p in _CTA_FONT_CANDIDATES:
        if Path(p).exists():
            return p
    return _FONT_BOLD


def _escape_drawtext(text: str) -> str:
    # ffmpeg drawtext: escape \ : ' %
    t = (text or "").replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")
    return t[:36]


# Scenario → procedural BGM character (still not a licensed Creatify library)
BGM_PRESETS: dict[str, dict] = {
    "soft": {"f1": 196.0, "f2": 293.66, "f3": 392.0, "lp": 1600, "vol": 0.12},
    "upbeat": {"f1": 261.63, "f2": 329.63, "f3": 392.0, "lp": 2400, "vol": 0.16},
    "cinematic": {"f1": 110.0, "f2": 164.81, "f3": 220.0, "lp": 1200, "vol": 0.14},
    "drama": {"f1": 98.0, "f2": 146.83, "f3": 196.0, "lp": 1400, "vol": 0.13},
}


def _fixtures_music_dir() -> Path:
    # backend/fixtures/music — optional pre-rendered beds / env-overridable URLs later
    return Path(__file__).resolve().parents[2] / "fixtures" / "music"


def _render_bgm_wav(duration: float, dest: Path, *, preset: str = "soft") -> Path:
    """Multi-tone procedural bed (upbeat/cinematic/soft/drama). Not licensed music.

    If ``fixtures/music/{preset}.wav`` exists, loop/trim that file instead (allows
    shipping better beds without code changes).
    """
    dur = max(1.0, min(float(duration), 120.0))
    preset = preset if preset in BGM_PRESETS else "soft"
    fixture = _fixtures_music_dir() / f"{preset}.wav"
    if fixture.is_file() and fixture.stat().st_size > 1000:
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-stream_loop", "-1", "-i", str(fixture),
                "-t", f"{dur:.2f}", "-ac", "2",
                "-af", f"volume={BGM_PRESETS[preset]['vol'] * 4:.3f}",
                str(dest),
            ],
            check=True, capture_output=True, timeout=60,
        )
        return dest
    cfg = BGM_PRESETS[preset]
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-t", f"{dur:.2f}",
            "-i", f"sine=frequency={cfg['f1']}:sample_rate=44100",
            "-f", "lavfi", "-t", f"{dur:.2f}",
            "-i", f"sine=frequency={cfg['f2']}:sample_rate=44100",
            "-f", "lavfi", "-t", f"{dur:.2f}",
            "-i", f"sine=frequency={cfg['f3']}:sample_rate=44100",
            "-filter_complex",
            f"[0:a][1:a][2:a]amix=inputs=3:duration=longest,"
            f"lowpass=f={cfg['lp']},volume={cfg['vol']}[a]",
            "-map", "[a]", "-ac", "2", str(dest),
        ],
        check=True, capture_output=True, timeout=60,
    )
    return dest


def _append_cta_card(video_path: Path, cta_text: str, *, seconds: float = 2.4) -> Path:
    """Append a short end card with CTA copy (Creatify/HeyGen-style finish)."""
    text = (cta_text or "").strip()
    if not text or seconds <= 0.3:
        return video_path
    w, h = _probe_size(video_path)
    w -= w % 2
    h -= h % 2
    font = _cta_fontfile().replace("\\", "\\\\").replace(":", "\\:")
    safe = _escape_drawtext(text)
    fontsize = max(28, min(56, w // 14))
    gen_dir = video_path.parent
    card = gen_dir / f"cta_{uuid.uuid4().hex[:10]}.mp4"
    out = gen_dir / f"{video_path.stem}_cta.mp4"
    vf = (
        f"drawtext=fontfile='{font}':text='{safe}':fontsize={fontsize}:"
        f"fontcolor=white:borderw=2:bordercolor=black@0.55:"
        f"x=(w-text_w)/2:y=(h-text_h)/2"
    )
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", f"color=c=0x0B0D14:s={w}x{h}:d={seconds:.2f}",
                "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={seconds:.2f}",
                "-vf", vf,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25",
                "-c:a", "aac", "-shortest", str(card),
            ],
            check=True, capture_output=True, timeout=60,
        )
        # Guarantee main has audio before concat
        main = video_path
        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "a",
                 "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(video_path)],
                capture_output=True, text=True, timeout=30,
            )
            if not (probe.stdout or "").strip():
                filled = gen_dir / f"main_a_{uuid.uuid4().hex[:8]}.mp4"
                dur = max(_probe_duration(video_path), 0.5)
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path),
                        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={dur:.2f}",
                        "-map", "0:v:0", "-map", "1:a:0", "-shortest",
                        "-c:v", "copy", "-c:a", "aac", str(filled),
                    ],
                    check=True, capture_output=True, timeout=120,
                )
                main = filled
        except Exception:
            main = video_path

        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(main), "-i", str(card),
                "-filter_complex",
                "[0:v]fps=25,setsar=1[v0];"
                "[1:v]fps=25,setsar=1[v1];"
                "[0:a]aformat=sample_rates=44100:channel_layouts=stereo[a0];"
                "[1:a]aformat=sample_rates=44100:channel_layouts=stereo[a1];"
                "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]",
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-movflags", "+faststart", str(out),
            ],
            check=True, capture_output=True, timeout=180,
        )
        return out if out.exists() else video_path
    except Exception as e:
        logger.warning("[demo] CTA card append failed: %s", e)
        return video_path


def compose_final_video(video_urls: list[str], style: Optional[str] = None,
                        with_audio: bool = True, narration_url: Optional[str] = None,
                        *, transitions: Optional[list[str]] = None,
                        subtitle_track: Optional[list[dict]] = None,
                        clip_trims: Optional[list[dict]] = None,
                        export_preset: Optional[str] = None,
                        bgm: bool = False,
                        bgm_preset: Optional[str] = None,
                        subtitle_style: Optional[str] = None,
                        cta_text: Optional[str] = None,
                        cta_seconds: float = 2.4,
                        preserve_clip_audio: bool = False) -> tuple[str, str]:
    """
    Stitch multiple shot videos into ONE final film (the Director Agent's hero
    deliverable). Scales/pads every shot to the export canvas, concatenates with
    ffmpeg, muxes narration and/or soft BGM, burns subtitles, and optionally
    appends an end CTA card. Returns (final_video_url, poster_url).

    ``preserve_clip_audio=True`` keeps speech already baked into clips (口播 lipsync)
    instead of replacing with narration/BGM beds.
    ``subtitle_style`` / ``bgm_preset`` select packaging presets (feed/talking/ad/…).
    """
    paths = [p for p in (_local_media_path(u) for u in video_urls) if p]
    if not paths:
        raise RuntimeError("compose: no local shot videos to stitch")

    gen_dir = _generated_dir()
    out_name = f"final_{uuid.uuid4().hex[:12]}.mp4"
    out_path = gen_dir / out_name

    trim_specs = clip_trims or [{} for _ in paths]
    work_paths: list[Path] = []
    for i, src in enumerate(paths):
        spec = trim_specs[i] if i < len(trim_specs) else {}
        start = float(spec.get("start", 0) or 0)
        end_raw = float(spec.get("end", 0) or 0)
        full_dur = _probe_duration(src)
        end = end_raw if end_raw > 0 else full_dur
        needs_trim = start > 0.05 or end < full_dur - 0.05
        if needs_trim and not preserve_clip_audio:
            trimmed = gen_dir / f"trim_{uuid.uuid4().hex[:10]}.mp4"
            _trim_video(src, start, end, trimmed)
            work_paths.append(trimmed)
        else:
            work_paths.append(src)
    paths = work_paths

    base_w, base_h = _probe_size(paths[0])
    base_w -= base_w % 2
    base_h -= base_h % 2
    if export_preset and export_preset in EXPORT_PRESETS:
        w, h = EXPORT_PRESETS[export_preset]
    else:
        w, h = base_w, base_h
    w -= w % 2
    h -= h % 2

    # ── Talking / baked-audio path: keep clip speech, package subs + CTA ──
    if preserve_clip_audio:
        # Ensure every clip has an audio stream (demo Ken Burns may be silent)
        norm_paths: list[Path] = []
        for src in paths:
            dur = max(_probe_duration(src), 0.5)
            has_a = False
            try:
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "a",
                     "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(src)],
                    capture_output=True, text=True, timeout=30,
                )
                has_a = bool((probe.stdout or "").strip())
            except Exception:
                has_a = False
            if has_a:
                norm_paths.append(src)
                continue
            filled = gen_dir / f"witha_{uuid.uuid4().hex[:10]}.mp4"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-i", str(src),
                    "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={dur:.2f}",
                    "-map", "0:v:0", "-map", "1:a:0", "-shortest",
                    "-c:v", "copy", "-c:a", "aac", str(filled),
                ],
                check=True, capture_output=True, timeout=120,
            )
            norm_paths.append(filled)
        paths = norm_paths

        inputs = []
        for p in paths:
            inputs += ["-i", str(p)]
        n_vid = len(paths)
        filters = []
        for i in range(n_vid):
            filters.append(
                f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25[v{i}];"
                f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=1.0[a{i}]"
            )
        concat_in = "".join(f"[v{i}][a{i}]" for i in range(n_vid))
        filter_complex = ";".join(filters) + f";{concat_in}concat=n={n_vid}:v=1:a=1[outv][aud]"
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error", *inputs,
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-map", "[aud]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25", "-c:a", "aac",
            "-movflags", "+faststart", str(out_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.warning("[demo] preserve_clip_audio concat failed, fallback scale: %s", e)
            src0 = paths[0]
            dur0 = max(_probe_duration(src0), 0.5)
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error", "-i", str(src0),
                    "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={dur0:.2f}",
                    "-vf",
                    f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25",
                    "-map", "0:v:0", "-map", "1:a:0", "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-movflags", "+faststart", str(out_path),
                ],
                check=True, capture_output=True, timeout=180,
            )
    else:
        total_dur = sum(_probe_duration(p) for p in paths) if with_audio else 0.0
        narration_path = _local_media_path(narration_url) if narration_url else None
        bgm_path: Optional[Path] = None
        if with_audio and bgm and total_dur > 0:
            try:
                bgm_path = _render_bgm_wav(
                    total_dur,
                    gen_dir / f"bgm_{uuid.uuid4().hex[:8]}.wav",
                    preset=(bgm_preset or "soft"),
                )
            except Exception as e:
                logger.warning("[demo] bgm render failed: %s", e)
                bgm_path = None

        audio_args: list = []
        use_narr = bool(with_audio and narration_path)
        use_bgm = bool(with_audio and bgm_path)
        if use_narr:
            audio_args += ["-i", str(narration_path)]
        if use_bgm:
            audio_args += ["-i", str(bgm_path)]
        if with_audio and not use_narr and not use_bgm and total_dur > 0:
            audio_args = ["-f", "lavfi", "-t", f"{total_dur:.2f}",
                          "-i", "sine=frequency=196:sample_rate=44100"]
            sine_fallback = True
        else:
            sine_fallback = False
        if not (use_narr or use_bgm or sine_fallback):
            with_audio = False

        inputs = []
        for p in paths:
            inputs += ["-i", p]
        n_vid = len(paths)

        filters = []
        for i in range(n_vid):
            filters.append(
                f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25[v{i}]"
            )
        concat_in = "".join(f"[v{i}]" for i in range(n_vid))
        filter_complex = ";".join(filters) + f";{concat_in}concat=n={n_vid}:v=1:a=0[outv]"
        if with_audio:
            if use_narr and use_bgm:
                filter_complex += (
                    f";[{n_vid}:a]volume=1.0[narr];"
                    f"[{n_vid + 1}:a]volume=0.22[bed];"
                    f"[narr][bed]amix=inputs=2:duration=first:dropout_transition=0[aud]"
                )
            elif use_narr:
                filter_complex += f";[{n_vid}:a]volume=1.0[aud]"
            elif use_bgm:
                filter_complex += f";[{n_vid}:a]volume=0.85[aud]"
            else:
                filter_complex += f";[{n_vid}:a]tremolo=f=0.12:d=0.6,volume=0.05[aud]"

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
            burned = _burn_subtitles(
                out_path, subtitle_track, style=subtitle_style or style or "feed",
            )
            if burned != out_path and burned.exists():
                out_path = burned
                out_name = out_path.name
        except Exception as e:
            logger.warning("[demo] subtitle burn failed (video still usable): %s", e)

    if cta_text:
        try:
            with_cta = _append_cta_card(out_path, cta_text, seconds=float(cta_seconds or 2.4))
            if with_cta != out_path and with_cta.exists():
                out_path = with_cta
                out_name = out_path.name
        except Exception as e:
            logger.warning("[demo] CTA packaging failed: %s", e)

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
                meta={"demo": True, "style": style,
                      "refs": len(kwargs.get("image_urls") or ([kwargs["image_url"]] if kwargs.get("image_url") else []))},
            ))
        return results

    async def edit_image(
        self, *, image_urls: list[str], prompt: str,
        image_size: str = "auto", **kwargs,
    ) -> GenerationResult:
        """Demo i2i — renders locally; records that refs were received."""
        size = image_size if image_size and image_size != "auto" else "1024x1024"
        url = render_demo_image(prompt or "edit", size, "auto", index=0)
        return GenerationResult(
            media_url=url, thumbnail_url=url, media_type="image",
            model=f"{self._label}-edit", resolution=size, cost=2.0,
            meta={"demo": True, "i2i": True, "ref_count": len(image_urls or [])},
        )

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
