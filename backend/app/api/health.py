"""
Health check endpoint.
"""
from fastapi import APIRouter
from datetime import datetime, timezone
import os

router = APIRouter()


@router.get("/")
async def health_status():
    """Health check."""
    services = {}

    # Check database (just check file exists)
    db_path = "./dev.db"
    if os.path.exists(db_path):
        services["database"] = "healthy"
    else:
        services["database"] = "not_initialized"

    # Check Redis
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, db=0, socket_timeout=2)
        r.ping()
        services["redis"] = "healthy"
    except Exception:
        services["redis"] = "unhealthy"

    # Check Celery (just check Redis keys)
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, db=1, socket_timeout=2)
        keys = r.keys("celery*")
        services["celery"] = f"active ({len(keys)} keys)"
    except Exception:
        services["celery"] = "unavailable"

    # Check storage
    try:
        from app.config import settings
        os.makedirs(settings.STORAGE_LOCAL_PATH, exist_ok=True)
        services["storage"] = "ok"
    except Exception:
        services["storage"] = "error"

    all_ok = services["database"] == "healthy" and services["redis"] == "healthy"
    return {
        "status": "ok" if all_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
    }
