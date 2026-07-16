#!/usr/bin/env python3
"""Regenerate license-free Motion fixture assets under fixtures/motion/."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "motion"


def main() -> int:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow required: pip install Pillow", file=sys.stderr)
        return 1

    ROOT.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (512, 768), (32, 40, 56))
    d = ImageDraw.Draw(img)
    d.ellipse([206, 80, 306, 180], fill=(220, 200, 180))
    d.rectangle([230, 180, 282, 420], fill=(70, 130, 180))
    d.rectangle([160, 200, 230, 230], fill=(70, 130, 180))
    d.rectangle([282, 200, 352, 230], fill=(70, 130, 180))
    d.rectangle([230, 420, 250, 620], fill=(40, 60, 90))
    d.rectangle([262, 420, 282, 620], fill=(40, 60, 90))
    still = ROOT / "still.png"
    img.save(still, "PNG")

    ref = ROOT / "ref.mp4"
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "color=c=0x203040:s=512x768:d=2",
        "-f", "lavfi", "-i", "color=c=0x4682b4:s=40x40:d=2",
        "-filter_complex", "[1][0]overlay=x='40+t*180':y=300",
        "-t", "2", "-pix_fmt", "yuv420p", "-an",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        str(ref),
    ]
    subprocess.run(cmd, check=True)
    print(f"OK still={still} ({still.stat().st_size}B) ref={ref} ({ref.stat().st_size}B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
