"""Thumbnail generation tests — ffmpeg invocation and PIL placeholder."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import thumbnail_gen
from app.thumbnail_gen import generate_placeholder_thumbnail, generate_video_thumbnail


class _Completed:
    def __init__(self, returncode=0, stderr=b""):
        self.returncode = returncode
        self.stderr = stderr


def _fake_ffmpeg(monkeypatch, on_extract, available=True):
    """Patch subprocess.run: first call is the `ffmpeg -version` probe."""
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[:2] == ["ffmpeg", "-version"]:
            if not available:
                raise FileNotFoundError("ffmpeg")
            return _Completed()
        return on_extract(cmd)

    monkeypatch.setattr(thumbnail_gen.subprocess, "run", run)
    return calls


def test_returns_none_when_ffmpeg_is_missing(monkeypatch, tmp_path):
    _fake_ffmpeg(monkeypatch, lambda cmd: _Completed(), available=False)
    assert generate_video_thumbnail(str(tmp_path / "clip.mp4")) is None


def test_generates_thumbnail_next_to_the_video(monkeypatch, tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")

    def extract(cmd):
        open(cmd[-1], "wb").write(b"jpeg")
        return _Completed()

    calls = _fake_ffmpeg(monkeypatch, extract)
    out = generate_video_thumbnail(str(video), timestamp=1.5, width=640)

    assert out == str(tmp_path / "clip_thumb.jpg")
    assert os.path.exists(out)
    extract_cmd = calls[-1]
    assert extract_cmd[extract_cmd.index("-ss") + 1] == "1.5"
    assert extract_cmd[extract_cmd.index("-vf") + 1] == "scale=640:-1"


def test_honours_explicit_output_path(monkeypatch, tmp_path):
    target = tmp_path / "custom" / "thumb.jpg"
    target.parent.mkdir()

    def extract(cmd):
        open(cmd[-1], "wb").write(b"x")
        return _Completed()

    _fake_ffmpeg(monkeypatch, extract)
    assert generate_video_thumbnail(str(tmp_path / "clip.mp4"), str(target)) == str(target)


def test_returns_none_when_ffmpeg_fails(monkeypatch, tmp_path):
    _fake_ffmpeg(monkeypatch, lambda cmd: _Completed(returncode=1, stderr=b"bad input"))
    assert generate_video_thumbnail(str(tmp_path / "clip.mp4")) is None


def test_returns_none_when_extraction_times_out(monkeypatch, tmp_path):
    def extract(cmd):
        raise subprocess.TimeoutExpired(cmd, 30)

    _fake_ffmpeg(monkeypatch, extract)
    assert generate_video_thumbnail(str(tmp_path / "clip.mp4")) is None


def test_placeholder_thumbnail_is_a_readable_image():
    from PIL import Image

    path = generate_placeholder_thumbnail("视频", width=200, height=120)
    assert path and os.path.exists(path)
    with Image.open(path) as img:
        assert img.size == (200, 120)
        assert img.format == "JPEG"


def test_placeholder_thumbnail_path_is_stable_per_input():
    a = generate_placeholder_thumbnail("视频")
    b = generate_placeholder_thumbnail("视频")
    c = generate_placeholder_thumbnail("other")
    assert a == b != c


def test_placeholder_thumbnail_survives_pil_failures(monkeypatch):
    import PIL

    monkeypatch.setattr(PIL.Image, "new", lambda *a, **k: (_ for _ in ()).throw(OSError("no pil")))
    assert generate_placeholder_thumbnail("视频") is None
