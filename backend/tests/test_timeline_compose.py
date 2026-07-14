"""Timeline compose + subtitle burn + project persistence tests."""
import shutil
import subprocess
from pathlib import Path

import pytest
from httpx import Client

BASE_URL = "http://localhost:8000"
API = f"{BASE_URL}/api/v1"
GUEST = "test-timeline-guest-001"


def _server_up() -> bool:
    try:
        return Client(base_url=BASE_URL, timeout=2).get("/health").status_code == 200
    except Exception:
        return False


def _ffmpeg_ok() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=5)
        return True
    except Exception:
        return False


class TestSubtitleHelpers:
    def test_write_srt_timestamps_and_content(self, tmp_path: Path):
        from app.adapters.demo_provider import _write_srt, _srt_timestamp

        assert _srt_timestamp(0) == "00:00:00,000"
        assert _srt_timestamp(65.5) == "00:01:05,500"

        out = tmp_path / "test.srt"
        _write_srt(
            [
                {"text": "Hello Betty", "start": 0, "end": 3},
                {"text": "  ", "start": 3, "end": 6},
                {"text": "Second line", "start": 3, "end": 8},
            ],
            out,
        )
        body = out.read_text(encoding="utf-8")
        assert "Hello Betty" in body
        assert "Second line" in body
        assert body.count("-->") == 2

    @pytest.mark.skipif(not _ffmpeg_ok(), reason="ffmpeg not available")
    def test_burn_subtitles_produces_new_file(self, tmp_path: Path):
        from app.adapters.demo_provider import render_demo_video, _burn_subtitles, _local_media_path

        url, _ = render_demo_video("subtitle burn unit", "320x180", 2, "cinematic")
        src = Path(_local_media_path(url))
        assert src.exists()
        dst = tmp_path / "burned.mp4"
        shutil.copy(src, dst)
        burned = _burn_subtitles(dst, [{"text": "E2E字幕", "start": 0, "end": 2}])
        assert burned.exists()
        assert burned.stat().st_size > 0
        assert burned.name.endswith("_sub.mp4")


@pytest.mark.skipif(not _server_up(), reason="backend server not running on :8000")
class TestTimelineAPI:
    @pytest.fixture
    def client(self):
        return Client(base_url=API, timeout=120, headers={"X-Guest-Id": GUEST})

    @pytest.fixture
    def video_urls(self):
        from app.adapters.demo_provider import render_demo_video

        if not _ffmpeg_ok():
            pytest.skip("ffmpeg not available")
        u1, _ = render_demo_video("timeline clip 1", "320x180", 2, "cinematic")
        u2, _ = render_demo_video("timeline clip 2", "320x180", 2, "sci-fi")
        return [u1, u2]

    def test_save_list_get_project(self, client, video_urls):
        save = client.post(
            "/timeline/projects",
            json={
                "name": "pytest 时间线",
                "clips": [
                    {"url": video_urls[0], "start": 0, "end": 2, "transition": "fade"},
                    {"url": video_urls[1], "start": 0, "end": 2, "transition": "dissolve"},
                ],
                "settings": {
                    "with_audio": True,
                    "transition": "fade",
                    "subtitle_track": [{"text": "持久化字幕", "start": 0, "end": 5}],
                },
            },
        )
        assert save.status_code == 201, save.text
        pid = save.json()["id"]

        listed = client.get("/timeline/projects")
        assert listed.status_code == 200
        ids = [p["id"] for p in listed.json().get("projects", [])]
        assert pid in ids

        got = client.get(f"/timeline/projects/{pid}")
        assert got.status_code == 200
        body = got.json()
        assert body["name"] == "pytest 时间线"
        assert len(body["clips"]) == 2
        assert body["settings"]["subtitle_track"][0]["text"] == "持久化字幕"

    def test_compose_with_subtitle_track(self, client, video_urls):
        res = client.post(
            "/timeline/compose",
            json={
                "clips": [
                    {"url": video_urls[0], "transition": "fade"},
                    {"url": video_urls[1], "transition": "fade"},
                ],
                "with_audio": True,
                "transition": "fade",
                "subtitle_track": [{"text": "烧录测试字幕", "start": 0, "end": 6}],
            },
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["clip_count"] == 2
        assert data["url"]
        assert data["subtitle_track"]

        from app.adapters.demo_provider import _local_media_path

        path = Path(_local_media_path(data["url"]))
        assert path.exists()
        assert path.stat().st_size > 1000
