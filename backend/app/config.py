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

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

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

    # File Storage
    STORAGE_TYPE: str = "local"
    STORAGE_LOCAL_PATH: str = os.getenv("STORAGE_PATH", "/tmp/aivideo-media")
    STORAGE_PUBLIC_URL: str = "http://localhost:8000/api/v1/media"

    # S3/OSS
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = "aivideo-media"
    AWS_REGION: str = "cn-north-1"
    AWS_S3_ENDPOINT_URL: Optional[str] = None

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
