"""Audio prep for talking-avatar / lipsync: loudness normalize + speech-friendly format.

口播成片偏安静（实测约 -20~-24 LUFS）且驱动音频未经处理时，
口型驱动也会变弱。统一在送入 Kling / 成片落盘前做响度归一化。
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# Broadcast-ish target; phone speakers still need headroom.
TARGET_I = -16.0
TARGET_TP = -1.5
TARGET_LRA = 11.0


def _run_ffmpeg(cmd: list[str], timeout: int = 120) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {(p.stderr or p.stdout or '')[:400]}")


def loudnorm_file(
    src: Path,
    dest: Path,
    *,
    target_i: float = TARGET_I,
    target_tp: float = TARGET_TP,
    target_lra: float = TARGET_LRA,
    sample_rate: int = 44100,
) -> Path:
    """Normalize loudness to target LUFS; mono PCM/WAV (or keep container for video)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Two-pass loudnorm is ideal but slow; single-pass is enough for TTS/口播.
    af = (
        f"highpass=f=80,"
        f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}:print_format=summary,"
        f"alimiter=limit=0.95"
    )
    suffix = dest.suffix.lower()
    if suffix in (".mp4", ".mov", ".webm"):
        # Remux video, replace audio track only
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(src),
            "-c:v", "copy",
            "-af", af,
            "-c:a", "aac", "-b:a", "192k", "-ar", str(sample_rate), "-ac", "1",
            "-movflags", "+faststart",
            str(dest),
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(src),
            "-af", af,
            "-ar", str(sample_rate), "-ac", "1",
            str(dest),
        ]
    _run_ffmpeg(cmd)
    if not dest.is_file() or dest.stat().st_size < 200:
        raise RuntimeError(f"loudnorm produced empty file: {dest}")
    return dest


def download_to_temp(url: str, suffix: str = ".bin") -> Path:
    req = Request(url, headers={"User-Agent": "BettyAudioPrep/1.0"})
    with urlopen(req, timeout=120) as resp:
        data = resp.read()
    td = Path(tempfile.mkdtemp(prefix="betty_audio_"))
    path = td / f"src_{uuid.uuid4().hex[:8]}{suffix}"
    path.write_bytes(data)
    return path


def prepare_lipsync_audio_bytes(
    data: bytes,
    *,
    filename: str = "drive.wav",
) -> tuple[bytes, str]:
    """Loudnorm in-memory-ish via temp files; returns (bytes, content_type)."""
    td = Path(tempfile.mkdtemp(prefix="betty_audio_"))
    src = td / filename
    src.write_bytes(data)
    out = td / f"norm_{uuid.uuid4().hex[:8]}.wav"
    loudnorm_file(src, out)
    return out.read_bytes(), "audio/wav"


def prepare_lipsync_audio_url(url: str) -> Path:
    """Download remote/local-ish audio URL and write a loudnormed WAV."""
    if not url:
        raise ValueError("empty audio url")
    # Local media path
    if "/api/v1/media/" in url or url.startswith("/"):
        from app.adapters.demo_provider import _local_media_path
        local = _local_media_path(url)
        if local and Path(local).is_file():
            src = Path(local)
        else:
            # May be absolute path under storage
            src = download_to_temp(
                url if url.startswith("http") else f"http://127.0.0.1:8000{url}",
                suffix=Path(url).suffix or ".wav",
            )
    else:
        src = download_to_temp(url, suffix=Path(url).suffix or ".wav")
    out = src.parent / f"norm_{uuid.uuid4().hex[:8]}.wav"
    loudnorm_file(src, out)
    return out


def boost_video_audio(url_or_path: str) -> Optional[str]:
    """Loudnorm audio on a finished talking video; return local media URL or None."""
    try:
        from app.adapters.demo_provider import MEDIA_URL_PREFIX, GENERATED_SUBDIR, _local_media_path
        from app.config import settings

        local = _local_media_path(url_or_path)
        if local and Path(local).is_file():
            src = Path(local)
        elif url_or_path.startswith("http"):
            src = download_to_temp(url_or_path, suffix=".mp4")
        else:
            return None
        out_name = f"{uuid.uuid4().hex[:12]}_loud.mp4"
        out = Path(settings.STORAGE_LOCAL_PATH) / GENERATED_SUBDIR / out_name
        out.parent.mkdir(parents=True, exist_ok=True)
        loudnorm_file(src, out)
        return f"{MEDIA_URL_PREFIX}/{GENERATED_SUBDIR}/{out_name}"
    except Exception as e:
        logger.warning("[audio_prep] boost_video_audio failed: %s", e)
        return None


async def synthesize_speech_edge(text: str, voice_id: str) -> tuple[bytes, str]:
    """Microsoft Edge Neural TTS (real Azure-style ids). Returns (wav_bytes, voice)."""
    import edge_tts

    voice = (voice_id or "zh-CN-XiaoxiaoNeural").strip()
    # Slightly slower → clearer phonemes for lip sync
    communicate = edge_tts.Communicate(text, voice, rate="-5%")
    td = Path(tempfile.mkdtemp(prefix="betty_tts_"))
    mp3 = td / "tts.mp3"
    await communicate.save(str(mp3))
    wav = td / "tts.wav"
    loudnorm_file(mp3, wav)
    return wav.read_bytes(), voice


def is_azure_neural_voice(voice_id: str) -> bool:
    v = (voice_id or "").strip()
    return v.startswith("zh-CN-") or v.startswith("en-US-") or v.startswith("ja-JP-")
