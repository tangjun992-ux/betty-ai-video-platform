"""Media store tests — URL classification, extension guessing, result rewriting."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import media_store
from app.services.media_store import (
    MEDIA_URL_PREFIX,
    _guess_ext,
    _is_external,
    _local_path_from_url,
    extract_video_poster,
    localize_media_url,
    persist_results,
)


class _FakeResponse:
    def __init__(self, content=b"data", headers=None):
        self.content = content
        self.headers = headers or {"content-type": "image/png"}

    def raise_for_status(self):
        return None


class _FakeClient:
    """Stand-in for httpx.Client used as a context manager."""

    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error
        self.requested = None

    def __call__(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url):
        self.requested = url
        if self._error:
            raise self._error
        return self._response


def test_is_external_only_for_remote_http_urls():
    assert _is_external("https://cdn.provider.com/a.mp4")
    assert _is_external("http://cdn.provider.com/a.mp4")
    assert not _is_external(f"http://localhost:8000{MEDIA_URL_PREFIX}/generated/a.mp4")
    assert not _is_external("/api/v1/media/generated/a.mp4")
    assert not _is_external("")


def test_guess_ext_from_path_then_content_type():
    assert _guess_ext("https://x.com/a.mp4", None) == ".mp4"
    assert _guess_ext("https://x.com/a.JPEG", None) == ".jpg"
    assert _guess_ext("https://x.com/download", "image/png") == ".png"
    assert _guess_ext("https://x.com/download", "video/mp4; charset=utf-8") == ".mp4"
    assert _guess_ext("https://x.com/download", None) == ".bin"


def test_localize_media_url_saves_content(monkeypatch, tmp_path):
    saved = {}

    class _Storage:
        def save_bytes(self, key, content, content_type=None):
            saved.update(key=key, content=content, content_type=content_type)
            return f"{MEDIA_URL_PREFIX}/{key}"

    monkeypatch.setattr("app.services.storage.get_storage", lambda: _Storage())
    monkeypatch.setattr(media_store.httpx, "Client", _FakeClient(_FakeResponse(b"png-bytes")))

    url = localize_media_url("https://cdn.provider.com/out")
    assert url.startswith(f"{MEDIA_URL_PREFIX}/generated/")
    assert url.endswith(".png")
    assert saved["content"] == b"png-bytes"
    assert saved["content_type"] == "image/png"


def test_localize_media_url_uses_hint_for_unknown_types(monkeypatch):
    keys = []

    class _Storage:
        def save_bytes(self, key, content, content_type=None):
            keys.append(key)
            return f"{MEDIA_URL_PREFIX}/{key}"

    monkeypatch.setattr("app.services.storage.get_storage", lambda: _Storage())
    monkeypatch.setattr(
        media_store.httpx, "Client",
        _FakeClient(_FakeResponse(b"x", {"content-type": "application/octet-stream"})))

    assert localize_media_url("https://cdn.provider.com/out", "video").endswith(".mp4")
    assert localize_media_url("https://cdn.provider.com/out", "image").endswith(".jpg")
    assert [k.split(".")[-1] for k in keys] == ["mp4", "jpg"]


def test_localize_media_url_rejects_non_media_and_empty_bodies(monkeypatch):
    monkeypatch.setattr(
        media_store.httpx, "Client",
        _FakeClient(_FakeResponse(b"<html>", {"content-type": "text/html"})))
    assert localize_media_url("https://cdn.provider.com/a") is None

    monkeypatch.setattr(
        media_store.httpx, "Client", _FakeClient(_FakeResponse(b"")))
    assert localize_media_url("https://cdn.provider.com/a") is None


def test_localize_media_url_swallows_download_errors(monkeypatch):
    monkeypatch.setattr(
        media_store.httpx, "Client", _FakeClient(error=RuntimeError("boom")))
    assert localize_media_url("https://cdn.provider.com/a") is None


def test_localize_media_url_ignores_already_local_urls():
    assert localize_media_url(f"{MEDIA_URL_PREFIX}/generated/a.png") is None


def test_local_path_from_url(monkeypatch, tmp_path):
    monkeypatch.setattr(media_store.settings, "STORAGE_LOCAL_PATH", str(tmp_path))
    (tmp_path / "generated").mkdir()
    (tmp_path / "generated" / "clip.mp4").write_bytes(b"video")

    found = _local_path_from_url(f"{MEDIA_URL_PREFIX}/generated/clip.mp4?t=1")
    assert found is not None and found.read_bytes() == b"video"
    assert _local_path_from_url(f"{MEDIA_URL_PREFIX}/generated/missing.mp4") is None
    assert _local_path_from_url("https://cdn.provider.com/clip.mp4") is None
    assert _local_path_from_url("") is None


def test_extract_video_poster_without_local_file_returns_none():
    assert extract_video_poster("https://cdn.provider.com/clip.mp4") is None


def test_persist_results_rewrites_external_urls(monkeypatch):
    monkeypatch.setattr(
        media_store, "localize_media_url",
        lambda url, hint="": f"{MEDIA_URL_PREFIX}/generated/local-{hint or 'x'}.png")

    results = persist_results([
        {"url": "https://cdn.provider.com/a.png", "thumbnail": "https://cdn.provider.com/t.png",
         "type": "image"},
    ])
    r = results[0]
    assert r["source_url"] == "https://cdn.provider.com/a.png"
    assert r["url"] == f"{MEDIA_URL_PREFIX}/generated/local-image.png"
    assert r["thumbnail"] == f"{MEDIA_URL_PREFIX}/generated/local-image.png"


def test_persist_results_keeps_url_when_download_fails(monkeypatch):
    monkeypatch.setattr(media_store, "localize_media_url", lambda url, hint="": None)
    results = persist_results([{"url": "https://cdn.provider.com/a.png", "type": "image"}])
    assert results[0]["url"] == "https://cdn.provider.com/a.png"
    assert "source_url" not in results[0]


def test_persist_results_extracts_poster_for_videos(monkeypatch):
    monkeypatch.setattr(
        media_store, "localize_media_url",
        lambda url, hint="": f"{MEDIA_URL_PREFIX}/generated/clip.mp4")
    monkeypatch.setattr(
        media_store, "extract_video_poster",
        lambda url: f"{MEDIA_URL_PREFIX}/generated/poster.jpg")

    results = persist_results([{"url": "https://cdn.provider.com/a.mp4", "type": "video"}])
    assert results[0]["thumbnail"] == f"{MEDIA_URL_PREFIX}/generated/poster.jpg"


def test_persist_results_tolerates_odd_input(monkeypatch):
    monkeypatch.setattr(media_store, "localize_media_url", lambda url, hint="": None)
    assert persist_results("not-a-list") == "not-a-list"
    assert persist_results([None, "x"]) == [None, "x"]
    assert persist_results([{"url": f"{MEDIA_URL_PREFIX}/generated/a.png"}]) == [
        {"url": f"{MEDIA_URL_PREFIX}/generated/a.png"}]
