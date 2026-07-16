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
    return StorageStatus(
        storage_type=stype,
        cdn_configured=cdn,
        s3_public_configured=s3_pub,
        production_ok=not blockers,
        blockers=blockers,
    )


def assert_storage_production_ready() -> None:
    st = storage_status()
    if settings.is_production and not st.production_ok:
        raise RuntimeError("Storage/CDN production blockers: " + "; ".join(st.blockers))
