"""StorageProvider tests — key generation, local upload/delete, URL mapping."""
import asyncio
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage import StorageProvider, create_storage


def local_provider(tmp_path, public_url="http://localhost:8000/api/v1/media"):
    return StorageProvider("local", local_path=str(tmp_path), public_url=public_url)


def test_base_url_per_backend():
    assert local_provider("/tmp").base_url == "http://localhost:8000/api/v1/media"
    assert StorageProvider("s3", cdn_url="https://cdn.x").base_url == "https://cdn.x"
    assert StorageProvider("s3", bucket_url="https://b.x").base_url == "https://b.x"
    assert StorageProvider("oss", endpoint="https://oss.x").base_url == "https://oss.x"
    assert StorageProvider("unknown").base_url == ""


def test_generate_key_is_date_partitioned_and_unique(tmp_path):
    p = local_provider(tmp_path)
    key = p._generate_key("clip.mp4", folder="uploads")
    assert re.fullmatch(r"uploads/\d{4}/\d{2}/\d{2}/[0-9a-f]{8}\.mp4", key)
    assert p._generate_key("clip.mp4") != key
    # Extension-less names still get a suffix.
    assert p._generate_key("noext").endswith(".dat")


def test_local_upload_writes_file_and_returns_public_url(tmp_path):
    p = local_provider(tmp_path)
    url = asyncio.run(p.upload_file(b"bytes", "a.png", folder="uploads", content_type="image/png"))
    assert url.startswith("http://localhost:8000/api/v1/media/uploads/")
    key = url.split("/api/v1/media/")[1]
    assert (tmp_path / key).read_bytes() == b"bytes"


def test_local_delete_removes_the_file(tmp_path):
    p = local_provider(tmp_path)
    url = asyncio.run(p.upload_file(b"bytes", "a.png"))
    assert asyncio.run(p.delete_file(url)) is True
    # Second delete finds nothing left.
    assert asyncio.run(p.delete_file(url)) is False


def test_delete_ignores_foreign_urls(tmp_path):
    p = local_provider(tmp_path)
    assert asyncio.run(p.delete_file("https://cdn.other.com/a.png")) is False


def test_unknown_backend_rejects_uploads():
    with pytest.raises(ValueError, match="Unknown storage type"):
        asyncio.run(StorageProvider("floppy-disk").upload_file(b"x", "a.png"))


def test_url_to_key_only_supported_for_local():
    assert StorageProvider("s3", cdn_url="https://cdn.x")._url_to_key("https://cdn.x/a.png") is None


def test_create_storage_reads_app_settings(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "STORAGE_TYPE", "local")
    monkeypatch.setattr(settings, "STORAGE_LOCAL_PATH", "/tmp/betty-test-media")
    provider = create_storage()
    assert provider.storage_type == "local"
    assert provider.config["local_path"] == "/tmp/betty-test-media"
    assert provider.config["bucket"] == settings.AWS_S3_BUCKET
