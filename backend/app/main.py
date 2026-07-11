from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import os

from app.config import settings as _settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline security response headers for a public-facing service."""

    async def dispatch(self, request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("X-XSS-Protection", "0")
        resp.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if _settings.is_production:
            resp.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return resp

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.config import settings
    from app.db import init_db
    print(f"[LIFESPAN] Starting AI Video Platform v{settings.APP_VERSION}")
    print(f"[LIFESPAN] Environment: {settings.ENV}")

    os.makedirs(settings.STORAGE_LOCAL_PATH, exist_ok=True)
    print(f"[LIFESPAN] Media storage: {settings.STORAGE_LOCAL_PATH}")

    try:
        await init_db()
        print("[LIFESPAN] Database initialized")
    except Exception as e:
        print(f"[LIFESPAN] Error initializing database: {e}")
        raise

    # Localize expired-prone external result URLs in the background
    import asyncio
    from app.services.media_store import backfill_generated_media
    backfill_task = asyncio.create_task(backfill_generated_media())

    yield
    backfill_task.cancel()
    print("[LIFESPAN] Shutting down...")

app = FastAPI(
    title="AI Video Platform",
    description="AI 短视频自动生成平台 — 支持多模型智能路由",
    version="0.1.0",
    # API docs are disabled in production to reduce attack surface.
    docs_url=None if _settings.is_production else "/api/docs",
    redoc_url=None if _settings.is_production else "/api/redoc",
    openapi_url=None if _settings.is_production else "/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
# Auth first
from app.api.router import router as api_router
app.include_router(api_router, prefix="/api/v1")

# Serve media files
from app.config import settings
if settings.STORAGE_TYPE == "local":
    os.makedirs(settings.STORAGE_LOCAL_PATH, exist_ok=True)
    app.mount(
        "/api/v1/media",
        StaticFiles(directory=settings.STORAGE_LOCAL_PATH),
        name="media",
    )

@app.get("/health")
async def health_check():
    """Liveness + dependency readiness probe (DB, Redis)."""
    checks = {}
    # DB
    try:
        from sqlalchemy import text
        from app.db import async_session
        async with async_session() as s:
            await s.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:80]}"
    # Redis (best-effort)
    try:
        import redis as _redis
        c = _redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=2)
        c.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:80]}"
    healthy = all(v == "ok" for v in checks.values())
    return {"status": "ok" if healthy else "degraded",
            "version": settings.APP_VERSION, "checks": checks}

@app.get("/")
async def root():
    return {"message": "AI Video Platform API", "docs": "/api/docs"}
