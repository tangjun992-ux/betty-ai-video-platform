"""
Pluggable media storage backends.

Every generated / uploaded asset is written through a `StorageBackend` so the
platform can run against local disk in development and against S3 / Cloudflare
R2 / OSS (any S3-compatible object store) + a CDN in production, selected purely
by configuration (STORAGE_TYPE).

Backends return a *public URL* for the stored object:
  - local: `/api/v1/media/<rel>` (optionally prefixed by MEDIA_CDN_BASE_URL)
  - s3:    `{S3_PUBLIC_BASE_URL}/{prefix}/<rel>` (CDN edge) or the bucket URL
"""
from __future__ import annotations

import logging
import mimetypes
import threading
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

MEDIA_URL_PREFIX = "/api/v1/media"


def _guess_ct(rel_path: str, content_type: Optional[str]) -> str:
    if content_type:
        return content_type
    guessed, _ = mimetypes.guess_type(rel_path)
    return guessed or "application/octet-stream"


class StorageBackend:
    """Abstract storage backend."""

    kind = "base"

    def save_bytes(self, rel_path: str, data: bytes, content_type: Optional[str] = None) -> str:
        raise NotImplementedError

    def public_url(self, rel_path: str) -> str:
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """Write to STORAGE_LOCAL_PATH; serve via the backend's /api/v1/media route."""

    kind = "local"

    def __init__(self, root: str, cdn_base: str = ""):
        self.root = Path(root)
        self.cdn_base = (cdn_base or "").rstrip("/")

    def save_bytes(self, rel_path: str, data: bytes, content_type: Optional[str] = None) -> str:
        rel = rel_path.lstrip("/")
        dest = self.root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return self.public_url(rel)

    def public_url(self, rel_path: str) -> str:
        rel = rel_path.lstrip("/")
        if self.cdn_base:
            return f"{self.cdn_base}{MEDIA_URL_PREFIX}/{rel}"
        return f"{MEDIA_URL_PREFIX}/{rel}"


class S3Storage(StorageBackend):
    """Upload to an S3-compatible bucket (AWS S3 / Cloudflare R2 / OSS)."""

    kind = "s3"

    def __init__(self):
        import boto3  # imported lazily so local mode needs no boto3 at runtime

        self.bucket = settings.AWS_S3_BUCKET
        self.prefix = (settings.S3_KEY_PREFIX or "").strip("/")
        self.public_base = (settings.S3_PUBLIC_BASE_URL or "").rstrip("/")
        self.endpoint = settings.AWS_S3_ENDPOINT_URL
        self._client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION or None,
            endpoint_url=self.endpoint or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        )

    def _key(self, rel_path: str) -> str:
        rel = rel_path.lstrip("/")
        return f"{self.prefix}/{rel}" if self.prefix else rel

    def save_bytes(self, rel_path: str, data: bytes, content_type: Optional[str] = None) -> str:
        key = self._key(rel_path)
        self._client.put_object(
            Bucket=self.bucket, Key=key, Body=data,
            ContentType=_guess_ct(rel_path, content_type),
            CacheControl="public, max-age=31536000, immutable",
        )
        logger.info("storage(s3): uploaded %s (%d bytes)", key, len(data))
        return self.public_url(rel_path)

    def public_url(self, rel_path: str) -> str:
        key = self._key(rel_path)
        if self.public_base:
            return f"{self.public_base}/{key}"
        if self.endpoint:
            return f"{self.endpoint.rstrip('/')}/{self.bucket}/{key}"
        return f"https://{self.bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"


_backend: Optional[StorageBackend] = None
_lock = threading.Lock()


def get_storage() -> StorageBackend:
    """Return the process-wide storage backend selected by STORAGE_TYPE."""
    global _backend
    if _backend is not None:
        return _backend
    with _lock:
        if _backend is not None:
            return _backend
        if (settings.STORAGE_TYPE or "local").lower() == "s3":
            try:
                _backend = S3Storage()
                logger.info("storage: using S3 backend bucket=%s endpoint=%s",
                            settings.AWS_S3_BUCKET, settings.AWS_S3_ENDPOINT_URL or "aws")
            except Exception as e:  # fall back to local if S3 misconfigured
                logger.error("storage: S3 init failed (%s) → falling back to local", e)
                _backend = LocalStorage(settings.STORAGE_LOCAL_PATH, settings.MEDIA_CDN_BASE_URL)
        else:
            _backend = LocalStorage(settings.STORAGE_LOCAL_PATH, settings.MEDIA_CDN_BASE_URL)
    return _backend


def reset_storage() -> None:
    """Reset the cached backend (used by tests after changing config)."""
    global _backend
    _backend = None
