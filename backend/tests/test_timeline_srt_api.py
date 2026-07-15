"""Timeline SRT import API smoke (no running server required)."""
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

SAMPLE = """1
00:00:00,000 --> 00:00:03,000
E2E导入字幕
"""


@pytest.fixture
def client():
    return TestClient(app)


def test_parse_srt_endpoint(client):
    res = client.post("/api/v1/timeline/subtitles/parse", json={"content": SAMPLE})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["cue_count"] == 1
    assert data["subtitle_track"][0]["text"] == "E2E导入字幕"


def test_parse_srt_invalid(client):
    res = client.post("/api/v1/timeline/subtitles/parse", json={"content": "garbage"})
    assert res.status_code == 400
