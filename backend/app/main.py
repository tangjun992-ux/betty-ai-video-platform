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
        # Generated media is content-addressed (uuid filenames) → immutable; long
        # cache makes it CDN/browser cacheable for cheap edge delivery.
        if request.url.path.startswith("/api/v1/media/"):
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.config import settings
    from app.db import init_db
    from app.observability import configure_logging, init_sentry
    configure_logging()
    init_sentry()
    if settings.is_production and settings.JWT_SECRET == "dev-secret-change-in-production-please!":
        raise RuntimeError("JWT_SECRET must be set to a strong value in production")
    print(f"[LIFESPAN] Starting AI Video Platform v{settings.APP_VERSION}")
    print(f"[LIFESPAN] Environment: {settings.ENV}")

    os.makedirs(settings.STORAGE_LOCAL_PATH, exist_ok=True)
    print(f"[LIFESPAN] Media storage: {settings.STORAGE_LOCAL_PATH}")

    try:
        await init_db()
        print("[LIFESPAN] Database initialized")
        from app.db import async_session
        from app.services.guest import migrate_legacy_guest_pool
        async with async_session() as db:
            n = await migrate_legacy_guest_pool(db)
            if n:
                print(f"[LIFESPAN] Migrated {n} legacy guest rows to legacy_pool user")
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

from app.observability import RequestContextMiddleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    """Never leak stack traces; log with the request id and return a clean 500."""
    import logging
    from fastapi.responses import JSONResponse
    rid = getattr(request.state, "request_id", "-")
    try:
        from app.metrics import HTTP_EXCEPTIONS
        HTTP_EXCEPTIONS.inc()
    except Exception:
        pass
    logging.getLogger("betty.error").exception("unhandled error rid=%s path=%s", rid, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后重试", "request_id": rid})


@app.get("/metrics")
async def metrics():
    """Prometheus metrics (HTTP counters/latency + live queue depth + task counts)."""
    from fastapi.responses import Response
    from app.metrics import render_metrics
    body, content_type = await render_metrics()
    return Response(content=body, media_type=content_type)

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


@app.get("/health/ready")
async def readiness():
    """Deep readiness probe: DB, Redis, Celery workers, and queue backlog.
    Returns 503 when a hard dependency (DB/Redis) is down (for load-balancer
    readiness gating)."""
    from fastapi.responses import JSONResponse
    checks = {}
    hard_ok = True
    # DB
    try:
        from sqlalchemy import text
        from app.db import async_session
        async with async_session() as s:
            await s.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:60]}"; hard_ok = False
    # Redis + Celery workers + queue backlog
    try:
        import redis as _redis
        c = _redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=2)
        c.ping()
        checks["redis"] = "ok"
        depths = {}
        for q in ("celery", "image_q", "video_q", "director_q"):
            try:
                depths[q] = c.llen(q)
            except Exception:
                depths[q] = None
        checks["queue_depth"] = depths
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:60]}"; hard_ok = False
    # Celery workers (best-effort ping)
    try:
        from celery_app import app as celery_app
        pong = celery_app.control.ping(timeout=1.0)
        checks["celery_workers"] = len(pong)
    except Exception:
        checks["celery_workers"] = 0
    body = {"status": "ready" if hard_ok else "not_ready",
            "version": settings.APP_VERSION, "checks": checks}
    return JSONResponse(status_code=200 if hard_ok else 503, content=body)

@app.get("/")
async def root():
    return {"message": "AI Video Platform API", "docs": "/api/docs"}
