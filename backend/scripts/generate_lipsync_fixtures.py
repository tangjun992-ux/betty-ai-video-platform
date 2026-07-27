#!/usr/bin/env python3
"""Generate license-free lipsync/avatar fixture inputs (portrait + short speech audio)."""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "lipsync"


def make_portrait(path: Path) -> None:
    img = Image.new("RGB", (512, 640), (34, 40, 56))
    d = ImageDraw.Draw(img)
    # Simple face silhouette for lipsync input validation
    d.ellipse([156, 80, 356, 300], fill=(220, 190, 160))
    d.ellipse([210, 150, 240, 180], fill=(40, 40, 50))
    d.ellipse([272, 150, 302, 180], fill=(40, 40, 50))
    d.arc([220, 200, 292, 250], 20, 160, fill=(160, 80, 90), width=3)
    d.rectangle([180, 300, 332, 560], fill=(70, 100, 140))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")


def make_speech_wav(path: Path, seconds: float = 2.0, freq: float = 220.0) -> None:
    """Short tone as stand-in audio (real TTS preferred in live runs)."""
    rate = 22050
    n = int(rate * seconds)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            # Soft envelope so it's a valid non-silent clip
            env = min(1.0, i / (rate * 0.05), (n - i) / (rate * 0.1))
            sample = int(12000 * env * math.sin(2 * math.pi * freq * (i / rate)))
            frames += struct.pack("<h", sample)
        w.writeframes(frames)


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    portrait = ROOT / "portrait.png"
    audio = ROOT / "line.wav"
    readme = ROOT / "README.md"
    make_portrait(portrait)
    make_speech_wav(audio)
    readme.write_text(
        "# Lipsync / Talking Avatar fixtures\n\n"
        "| File | Role |\n|------|------|\n"
        "| `portrait.png` | Face still |\n"
        "| `line.wav` | Short speech audio |\n\n"
        "Live paid runs: `LIPSYNC_FIXTURE_LIVE=1` via "
        "`scripts/fixture_derivative_harness.py`.\n",
        encoding="utf-8",
    )
    print(f"Wrote {portrait} ({portrait.stat().st_size} B)")
    print(f"Wrote {audio} ({audio.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
