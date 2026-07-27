"""SRT parse round-trip tests."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.adapters.demo_provider import parse_srt, _write_srt


SAMPLE = """1
00:00:01,000 --> 00:00:04,000
Hello Betty

2
00:00:05,500 --> 00:00:08,200
第二行字幕
"""


def test_parse_srt_multiple_cues():
    cues = parse_srt(SAMPLE)
    assert len(cues) == 2
    assert cues[0]["text"] == "Hello Betty"
    assert abs(cues[0]["start"] - 1.0) < 0.01
    assert abs(cues[0]["end"] - 4.0) < 0.01
    assert "第二行" in cues[1]["text"]


def test_parse_srt_empty_returns_empty():
    assert parse_srt("") == []
    assert parse_srt("not valid srt") == []


def test_write_then_parse_roundtrip(tmp_path):
    track = [
        {"text": "Line A", "start": 0, "end": 2.5},
        {"text": "Line B", "start": 3, "end": 6},
    ]
    out = tmp_path / "t.srt"
    _write_srt(track, out)
    parsed = parse_srt(out.read_text(encoding="utf-8"))
    assert len(parsed) == 2
    assert parsed[0]["text"] == "Line A"
