"""Security regression tests — config hardening, path traversal, SQL field allowlist."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.auth import get_password_hash, verify_password  # noqa: E402
from app.config import Settings  # noqa: E402


def _settings(**env) -> Settings:
    s = Settings()
    for k, v in env.items():
        setattr(s, k, v)
    return s


def test_production_rejects_default_jwt_secret():
    s = _settings(ENV="production")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        s.validate_production()


def test_production_rejects_wildcard_cors():
    s = _settings(ENV="production", JWT_SECRET="x" * 48, CORS_ORIGINS=["*"])
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        s.validate_production()


def test_production_accepts_hardened_config():
    s = _settings(ENV="production", JWT_SECRET="x" * 48,
                  CORS_ORIGINS=["https://app.example.com"])
    s.validate_production()
    assert s.cors_allows_credentials


def test_credentials_disabled_for_wildcard_origin():
    assert _settings(CORS_ORIGINS=["*"]).cors_allows_credentials is False


def test_verify_password_rejects_malformed_hash():
    assert verify_password("pw", "") is False
    assert verify_password("pw", "not-a-hash") is False
    assert verify_password("pw", get_password_hash("pw")) is True
    assert verify_password("other", get_password_hash("pw")) is False


def test_media_path_resolution_blocks_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_LOCAL_PATH", str(tmp_path))
    import importlib
    from app.tasks import timeline_tasks
    importlib.reload(timeline_tasks)

    (tmp_path / "videos").mkdir()
    clip = tmp_path / "videos" / "a.mp4"
    clip.write_bytes(b"x")

    assert timeline_tasks._resolve_path("/api/v1/media/videos/a.mp4") == str(clip)
    assert timeline_tasks._resolve_path("/api/v1/media/../../etc/passwd") == ""
    assert timeline_tasks._resolve_path("/etc/passwd") == ""
    assert timeline_tasks._is_local_file("/api/v1/media/../../etc/passwd") is False


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8000/x",
    "http://localhost/x",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/internal",
    "file:///etc/passwd",
    "ftp://example.com/a.png",
    "not-a-url",
])
def test_ssrf_guard_rejects_internal_urls(url):
    from app.services.media_store import is_safe_remote_url
    assert is_safe_remote_url(url) is False


def test_generate_request_rejects_internal_urls():
    from pydantic import ValidationError
    from app.api.generate import GenerateRequest
    with pytest.raises(ValidationError):
        GenerateRequest(prompt="p", image_url="http://169.254.169.254/latest/meta-data/")
    with pytest.raises(ValidationError):
        GenerateRequest(prompt="p", webhook_url="http://127.0.0.1:8000/hook")
    assert GenerateRequest(prompt="p", image_url="/api/v1/media/uploads/a.png").image_url


@pytest.mark.parametrize("module", [
    "image_tasks", "video_tasks", "motion_tasks",
    "lipsync_tasks", "pipeline_tasks", "timeline_tasks",
])
def test_task_update_only_allows_real_columns(module):
    """Column names are interpolated into UPDATE statements, so the set they are
    checked against must be exactly the Task model's columns."""
    import importlib
    mod = importlib.import_module(f"app.tasks.{module}")
    assert {"status", "progress", "results"} <= mod._TASK_COLUMNS
    assert "status = 'x'; DROP TABLE tasks; --" not in mod._TASK_COLUMNS
