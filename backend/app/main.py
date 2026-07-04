from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

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
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3200", "http://127.0.0.1:3200", "http://localhost:3001", "http://127.0.0.1:3001"],
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
    return {"status": "ok", "version": settings.APP_VERSION}

@app.get("/")
async def root():
    return {"message": "AI Video Platform API", "docs": "/api/docs"}
