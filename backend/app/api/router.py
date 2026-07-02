from fastapi import APIRouter
from app.api import generate, tasks, models_info, health, upload, websocket, gallery, auth, settings, lipsync, motion, timeline, pricing, director, dashboard
from app.collector.api import router as collector_router

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(generate.router, prefix="/generate", tags=["Generation"])
router.include_router(tasks.router, prefix="/tasks", tags=["Task Management"])
router.include_router(models_info.router, prefix="/models", tags=["Available Models"])
router.include_router(upload.router, prefix="/upload", tags=["Upload"])
router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
router.include_router(gallery.router, prefix="/gallery", tags=["Gallery"])
router.include_router(settings.router, prefix="/settings", tags=["Settings"])
router.include_router(pricing.router, prefix="/pricing", tags=["Pricing"])
router.include_router(director.router, prefix="/director", tags=["Director Agent"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
router.include_router(lipsync.router, prefix="", tags=["Lipsync"])
router.include_router(motion.router, prefix="", tags=["Motion Control"])
router.include_router(timeline.router, prefix="", tags=["Timeline"])
router.include_router(collector_router, tags=["Viral Intelligence"])
