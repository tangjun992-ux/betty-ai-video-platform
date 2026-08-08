"""
Production storage / CDN readiness checks.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass
class StorageStatus:
    storage_type: str
    cdn_configured: bool
    s3_public_configured: bool
    production_ok: bool
    blockers: list[str]

    def public_dict(self) -> dict:
        return {
            "storage_type": self.storage_type,
            "cdn_configured": self.cdn_configured,
            "s3_public_configured": self.s3_public_configured,
            "production_ok": self.production_ok,
            "blockers": self.blockers,
        }


def storage_status() -> StorageStatus:
    stype = (settings.STORAGE_TYPE or "local").lower()
    cdn = bool((settings.MEDIA_CDN_BASE_URL or "").strip())
    s3_pub = bool((settings.S3_PUBLIC_BASE_URL or "").strip())
    blockers: list[str] = []
    if settings.is_production:
        if stype == "local":
            blockers.append("STORAGE_TYPE=local is not allowed in production (use s3)")
        if stype == "s3" and not (cdn or s3_pub):
            blockers.append("Set MEDIA_CDN_BASE_URL or S3_PUBLIC_BASE_URL for production media delivery")
        if stype == "s3" and not (settings.AWS_ACCESS_KEY_ID and settings.AWS_S3_BUCKET):
            blockers.append("AWS_ACCESS_KEY_ID and AWS_S3_BUCKET required when STORAGE_TYPE=s3")
    # Non-prod: still surface soft guidance when CDN unset (not a blocker).
    return StorageStatus(
        storage_type=stype,
        cdn_configured=cdn,
        s3_public_configured=s3_pub,
        production_ok=not blockers,
        blockers=blockers,
    )


def public_media_base() -> str:
    """Resolved public base for media URLs (CDN → S3 public → local relative)."""
    cdn = (settings.MEDIA_CDN_BASE_URL or "").strip().rstrip("/")
    if cdn:
        return cdn
    s3 = (settings.S3_PUBLIC_BASE_URL or "").strip().rstrip("/")
    if s3 and (settings.STORAGE_TYPE or "").lower() == "s3":
        return s3
    return (settings.STORAGE_PUBLIC_URL or "/api/v1/media").rstrip("/")


def assert_storage_production_ready() -> None:
    st = storage_status()
    if settings.is_production and not st.production_ok:
        raise RuntimeError("Storage/CDN production blockers: " + "; ".join(st.blockers))


def storage_staging_readiness() -> dict:
    """Actionable checklist for S3/CDN staging go-live."""
    st = storage_status()
    stype = (settings.STORAGE_TYPE or "local").lower()
    checklist = [
        {
            "id": "storage_type",
            "label": "STORAGE_TYPE=s3（生产禁止 local）",
            "ok": stype == "s3",
            "required": settings.is_production,
        },
        {
            "id": "aws_credentials",
            "label": "AWS_ACCESS_KEY_ID + AWS_S3_BUCKET",
            "ok": bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_S3_BUCKET),
            "required": stype == "s3",
        },
        {
            "id": "public_base",
            "label": "MEDIA_CDN_BASE_URL 或 S3_PUBLIC_BASE_URL",
            "ok": st.cdn_configured or st.s3_public_configured,
            "required": stype == "s3",
        },
        {
            "id": "local_dev_ok",
            "label": "开发环境 local 存储可用",
            "ok": stype == "local" and not settings.is_production,
            "required": False,
        },
    ]
    required = [c for c in checklist if c.get("required")]
    staging_ready = all(c["ok"] for c in required) if required else True
    if settings.is_production:
        staging_ready = st.production_ok
    blockers = [c["label"] for c in required if not c["ok"]]
    return {
        "staging_ready": staging_ready,
        "checklist": checklist,
        "storage_type": stype,
        "blockers": blockers,
        "public_media_base": public_media_base(),
        "env_hint": {
            "STORAGE_TYPE": "s3",
            "AWS_S3_BUCKET": "<bucket>",
            "MEDIA_CDN_BASE_URL": "https://cdn.example.com",
        },
    }
