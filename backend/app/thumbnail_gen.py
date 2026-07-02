"""
Thumbnail generator — creates video thumbnails.

Uses ffmpeg if available, falls back to placeholder.
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def generate_video_thumbnail(
    video_path: str,
    output_path: Optional[str] = None,
    timestamp: float = 0.0,
    width: int = 320,
) -> Optional[str]:
    """
    Generate a thumbnail from a video file.

    Args:
        video_path: Path to the video file
        output_path: Output path for the thumbnail (auto-generated if None)
        timestamp: Time in seconds to capture (default: 0, first frame)
        width: Thumbnail width (height auto-calculated)

    Returns:
        Path to the thumbnail file, or None if failed
    """
    try:
        # Check if ffmpeg is available
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=False, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.warning("ffmpeg not available, skipping thumbnail generation")
        return None

    # Auto-generate output path
    if output_path is None:
        video_p = Path(video_path)
        output_path = str(video_p.parent / f"{video_p.stem}_thumb.jpg")

    try:
        cmd = [
            "ffmpeg",
            "-ss", str(timestamp),
            "-i", video_path,
            "-vframes", "1",
            "-vf", f"scale={width}:-1",
            "-y",  # overwrite
            output_path,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0 and os.path.exists(output_path):
            logger.info(f"Thumbnail generated: {output_path}")
            return output_path
        else:
            logger.warning(f"ffmpeg failed: {result.stderr.decode()[:200]}")
            return None
    except Exception as e:
        logger.warning(f"Thumbnail generation failed: {e}")
        return None


def generate_placeholder_thumbnail(
    text: str = "视频",
    bg_color: str = "#1a1a2e",
    width: int = 320,
    height: int = 180,
) -> Optional[str]:
    """
    Generate a simple placeholder thumbnail using PIL.

    Args:
        text: Text to display on the thumbnail
        bg_color: Background color
        width: Width in pixels
        height: Height in pixels

    Returns:
        Path to the generated image
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import hashlib

        storage_dir = Path("/tmp/aivideo-media/thumbnails")
        storage_dir.mkdir(parents=True, exist_ok=True)

        file_hash = hashlib.md5(f"{text}{bg_color}".encode()).hexdigest()[:8]
        output_path = storage_dir / f"thumb_{file_hash}.jpg"

        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        # Draw a simple camera icon placeholder
        cx, cy = width // 2, height // 2
        draw.ellipse(
            [cx - 30, cy - 25, cx + 30, cy + 25],
            fill="#333344",
        )
        draw.rectangle(
            [cx + 25, cy - 10, cx + 40, cy + 5],
            fill="#333344",
        )

        # Draw play triangle
        draw.polygon(
            [cx - 10, cy - 12, cx - 10, cy + 12, cx + 12, cy],
            fill="#14b8a6",
        )

        # Draw text
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except IOError:
            font = ImageFont.load_default()

        _, _, tw, th, _, _ = draw.textbbox((0, 0), text, font=font)
        draw.text(
            (cx - tw / 2, cy + 35),
            text,
            fill="#ffffff",
            font=font,
        )

        img.save(str(output_path), "JPEG", quality=80)
        return str(output_path)

    except Exception as e:
        logger.warning(f"Placeholder thumbnail failed: {e}")
        return None
