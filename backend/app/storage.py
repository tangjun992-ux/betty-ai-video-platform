"""
Storage Provider — unified storage interface for local, S3, and OSS.

Supports:
- Local filesystem (development)
- AWS S3 (production)
- Alibaba Cloud OSS (production, China)
- MinIO (self-hosted S3-compatible)
"""
import os
import logging
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class StorageProvider:
    """Unified storage provider."""

    def __init__(self, storage_type: str = "local", **config):
        self.storage_type = storage_type
        self.config = config
        self._s3_client = None
        self._oss_client = None

    @property
    def base_url(self) -> str:
        """Get the base URL for accessing stored files."""
        if self.storage_type == "local":
            return self.config.get("public_url", "http://localhost:8000/api/v1/media")
        elif self.storage_type in ("s3", "minio"):
            return self.config.get("cdn_url", self.config.get("bucket_url", ""))
        elif self.storage_type == "oss":
            return self.config.get("cdn_url", self.config.get("endpoint", ""))
        return ""

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        folder: str = "",
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file and return its public URL."""
        key = self._generate_key(filename, folder)

        if self.storage_type == "local":
            return await self._upload_local(file_content, key, content_type)
        elif self.storage_type in ("s3", "minio"):
            return await self._upload_s3(file_content, key, content_type)
        elif self.storage_type == "oss":
            return await self._upload_oss(file_content, key, content_type)
        else:
            raise ValueError(f"Unknown storage type: {self.storage_type}")

    async def delete_file(self, url: str) -> bool:
        """Delete a file by URL or key."""
        key = self._url_to_key(url)
        if not key:
            return False

        if self.storage_type == "local":
            return self._delete_local(key)
        elif self.storage_type in ("s3", "minio"):
            return await self._delete_s3(key)
        elif self.storage_type == "oss":
            return await self._delete_oss(key)
        return False

    def _generate_key(self, filename: str, folder: str = "") -> str:
        """Generate a unique storage key."""
        ext = Path(filename).suffix or ".dat"
        date_str = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        file_hash = hashlib.md5(f"{filename}{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        folder_path = f"{folder}/" if folder else ""
        return f"{folder_path}{date_str}/{file_hash}{ext}"

    def _url_to_key(self, url: str) -> Optional[str]:
        """Extract storage key from URL."""
        if self.storage_type == "local":
            base = self.config.get("public_url", "")
            if url.startswith(base):
                return url[len(base):].lstrip("/")
        return None

    async def _upload_local(self, content: bytes, key: str, content_type: str) -> str:
        """Upload to local filesystem."""
        storage_dir = Path(self.config.get("local_path", "/tmp/aivideo-media"))
        file_path = storage_dir / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        return f"{self.base_url.rstrip('/')}/{key}"

    def _delete_local(self, key: str) -> bool:
        """Delete local file."""
        storage_dir = Path(self.config.get("local_path", "/tmp/aivideo-media"))
        file_path = storage_dir / key
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def _upload_s3(self, content: bytes, key: str, content_type: str) -> str:
        """Upload to S3/MinIO."""
        try:
            import boto3
            from botocore.client import Config

            if self._s3_client is None:
                kwargs = {
                    "aws_access_key_id": self.config.get("access_key", ""),
                    "aws_secret_access_key": self.config.get("secret_key", ""),
                    "region_name": self.config.get("region", "cn-north-1"),
                    "config": Config(signature_version="s3v4"),
                }
                if self.config.get("endpoint_url"):
                    kwargs["endpoint_url"] = self.config["endpoint_url"]

                self._s3_client = boto3.client("s3", **kwargs)

            bucket = self.config.get("bucket", "aivideo-media")
            self._s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )

            if self.config.get("cdn_url"):
                return f"{self.config['cdn_url'].rstrip('/')}/{key}"
            return f"https://{bucket}.s3.{self.config.get('region', '')}.amazonaws.com/{key}"

        except ImportError:
            logger.warning("boto3 not installed, falling back to local storage")
            return await self._upload_local(content, key, content_type)

    async def _delete_s3(self, key: str) -> bool:
        import boto3
        bucket = self.config.get("bucket", "aivideo-media")
        client = self._s3_client
        if not client:
            client = boto3.client("s3", region_name=self.config.get("region", ""))
        try:
            client.delete_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False

    async def _upload_oss(self, content: bytes, key: str, content_type: str) -> str:
        """Upload to Alibaba Cloud OSS."""
        try:
            import oss2
            auth = oss2.Auth(
                self.config.get("access_key", ""),
                self.config.get("secret_key", ""),
            )
            bucket = oss2.Bucket(
                auth,
                self.config.get("endpoint", "https://oss-cn-hangzhou.aliyuncs.com"),
                self.config.get("bucket", "aivideo-media"),
            )
            result = bucket.put_object(key, content, headers={"Content-Type": content_type})
            if result.status == 200:
                if self.config.get("cdn_url"):
                    return f"{self.config['cdn_url'].rstrip('/')}/{key}"
                return f"https://{bucket.bucket_name}.{bucket.endpoint}/{key}"
            raise RuntimeError(f"OSS upload failed: {result.status}")
        except ImportError:
            logger.warning("oss2 not installed, falling back to local storage")
            return await self._upload_local(content, key, content_type)

    async def _delete_oss(self, key: str) -> bool:
        import oss2
        try:
            auth = oss2.Auth(self.config.get("access_key", ""), self.config.get("secret_key", ""))
            bucket = oss2.Bucket(
                auth,
                self.config.get("endpoint", ""),
                self.config.get("bucket", ""),
            )
            result = bucket.delete_object(key)
            return result.status == 204
        except Exception:
            return False


def create_storage() -> StorageProvider:
    """Create storage provider from app config."""
    from app.config import settings

    config = {
        "public_url": settings.STORAGE_PUBLIC_URL,
        "local_path": settings.STORAGE_LOCAL_PATH,
        "access_key": settings.AWS_ACCESS_KEY_ID,
        "secret_key": settings.AWS_SECRET_ACCESS_KEY,
        "bucket": settings.AWS_S3_BUCKET,
        "region": settings.AWS_REGION,
        "endpoint_url": settings.AWS_S3_ENDPOINT_URL,
    }

    return StorageProvider(
        storage_type=settings.STORAGE_TYPE,
        **config,
    )


# Singleton
storage = create_storage()
