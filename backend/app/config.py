import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "AI Video Platform"
    APP_VERSION: str = "0.1.0"
    ENV: str = os.getenv("ENV", "development")

    # Database - default to SQLite but allow override
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-in-production-please!")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # CORS — comma-separated origins via env (prod), defaults to local dev.
    CORS_ORIGINS: list[str] = [
        o.strip() for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
        ).split(",") if o.strip()
    ]

    @property
    def is_production(self) -> bool:
        return (self.ENV or "").lower() in ("production", "prod")

    # KIE.ai Unified API
    KIE_API_KEY: str = os.getenv("KIE_API_KEY", "")
    KIE_BASE_URL: str = os.getenv("KIE_BASE_URL", "https://api.kie.ai")

    # Replicate — stable/cheap image & video generation
    REPLICATE_API_KEY: str = os.getenv("REPLICATE_API_KEY", "")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # ByteDance Seedance
    SEEDANCE_API_KEY: str = os.getenv("SEEDANCE_API_KEY", "")
    SEEDANCE_BASE_URL: str = os.getenv("SEEDANCE_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

    # Kling
    KLING_ACCESS_KEY: str = os.getenv("KLING_ACCESS_KEY", "")
    KLING_SECRET_KEY: str = os.getenv("KLING_SECRET_KEY", "")
    KLING_BASE_URL: str = os.getenv("KLING_BASE_URL", "https://api.klingai.com")

    # ── Viral Intelligence System ──
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    TIKTOK_APIFY_TOKEN: str = os.getenv("TIKTOK_APIFY_TOKEN", "")
    VIS_COLLECTION_ENABLED: bool = os.getenv("VIS_COLLECTION_ENABLED", "true").lower() == "true"
    VIS_COLLECTOR_QUEUE: str = "collector_q"

    # File Storage — backend: "local" | "s3" (S3/R2/OSS compatible)
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "local")
    STORAGE_LOCAL_PATH: str = os.getenv("STORAGE_PATH", "/tmp/aivideo-media")
    STORAGE_PUBLIC_URL: str = "http://localhost:8000/api/v1/media"
    # Optional CDN / absolute base for locally-served media (empty = relative
    # /api/v1/media path). Set to a CDN origin in production for edge delivery.
    MEDIA_CDN_BASE_URL: str = os.getenv("MEDIA_CDN_BASE_URL", "")

    # S3 / Cloudflare R2 / OSS (S3-compatible). Activated when STORAGE_TYPE=s3.
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET", "aivideo-media")
    AWS_REGION: str = os.getenv("AWS_REGION", "auto")
    AWS_S3_ENDPOINT_URL: Optional[str] = os.getenv("AWS_S3_ENDPOINT_URL") or None
    # Public CDN base for S3 objects (e.g. https://cdn.example.com or the R2
    # public bucket URL). Objects are served from f"{base}/{key}".
    S3_PUBLIC_BASE_URL: str = os.getenv("S3_PUBLIC_BASE_URL", "")
    S3_KEY_PREFIX: str = os.getenv("S3_KEY_PREFIX", "media")

    # Billing — Stripe (optional). When STRIPE_API_KEY is set, checkout uses real
    # Stripe Checkout; otherwise a dev-grant mode credits the account directly.
    STRIPE_API_KEY: str = os.getenv("STRIPE_API_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_SUCCESS_URL: str = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:3000/billing?status=success")
    STRIPE_CANCEL_URL: str = os.getenv("STRIPE_CANCEL_URL", "http://localhost:3000/pricing?status=cancel")
    # Production price IDs (preferred over ad-hoc price_data when set).
    STRIPE_PRICE_STARTER_MONTHLY: str = os.getenv("STRIPE_PRICE_STARTER_MONTHLY", "")
    STRIPE_PRICE_STARTER_YEARLY: str = os.getenv("STRIPE_PRICE_STARTER_YEARLY", "")
    STRIPE_PRICE_PERSONAL_MONTHLY: str = os.getenv("STRIPE_PRICE_PERSONAL_MONTHLY", "")
    STRIPE_PRICE_PERSONAL_YEARLY: str = os.getenv("STRIPE_PRICE_PERSONAL_YEARLY", "")
    STRIPE_PRICE_CREATOR_MONTHLY: str = os.getenv("STRIPE_PRICE_CREATOR_MONTHLY", "")
    STRIPE_PRICE_CREATOR_YEARLY: str = os.getenv("STRIPE_PRICE_CREATOR_YEARLY", "")
    STRIPE_PRICE_PRO_MONTHLY: str = os.getenv("STRIPE_PRICE_PRO_MONTHLY", "")
    STRIPE_PRICE_PRO_YEARLY: str = os.getenv("STRIPE_PRICE_PRO_YEARLY", "")
    # Yapper-aligned Max tier (falls back to PRO envs when empty).
    STRIPE_PRICE_MAX_MONTHLY: str = os.getenv("STRIPE_PRICE_MAX_MONTHLY", "") or os.getenv("STRIPE_PRICE_PRO_MONTHLY", "")
    STRIPE_PRICE_MAX_YEARLY: str = os.getenv("STRIPE_PRICE_MAX_YEARLY", "") or os.getenv("STRIPE_PRICE_PRO_YEARLY", "")
    STRIPE_PRICE_TEAM_SEAT_MONTHLY: str = os.getenv("STRIPE_PRICE_TEAM_SEAT_MONTHLY", "")

    # Observability
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Public base URL for payment async callbacks (must be public HTTPS in prod).
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
    # USD→CNY rate for RMB payment display (packs/plans are priced in USD).
    USD_TO_CNY: float = float(os.getenv("USD_TO_CNY", "7.2"))

    # WeChat Pay (Native 扫码). Live when appid+mchid+key+cert are configured.
    WECHAT_APPID: str = os.getenv("WECHAT_APPID", "")
    WECHAT_MCHID: str = os.getenv("WECHAT_MCHID", "")
    WECHAT_API_V3_KEY: str = os.getenv("WECHAT_API_V3_KEY", "")
    WECHAT_CERT_SERIAL_NO: str = os.getenv("WECHAT_CERT_SERIAL_NO", "")
    WECHAT_PRIVATE_KEY_PATH: str = os.getenv("WECHAT_PRIVATE_KEY_PATH", "")

    # Alipay (当面付/precreate 扫码). Live when app_id + keys are configured.
    ALIPAY_APP_ID: str = os.getenv("ALIPAY_APP_ID", "")
    ALIPAY_APP_PRIVATE_KEY_PATH: str = os.getenv("ALIPAY_APP_PRIVATE_KEY_PATH", "")
    ALIPAY_PUBLIC_KEY_PATH: str = os.getenv("ALIPAY_PUBLIC_KEY_PATH", "")
    ALIPAY_SANDBOX: bool = os.getenv("ALIPAY_SANDBOX", "true").lower() == "true"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Prevent accidental secret leakage in logs/JSON responses
        json_schema_extra = {
            "REDDIT_CLIENT_SECRET": {"write_only": True},
            "YOUTUBE_API_KEY": {"write_only": True},
            "TIKTOK_APIFY_TOKEN": {"write_only": True},
        }

settings = Settings()
