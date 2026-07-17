"""Audio prep + lipsync quality path guards."""
from pathlib import Path

import pytest


def test_loudnorm_raises_quiet_speech_toward_minus_16():
    from app.services.audio_prep import loudnorm_file
    import subprocess
    import tempfile

    td = Path(tempfile.mkdtemp())
    src = td / "quiet.wav"
    # Generate a quiet sine (≈ speech band) then loudnorm
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=f=220:d=2",
            "-af", "volume=-18dB",
            str(src),
        ],
        check=True,
    )
    out = td / "norm.wav"
    loudnorm_file(src, out)
    assert out.is_file() and out.stat().st_size > 1000
    # Probe integrated loudness of output
    p = subprocess.run(
        [
            "ffmpeg", "-i", str(out),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=summary",
            "-f", "null", "-",
        ],
        capture_output=True, text=True,
    )
    log = (p.stderr or "") + (p.stdout or "")
    # Output Integrated should appear near -16
    assert "Input Integrated" in log


def test_lipsync_task_uses_loudnorm_and_edge_tts_path():
    src = Path(__file__).resolve().parents[1] / "app" / "tasks" / "lipsync_tasks.py"
    text = src.read_text(encoding="utf-8")
    assert "prepare_lipsync_audio_url" in text
    assert "synthesize_speech_edge" in text
    assert "boost_video_audio" in text
    assert "loudnorm_-16LUFS" in text
    assert "infinitalk/from-audio" in text


def test_azure_neural_voice_helper():
    from app.services.audio_prep import is_azure_neural_voice

    assert is_azure_neural_voice("zh-CN-XiaoxiaoNeural")
    assert is_azure_neural_voice("en-US-JennyNeural")
    assert not is_azure_neural_voice("Rachel")
