from fastapi import APIRouter
from app.api import generate, tasks, models_info, health, upload, websocket, gallery, auth

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(generate.router, prefix="/generate", tags=["Generation"])
router.include_router(tasks.router, prefix="/tasks", tags=["Task Management"])
router.include_router(models_info.router, prefix="/models", tags=["Available Models"])
router.include_router(upload.router, prefix="/upload", tags=["Upload"])
router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
router.include_router(gallery.router, prefix="/gallery", tags=["Gallery"])
